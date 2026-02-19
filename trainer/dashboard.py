"""Trainer domain helpers for process management."""

from __future__ import annotations

from pathlib import Path


def list_processes(knowledge_root: Path) -> list[str]:
    if not knowledge_root.exists():
        return []
    return sorted([p.name for p in knowledge_root.iterdir() if p.is_dir()])


def create_process(knowledge_root: Path, process_id: str) -> Path:
    normalized = process_id.strip().lower().replace(" ", "_")
    if not normalized:
        raise ValueError("Process name cannot be empty.")

    process_dir = knowledge_root / normalized
    process_dir.mkdir(parents=True, exist_ok=True)
    (process_dir / "raw_docs").mkdir(parents=True, exist_ok=True)
    return process_dir
