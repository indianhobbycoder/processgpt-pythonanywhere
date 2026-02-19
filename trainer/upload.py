"""Trainer upload helpers."""

from __future__ import annotations

from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {"txt"}


def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_doc(process_dir: Path, uploaded_file: FileStorage) -> Path:
    filename = secure_filename(uploaded_file.filename or "")
    if not filename or not is_allowed_file(filename):
        raise ValueError("Only .txt files are allowed.")

    raw_docs_dir = process_dir / "raw_docs"
    raw_docs_dir.mkdir(parents=True, exist_ok=True)

    destination = raw_docs_dir / filename
    uploaded_file.save(destination)
    return destination
