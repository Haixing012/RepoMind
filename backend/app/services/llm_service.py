from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def build_llm(streaming: bool = False) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.1,
        streaming=streaming,
    )
