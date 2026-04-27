from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    "coverage",
    "target",
    "vendor",
}

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".vue",
    ".java",
    ".go",
    ".rs",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".ini",
    ".cfg",
    ".sh",
    ".sql",
    ".proto",
}

IMPORTANT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(^|/)readme",
        r"(^|/)package\.json$",
        r"(^|/)pyproject\.toml$",
        r"(^|/)requirements.*\.txt$",
        r"(^|/)dockerfile$",
        r"(^|/)docker-compose",
        r"(^|/)main\.(py|ts|js|go|rs)$",
        r"(^|/)app\.(py|ts|js)$",
        r"(^|/)manage\.py$",
        r"(^|/)settings\.(py|json|yaml|yml)$",
        r"(^|/)(router|routes|api|service|controller|model|schema|config)",
    ]
]


@dataclass
class RepoSnapshot:
    tree: str
    tech_stack: list[str]
    readme_excerpt: str
    important_files: list[dict]
    manifests: dict[str, dict]


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in {"dockerfile", "makefile"}


def build_tree(root: Path, max_lines: int = 260) -> str:
    lines: list[str] = []

    def walk(current: Path, prefix: str = "") -> None:
        if len(lines) >= max_lines:
            return
        entries = [item for item in sorted(current.iterdir(), key=lambda value: (value.is_file(), value.name.lower()))]
        entries = [item for item in entries if item.name not in IGNORE_DIRS]
        for index, item in enumerate(entries):
            if len(lines) >= max_lines:
                lines.append(f"{prefix}... (truncated)")
                return
            connector = "`-- " if index == len(entries) - 1 else "|-- "
            lines.append(f"{prefix}{connector}{item.name}")
            if item.is_dir():
                child_prefix = "    " if index == len(entries) - 1 else "|   "
                walk(item, prefix + child_prefix)

    lines.append(root.name)
    walk(root)
    return "\n".join(lines)


def detect_manifests(root: Path) -> dict[str, dict]:
    manifests: dict[str, dict] = {}
    candidates = ["package.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml"]
    for candidate in candidates:
        path = root / candidate
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if candidate == "package.json":
            data = json.loads(text)
            manifests[candidate] = {
                "name": data.get("name"),
                "scripts": sorted((data.get("scripts") or {}).keys()),
                "dependencies": sorted(list((data.get("dependencies") or {}).keys()))[:20],
            }
        else:
            manifests[candidate] = {"preview": text[:1200]}
    return manifests


def detect_tech_stack(manifests: dict[str, dict], root: Path) -> list[str]:
    stack: list[str] = []
    names = set(manifests.keys())
    if "pyproject.toml" in names or "requirements.txt" in names:
        stack.append("Python")
    if "package.json" in names:
        stack.append("Node.js")
        package_json = manifests["package.json"]
        deps = set(package_json.get("dependencies", []))
        if "vue" in deps:
            stack.append("Vue")
        if "react" in deps:
            stack.append("React")
        if "typescript" in deps:
            stack.append("TypeScript")
    if (root / "Dockerfile").exists():
        stack.append("Docker")
    if (root / ".github").exists():
        stack.append("GitHub Actions")
    if not stack:
        stack.append("Mixed Source Code")
    return stack


def select_important_files(root: Path, limit: int) -> list[dict]:
    scored: list[tuple[int, Path]] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if not is_text_file(path):
            continue

        score = 0
        if len(relative.split("/")) <= 2:
            score += 2
        for pattern in IMPORTANT_PATTERNS:
            if pattern.search(relative):
                score += 8
        if path.name.startswith("test_") or "/tests/" in f"/{relative}/":
            score -= 2
        scored.append((score, path))

    scored.sort(key=lambda item: (-item[0], len(item[1].parts), item[1].name.lower()))
    selected = [path for score, path in scored if score > 0][:limit]

    result: list[dict] = []
    for path in selected:
        relative = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8", errors="ignore")[: settings.analysis_max_bytes]
        result.append({"path": relative, "content": content})
    return result


def collect_snapshot(root: Path) -> RepoSnapshot:
    manifests = detect_manifests(root)
    readme_candidates = [root / "README.md", root / "README", root / "readme.md", root / "readme"]
    readme_path = next(iter([path for path in readme_candidates if path.exists()]), None)
    readme_excerpt = ""
    if readme_path:
        readme_excerpt = readme_path.read_text(encoding="utf-8", errors="ignore")[:4000]
    return RepoSnapshot(
        tree=build_tree(root),
        tech_stack=detect_tech_stack(manifests, root),
        readme_excerpt=readme_excerpt,
        important_files=select_important_files(root, settings.analysis_max_files),
        manifests=manifests,
    )


def search_code(root: Path, query: str, limit: int = 8) -> list[dict]:
    hits: list[dict] = []
    pattern = query.lower()
    for path in root.rglob("*"):
        if len(hits) >= limit:
            break
        if path.is_dir() or any(part in IGNORE_DIRS for part in path.parts) or not is_text_file(path):
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            if pattern in line.lower():
                hits.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "lineno": lineno,
                        "line": line.strip()[:240],
                    }
                )
                if len(hits) >= limit:
                    break
    return hits


def read_file(root: Path, relative_path: str, start_line: int = 1, end_line: int = 220) -> str:
    clean_relative = relative_path.strip().replace("\\", "/").lstrip("./")
    if clean_relative.startswith(f"{root.name}/"):
        clean_relative = clean_relative[len(root.name) + 1 :]

    path = (root / clean_relative).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise ValueError("Path escapes repository root.")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    start_index = max(start_line - 1, 0)
    end_index = min(end_line, len(lines))
    numbered = [f"{idx + 1:04d}: {line}" for idx, line in enumerate(lines[start_index:end_index], start=start_index)]
    return "\n".join(numbered)
