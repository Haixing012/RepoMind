from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette import EventSourceResponse

from app.db.session import SessionLocal, get_db_session
from app.models.repository import Repository
from app.schemas.repository import AnalyzeRepositoryRequest, ChatRequest, RepositoryResponse
from app.services.analysis_service import AnalysisService
from app.services.chat_service import ask_repository
from app.services.progress import progress_broker
from app.services.report_service import normalize_markdown_report

router = APIRouter(prefix="/api")
analysis_service = AnalysisService(SessionLocal)


def serialize_repository(repository: Repository) -> RepositoryResponse:
    tech_stack = json.loads(repository.tech_stack_json) if repository.tech_stack_json else []
    return RepositoryResponse(
        id=repository.id,
        repo_url=repository.repo_url,
        normalized_url=repository.normalized_url,
        repo_name=repository.repo_name,
        status=repository.status,
        progress=repository.progress,
        current_step=repository.current_step,
        default_branch=repository.default_branch,
        last_commit=repository.last_commit,
        latest_summary=repository.latest_summary,
        tech_stack=tech_stack,
        report_markdown=normalize_markdown_report(repository.latest_report_markdown or ""),
        updated_at=repository.updated_at,
    )


@router.get("/health")
async def health() -> ORJSONResponse:
    return ORJSONResponse({"status": "ok"})


@router.post("/repos/analyze", response_model=RepositoryResponse)
async def analyze_repository(
    payload: AnalyzeRepositoryRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryResponse:
    repository = await analysis_service.ensure_repository(session, payload.repo_url, payload.force_refresh)
    cached = repository.latest_report_markdown and not payload.force_refresh and repository.status == "completed"
    if not cached:
        repository.status = "queued"
        repository.progress = 0.0
        repository.current_step = "排队中"
        await session.commit()
        await analysis_service.queue_analysis(repository.id)
        await session.refresh(repository)
    else:
        await session.commit()
    return serialize_repository(repository)


@router.get("/repos/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: str, session: AsyncSession = Depends(get_db_session)) -> RepositoryResponse:
    repository = await session.get(Repository, repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    restored = await analysis_service.ensure_repository_workspace(session, repository, fail_hard=False)
    if restored:
        await session.commit()
    else:
        repository.current_step = "本地源码缓存缺失，可重新分析或稍后重试"

    return serialize_repository(repository)


@router.get("/repos/{repository_id}/events")
async def stream_repository_events(repository_id: str, session: AsyncSession = Depends(get_db_session)):
    repository = await session.get(Repository, repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    async def event_generator():
        initial_payload = {
            "event": "progress",
            "repository_id": repository.id,
            "progress": repository.progress,
            "step": repository.current_step or "等待中",
            "detail": None,
            "status": repository.status,
        }
        yield {"event": "progress", "data": json.dumps(initial_payload, ensure_ascii=False)}
        queue = progress_broker.subscribe(repository_id)
        try:
            while True:
                payload = await queue.get()
                yield {"event": "progress", "data": json.dumps(payload, ensure_ascii=False)}
        finally:
            progress_broker.unsubscribe(repository_id, queue)

    return EventSourceResponse(event_generator())


@router.post("/repos/{repository_id}/chat")
async def chat_with_repository(
    repository_id: str,
    payload: ChatRequest,
    session: AsyncSession = Depends(get_db_session),
):
    repository = await session.get(Repository, repository_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    restored = await analysis_service.ensure_repository_workspace(session, repository, fail_hard=False)
    if not restored:
        raise HTTPException(status_code=503, detail="Local repository cache is missing and automatic restore failed")

    await session.commit()
    stream = await ask_repository(session, repository, payload.question)
    return StreamingResponse(stream, media_type="text/plain; charset=utf-8")


@router.get("/repos")
async def list_repositories(session: AsyncSession = Depends(get_db_session)):
    rows = await session.scalars(select(Repository).order_by(Repository.updated_at.desc()).limit(10))
    return [serialize_repository(row).model_dump(mode="json") for row in rows]
