"""RAG orchestration: query rewrite, retrieval, grounded answer generation."""

from __future__ import annotations

import re
from pathlib import Path

from retriever.similarity import ProcessKnowledgeNotReady, load_process_store, retrieve_top_k


class RAGRouter:
    def __init__(self, knowledge_root: Path):
        self.knowledge_root = knowledge_root
        self._cached_process_id = None
        self._cached_store = None

    def rewrite_query(self, question: str) -> str:
        text = question.strip().lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        replacements = {
            "cust": "customer",
            "cx": "customer",
            "angry": "escalated dissatisfied",
            "mad": "dissatisfied",
            "refund me": "refund procedure",
            "cancel": "cancellation procedure",
            "not working": "service issue troubleshooting",
            "idk": "clarification needed",
            "pls": "please",
            "asap": "urgent",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)

        text = re.sub(r"\s+", " ", text).strip()
        return text or question.strip()

    def _get_store(self, process_id: str):
        if self._cached_process_id == process_id and self._cached_store is not None:
            return self._cached_store

        process_dir = self.knowledge_root / process_id
        store = load_process_store(process_dir)
        self._cached_store = store
        self._cached_process_id = process_id
        return store

    def answer(self, process_id: str, user_question: str, top_k: int = 4) -> dict:
        rewritten = self.rewrite_query(user_question)

        try:
            store = self._get_store(process_id)
        except ProcessKnowledgeNotReady as exc:
            return {
                "answer": "Answer not available: this process knowledge base is not ready yet.",
                "sources": [],
                "rewritten_query": rewritten,
                "error": str(exc),
            }

        retrieved = retrieve_top_k(store, rewritten, k=top_k)
        if not retrieved:
            return {
                "answer": (
                    "Answer not available from approved process documents. "
                    "Please rephrase or contact a trainer to update SOP coverage."
                ),
                "sources": [],
                "rewritten_query": rewritten,
            }

        lines = ["Based on approved SOP content:"]
        for i, item in enumerate(retrieved, start=1):
            snippet = item["chunk"][:300].strip()
            lines.append(f"{i}. {snippet}")

        answer = "\n".join(lines)
        sources = [
            {
                "source": item["metadata"].get("source", "unknown"),
                "chunk_index": item["metadata"].get("chunk_index"),
                "score": round(item["score"], 3),
            }
            for item in retrieved
        ]
        return {"answer": answer, "sources": sources, "rewritten_query": rewritten}
