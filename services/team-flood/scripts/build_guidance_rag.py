#!/usr/bin/env python3
"""Build the local SQLite FTS RAG index from immutable source documents."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import Dict, Iterable, List


SERVICE_ROOT = Path(__file__).resolve().parents[1]
RAG_ROOT = SERVICE_ROOT / "data" / "rag"
SOURCE_ROOT = RAG_ROOT / "source_documents"
MANIFEST_PATH = RAG_ROOT / "source_manifest.json"
CHUNKS_PATH = RAG_ROOT / "index" / "chunks.jsonl"
DB_PATH = RAG_ROOT / "index" / "guidance.sqlite3"


def load_manifest() -> Dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def find_pdftotext() -> str:
    binary = shutil.which("pdftotext")
    if binary:
        return binary
    candidates = sorted(Path.home().glob(".cache/codex-runtimes/**/pdftotext"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("pdftotext is required to build the guidance RAG index")


def normalize(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("․", "·")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path: Path) -> List[str]:
    with tempfile.TemporaryDirectory(prefix="flood-rag-") as temp_dir:
        target = Path(temp_dir) / "document.txt"
        subprocess.run([find_pdftotext(), "-layout", str(path), str(target)], check=True)
        return [normalize(page) for page in target.read_text(encoding="utf-8", errors="replace").split("\f")]


def extract_hwp(path: Path) -> List[str]:
    binary = shutil.which("hwp5txt")
    if not binary:
        return []
    completed = subprocess.run([binary, str(path)], check=True, capture_output=True, text=True)
    return [normalize(completed.stdout)]


def chunk_page(text: str, max_chars: int = 700) -> Iterable[str]:
    paragraphs = [normalize(item) for item in re.split(r"\n\s*\n", text) if normalize(item)]
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            yield current
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        yield current


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(db_path: Path = DB_PATH) -> Dict:
    manifest = load_manifest()
    chunks = []
    documents = []
    for source in manifest["sources"]:
        path = SOURCE_ROOT / source["stored_name"]
        if not path.is_file():
            raise FileNotFoundError(path)
        pages = extract_pdf(path) if path.suffix.lower() == ".pdf" else extract_hwp(path)
        source_chunks = []
        for page_number, page in enumerate(pages, start=1):
            for chunk_number, text in enumerate(chunk_page(page), start=1):
                chunk_id = f"{source['source_id']}-p{page_number:03d}-c{chunk_number:02d}"
                source_chunks.append({
                    "chunk_id": chunk_id,
                    "source_id": source["source_id"],
                    "source_name": source["original_name"],
                    "page_number": page_number,
                    "text": text,
                })
        chunks.extend(source_chunks)
        documents.append({
            **source,
            "sha256": sha256(path),
            "extraction_status": "indexed" if source_chunks else "preserved_no_searchable_text",
            "chunk_count": len(source_chunks),
        })

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executescript("""
            CREATE TABLE documents (
                source_id TEXT PRIMARY KEY, original_name TEXT NOT NULL, stored_name TEXT NOT NULL,
                authority TEXT NOT NULL, sha256 TEXT NOT NULL, extraction_status TEXT NOT NULL,
                chunk_count INTEGER NOT NULL
            );
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_name TEXT NOT NULL,
                page_number INTEGER NOT NULL, text TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES documents(source_id)
            );
            CREATE VIRTUAL TABLE chunks_fts USING fts5(text, content='chunks', content_rowid='rowid', tokenize='unicode61');
        """)
        connection.executemany(
            "INSERT INTO documents VALUES (:source_id, :original_name, :stored_name, :authority, :sha256, :extraction_status, :chunk_count)",
            documents,
        )
        connection.executemany(
            "INSERT INTO chunks(chunk_id, source_id, source_name, page_number, text) VALUES (:chunk_id, :source_id, :source_name, :page_number, :text)",
            chunks,
        )
        connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
        connection.commit()
    CHUNKS_PATH.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in chunks), encoding="utf-8")
    report = {"database": str(db_path), "document_count": len(documents), "chunk_count": len(chunks), "documents": documents}
    (RAG_ROOT / "index" / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.db), ensure_ascii=False, indent=2))
