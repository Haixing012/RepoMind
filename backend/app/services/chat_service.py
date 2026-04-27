from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import ChatMessage, Repository
from app.services.llm_service import build_llm
from app.services.repository_intelligence import build_tree, read_file, search_code


class SearchCodeArgs(BaseModel):
    query: str = Field(min_length=1)


class ReadFileArgs(BaseModel):
    path: str
    start_line: int = 1
    end_line: int = 220


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_tools(repo_root: Path) -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            name="list_tree",
            description="查看仓库目录结构，适合先定位模块。",
            func=lambda: build_tree(repo_root, max_lines=180),
        ),
        StructuredTool.from_function(
            name="search_code",
            description="全文搜索代码关键字，返回匹配文件和行号。",
            args_schema=SearchCodeArgs,
            func=lambda query: _json(search_code(repo_root, query)),
        ),
        StructuredTool.from_function(
            name="read_file",
            description="读取文件指定行范围，用于查看具体实现。",
            args_schema=ReadFileArgs,
            func=lambda path, start_line=1, end_line=220: read_file(repo_root, path, start_line, end_line),
        ),
    ]


async def ask_repository(session: AsyncSession, repository: Repository, question: str):
    repo_root = Path(repository.local_path)
    tools = build_tools(repo_root)
    llm = build_llm(streaming=False)
    llm_with_tools = llm.bind_tools(tools)

    recent_messages = await session.scalars(
        select(ChatMessage).where(ChatMessage.repository_id == repository.id).order_by(ChatMessage.id.desc()).limit(6)
    )
    history = list(reversed(list(recent_messages)))

    messages = [
        SystemMessage(
            content=(
                "你是源码问答助手。回答前必须优先用工具查代码。"
                "当信息不够时继续调用工具，不要编造。"
                "最终回答使用中文，引用文件路径和必要行号。"
            )
        )
    ]
    for item in history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=question))

    gathered: list[str] = []
    for _ in range(6):
        ai_message = await llm_with_tools.ainvoke(messages)
        messages.append(ai_message)
        if not ai_message.tool_calls:
            gathered.append(str(ai_message.content))
            break
        for tool_call in ai_message.tool_calls:
            tool = next(tool for tool in tools if tool.name == tool_call["name"])
            result = await tool.ainvoke(tool_call["args"])
            gathered.append(f"Tool {tool.name}:\n{result}")
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    final_llm = build_llm(streaming=True)
    synthesis_prompt = [
        SystemMessage(
            content=(
                "你现在要基于已获取的源码证据回答用户问题。"
                "请结构化回答，结论明确，引用具体文件路径和必要行号。"
                "若存在推测，请显式写出“推测”。"
            )
        ),
        HumanMessage(
            content=(
                f"用户问题：{question}\n\n"
                f"仓库：{repository.repo_name}\n\n"
                f"证据：\n{chr(10).join(gathered)}"
            )
        ),
    ]

    async def stream():
        collected: list[str] = []
        async for chunk in final_llm.astream(synthesis_prompt):
            text = chunk.content if isinstance(chunk.content, str) else ""
            if text:
                collected.append(text)
                yield text
        answer = "".join(collected).strip()
        session.add(ChatMessage(repository_id=repository.id, role="user", content=question))
        session.add(ChatMessage(repository_id=repository.id, role="assistant", content=answer))
        await session.commit()

    return stream()
