"""Knowledge rebuild utilities for per-process chunking and embeddings."""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path
from typing import Iterable

from scipy.sparse import save_npz
from sklearn.feature_extraction.text import TfidfVectorizer


CHUNK_SIZE = 700
OVERLAP = 100


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, 0)
    return chunks


def rebuild_process_knowledge(process_dir: Path) -> dict:
    raw_docs_dir = process_dir / "raw_docs"
    raw_docs_dir.mkdir(parents=True, exist_ok=True)

    docs = sorted(raw_docs_dir.glob("*.txt"))
    if not docs:
        raise ValueError("No .txt SOP files found in raw_docs.")

    chunks: list[str] = []
    metadata: list[dict] = []

    for doc_path in docs:
        text = _read_text_file(doc_path)
        doc_chunks = _split_into_chunks(text)
        for idx, chunk in enumerate(doc_chunks):
            chunks.append(chunk)
            metadata.append(
                {
                    "source": doc_path.name,
                    "chunk_index": idx,
                    "process": process_dir.name,
                }
            )

    if not chunks:
        raise ValueError("Document parsing produced zero chunks.")

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    vectors = vectorizer.fit_transform(chunks)

    with (process_dir / "chunks.pkl").open("wb") as f:
        pickle.dump(chunks, f)

    with (process_dir / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with (process_dir / "vectorizer.pkl").open("wb") as f:
        pickle.dump(vectorizer, f)

    save_npz(process_dir / "vectors.npz", vectors)

    return {
        "process": process_dir.name,
        "documents": len(docs),
        "chunks": len(chunks),
        "vector_shape": list(vectors.shape),
    }
