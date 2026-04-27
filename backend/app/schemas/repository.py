from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: str = Field(min_length=10)
    force_refresh: bool = False


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class RepositoryResponse(BaseModel):
    id: str
    repo_url: str
    normalized_url: str
    repo_name: str
    status: str
    progress: float
    current_step: Optional[str]
    default_branch: Optional[str]
    last_commit: Optional[str]
    latest_summary: Optional[str]
    tech_stack: list[str]
    report_markdown: Optional[str]
    updated_at: datetime


class ProgressEvent(BaseModel):
    event: str
    repository_id: str
    progress: float
    step: str
    detail: Optional[str] = None
    status: str
