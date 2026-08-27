"""Local, reproducible RAG retrieval for official flood-guidance sources."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
from contextlib import closing
from typing import Any, Dict, List

from runtime_config import ROOT


DEFAULT_DB_PATH = ROOT / "data" / "rag" / "index" / "guidance.sqlite3"


def _search_terms(query: str) -> List[str]:
    terms = re.findall(r"[0-9A-Za-z가-힣]{2,}", query)
    seen = set()
    return [term for term in terms if not (term in seen or seen.add(term))]


def retrieve_guidance(
    query: str,
    *,
    limit: int = 3,
    db_path: Path | None = None,
) -> List[Dict[str, Any]]:
    """Return the best matching source chunks using the checked-in SQLite FTS index."""
    path = Path(os.getenv("FLOOD_GUIDANCE_RAG_DB", db_path or DEFAULT_DB_PATH))
    if not path.is_file():
        return []
    terms = _search_terms(query)
    if not terms:
        return []
    fts_query = " OR ".join(f'"{term}"' for term in terms)
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT c.chunk_id, c.source_id, c.source_name, c.page_number, c.text,
                   bm25(chunks_fts) AS score
              FROM chunks_fts
              JOIN chunks c ON c.rowid = chunks_fts.rowid
             WHERE chunks_fts MATCH ?
             ORDER BY score
             LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def compact_citations(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "chunk_id": item["chunk_id"],
            "source_id": item["source_id"],
            "source_name": item["source_name"],
            "page_number": item["page_number"],
            "matched_text": item["text"],
        }
        for item in results
    ]


def select_source_sentence(
    results: List[Dict[str, Any]],
    *,
    keywords: List[str],
    fallback: str,
    max_chars: int = 130,
) -> str:
    """Select one source sentence, favoring actionable keyword matches."""
    candidates = []
    for rank, result in enumerate(results):
        sentences = re.split(r"(?<=[.!?다요죠십시오시다])\s+|\n+", result["text"])
        for sentence in sentences:
            sentence = re.sub(r"\s+", " ", sentence).strip(" •·△o-\t")
            if not 15 <= len(sentence) <= max_chars:
                continue
            # Layout extraction can split a sentence at a visual line wrap. Never
            # narrate such a dangling fragment as if it were an official sentence.
            if not re.search(r"(다|요|시오|십시오|합시다|맙시다)[.!?]?$", sentence):
                continue
            keyword_matches = sum(1 for keyword in keywords if keyword in sentence)
            if keyword_matches == 0:
                continue
            score = keyword_matches * 3 - rank
            if re.search(r"(합니다|합시다|마십시오|확인|점검|이동|대피|접근)", sentence):
                score += 2
            candidates.append((score, sentence))
    if not candidates:
        return fallback
    return max(candidates, key=lambda item: (item[0], -len(item[1])))[1]


def dump_retrieval(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
