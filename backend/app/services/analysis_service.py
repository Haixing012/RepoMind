from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import AnalysisJob, Repository
from app.services.git_service import clone_or_update_repo, normalize_github_url
from app.services.progress import progress_broker
from app.services.report_service import generate_file_summaries, generate_report, normalize_markdown_report
from app.services.repository_intelligence import collect_snapshot


class AnalysisService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def _emit(
        self,
        repository: Repository,
        *,
        status: str,
        progress: float,
        step: str,
        detail: Optional[str] = None,
    ) -> None:
        repository.status = status
        repository.progress = progress
        repository.current_step = step
        payload = {
            "event": "progress",
            "repository_id": repository.id,
            "progress": progress,
            "step": step,
            "detail": detail,
            "status": status,
        }
        await progress_broker.publish(repository.id, payload)

    async def ensure_repository(self, session: AsyncSession, repo_url: str, force_refresh: bool = False) -> Repository:
        normalized_url = normalize_github_url(repo_url)
        repository = await session.scalar(select(Repository).where(Repository.normalized_url == normalized_url))
        repo_path, default_branch, commit_hash = await asyncio.to_thread(clone_or_update_repo, repo_url, force_refresh)

        if repository is None:
            repository = Repository(
                repo_url=repo_url,
                normalized_url=normalized_url,
                repo_name=normalized_url.rsplit("/", maxsplit=1)[-1],
                local_path=str(repo_path),
            )
            session.add(repository)

        repository.repo_url = repo_url
        repository.local_path = str(repo_path)
        repository.default_branch = default_branch
        repository.last_commit = commit_hash
        await session.flush()
        return repository

    async def ensure_repository_workspace(
        self,
        session: AsyncSession,
        repository: Repository,
        *,
        force_refresh: bool = False,
        fail_hard: bool = True,
    ) -> bool:
        local_path = Path(repository.local_path) if repository.local_path else None
        workspace_missing = not local_path or not local_path.exists()

        if not workspace_missing and not force_refresh:
            return True

        repo_url = repository.repo_url or repository.normalized_url
        try:
            repo_path, default_branch, commit_hash = await asyncio.to_thread(
                clone_or_update_repo,
                repo_url,
                force_refresh,
            )
        except Exception:
            if fail_hard:
                raise
            return False

        repository.local_path = str(repo_path)
        repository.default_branch = default_branch
        repository.last_commit = commit_hash
        repository.repo_name = repository.repo_name or repository.normalized_url.rsplit("/", maxsplit=1)[-1]
        await session.flush()
        return True

    async def queue_analysis(self, repository_id: str) -> None:
        asyncio.create_task(self.run_analysis(repository_id))

    async def run_analysis(self, repository_id: str) -> None:
        async with self._session_factory() as session:
            repository = await session.get(Repository, repository_id)
            if repository is None:
                return

            job = AnalysisJob(repository_id=repository_id, status="running", progress=0.0, current_step="准备分析")
            session.add(job)
            await self._emit(repository, status="running", progress=0.05, step="准备分析", detail="初始化分析任务")
            await session.commit()

            try:
                await self.ensure_repository_workspace(session, repository, fail_hard=True)
                snapshot = await asyncio.to_thread(collect_snapshot, repository_path(repository))
                await self._emit(repository, status="running", progress=0.25, step="扫描目录", detail="已提取目录树和技术栈")
                repository.tech_stack_json = json.dumps(snapshot.tech_stack, ensure_ascii=False)
                await session.commit()

                file_summaries = await generate_file_summaries(snapshot)
                await self._emit(
                    repository,
                    status="running",
                    progress=0.58,
                    step="解读核心文件",
                    detail=f"已总结 {len(file_summaries)} 个关键文件",
                )
                await session.commit()

                report_markdown, summary = await generate_report(
                    snapshot=snapshot,
                    repo_name=repository.repo_name,
                    commit_hash=repository.last_commit or "",
                    file_summaries=file_summaries,
                )
                repository.latest_report_markdown = normalize_markdown_report(report_markdown)
                repository.latest_summary = summary
                await self._emit(repository, status="running", progress=0.92, step="生成报告", detail="AI 正在组织最终报告")
                await session.commit()

                job.status = "completed"
                job.progress = 1.0
                job.current_step = "完成"
                await self._emit(repository, status="completed", progress=1.0, step="完成", detail="分析报告已可阅读")
                await session.commit()
            except Exception as exc:  # pragma: no cover - integration path
                repository.status = "failed"
                repository.current_step = "失败"
                job.status = "failed"
                job.error_message = str(exc)
                await progress_broker.publish(
                    repository.id,
                    {
                        "event": "progress",
                        "repository_id": repository.id,
                        "progress": repository.progress,
                        "step": "失败",
                        "detail": str(exc),
                        "status": "failed",
                    },
                )
                await session.commit()
                raise


def repository_path(repository: Repository) -> Path:
    return Path(repository.local_path)
