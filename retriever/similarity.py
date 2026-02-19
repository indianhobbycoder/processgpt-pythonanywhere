"""Similarity and storage helpers for process-isolated retrieval."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from scipy.sparse import load_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class ProcessStore:
    process_id: str
    chunks: List[str]
    metadata: list[dict]
    vectorizer: TfidfVectorizer
    vectors: any


class ProcessKnowledgeNotReady(Exception):
    pass


def load_process_store(process_dir: Path) -> ProcessStore:
    chunks_path = process_dir / "chunks.pkl"
    metadata_path = process_dir / "metadata.json"
    model_path = process_dir / "vectorizer.pkl"
    vectors_path = process_dir / "vectors.npz"

    required = [chunks_path, metadata_path, model_path, vectors_path]
    if not all(p.exists() for p in required):
        raise ProcessKnowledgeNotReady(
            f"Process knowledge for '{process_dir.name}' is not built yet."
        )

    with chunks_path.open("rb") as f:
        chunks = pickle.load(f)
    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    with model_path.open("rb") as f:
        vectorizer = pickle.load(f)
    vectors = load_npz(vectors_path)

    return ProcessStore(
        process_id=process_dir.name,
        chunks=chunks,
        metadata=metadata,
        vectorizer=vectorizer,
        vectors=vectors,
    )


def retrieve_top_k(store: ProcessStore, query: str, k: int = 4) -> list[dict]:
    query_vec = store.vectorizer.transform([query])
    sim = cosine_similarity(query_vec, store.vectors).flatten()

    if sim.size == 0:
        return []

    idxs = np.argsort(sim)[::-1][:k]
    results = []
    for idx in idxs:
        score = float(sim[idx])
        if score <= 0.05:
            continue
        results.append(
            {
                "chunk": store.chunks[idx],
                "metadata": store.metadata[idx],
                "score": score,
            }
        )
    return results
