from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from app.core.config import get_settings

settings = get_settings()


def normalize_github_url(repo_url: str) -> str:
    repo_url = repo_url.strip()
    if repo_url.startswith("git@github.com:"):
        repo_url = repo_url.replace("git@github.com:", "https://github.com/")
    if repo_url.endswith(".git"):
        repo_url = repo_url[:-4]
    parsed = urlparse(repo_url)
    path = parsed.path.strip("/")
    return f"https://github.com/{path.lower()}"


def repo_slug_from_url(normalized_url: str) -> str:
    path = urlparse(normalized_url).path.strip("/")
    return path.replace("/", "__")


def repo_path_for_url(normalized_url: str) -> Path:
    slug = repo_slug_from_url(normalized_url)
    digest = hashlib.sha1(normalized_url.encode("utf-8")).hexdigest()[:8]
    return settings.repo_storage / f"{slug}__{digest}"


def _run_git(args: list[str], cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def clone_or_update_repo(repo_url: str, force_refresh: bool = False) -> tuple[Path, str, str]:
    normalized = normalize_github_url(repo_url)
    repo_path = repo_path_for_url(normalized)

    if not repo_path.exists():
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        _run_git(["clone", "--depth", "1", normalized, str(repo_path)])
    elif force_refresh:
        _run_git(["fetch", "--all", "--prune"], cwd=repo_path)
        default_branch = get_default_branch(repo_path)
        _run_git(["reset", "--hard", f"origin/{default_branch}"], cwd=repo_path)

    default_branch = get_default_branch(repo_path)
    commit_hash = _run_git(["rev-parse", "HEAD"], cwd=repo_path)
    return repo_path, default_branch, commit_hash


def get_default_branch(repo_path: Path) -> str:
    symbolic = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_path)
    return symbolic.rsplit("/", maxsplit=1)[-1]
