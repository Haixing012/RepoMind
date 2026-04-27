from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm_service import build_llm
from app.services.repository_intelligence import RepoSnapshot


FENCED_MARKDOWN_RE = re.compile(r"^```(?:markdown|md)?\s*\n(?P<body>.*)\n```$", re.DOTALL | re.IGNORECASE)


def normalize_markdown_report(text: str) -> str:
    value = (text or "").strip()
    match = FENCED_MARKDOWN_RE.match(value)
    if match:
        value = match.group("body").strip()
    return value


async def generate_file_summaries(snapshot: RepoSnapshot) -> list[dict]:
    llm = build_llm(streaming=False)
    summaries: list[dict] = []
    prompt = (
        "你是一名源码讲解助手。请用中文总结这个文件的职责、关键函数、"
        "以及它和其他模块的关系。输出 3 个要点，每个要点不超过 30 个字。"
    )

    for item in snapshot.important_files:
        message = HumanMessage(content=f"文件路径: {item['path']}\n\n文件内容:\n{item['content']}")
        response = await llm.ainvoke([SystemMessage(content=prompt), message])
        summaries.append({"path": item["path"], "summary": str(response.content).strip()})
    return summaries


async def generate_report(
    snapshot: RepoSnapshot,
    repo_name: str,
    commit_hash: str,
    file_summaries: list[dict],
) -> tuple[str, str]:
    llm = build_llm(streaming=False)
    system_prompt = """
你是一个“项目学习助手”，任务是把开源项目讲到非专业读者也能快速看懂。

请直接输出原始 Markdown，不要用 ```markdown 代码块包裹整份报告，不要添加额外解释前言。

报告必须包含以下部分：
1. 项目概述
2. 技术栈与依赖观察
3. 目录结构导读
4. 核心模块拆解
5. 关键数据流 / 调用链
6. 设计模式与工程习惯
7. 阅读顺序建议
8. 二次开发建议

要求：
- 使用中文。
- 用通俗但专业的语言，不写空话。
- 必须引用具体文件路径。
- 对不确定的地方明确写“推测”。
- 适当使用表格、列表、代码块提升可读性。
- 标题层级清晰。
"""
    payload = {
        "repo_name": repo_name,
        "commit_hash": commit_hash,
        "tech_stack": snapshot.tech_stack,
        "tree": snapshot.tree,
        "readme_excerpt": snapshot.readme_excerpt,
        "manifests": snapshot.manifests,
        "file_summaries": file_summaries,
    }
    response = await llm.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
    )
    report_markdown = normalize_markdown_report(str(response.content))

    summary_prompt = "基于这份报告提炼一个 120 字以内的项目摘要，中文，适合卡片展示，不要使用代码块。"
    summary = await llm.ainvoke(
        [
            SystemMessage(content=summary_prompt),
            HumanMessage(content=report_markdown),
        ]
    )
    return report_markdown, str(summary.content).strip()
