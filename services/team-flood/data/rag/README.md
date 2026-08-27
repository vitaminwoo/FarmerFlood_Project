# 호우 안내 RAG 원본 데이터

이 디렉터리의 `source_documents/`는 **대본 생성 Agent가 사용하는 RAG 원본 자료의 보존본**이다. 원본 파일은 내용을 수정하지 않고 영문 저장명으로 복사했으며, 원래 파일명·발행기관·저장명은 `source_manifest.json`에서 대응한다.

- `source_documents/`: 첨부 원본 PDF/HWP 보존본
- `source_manifest.json`: 원본명, 발행기관, 용도 메타데이터
- `index/guidance.sqlite3`: 실행 시 검색하는 SQLite FTS5 RAG DB
- `index/chunks.jsonl`: DB에 적재된 검색 청크의 검토 가능한 표현
- `index/build_report.json`: 문서별 추출/적재 결과와 SHA-256

DB 재생성:

```bash
cd services/team-flood
.venv/bin/python scripts/build_guidance_rag.py
```

이미지형 PDF나 로컬 추출기가 없는 HWP는 원본과 해시를 보존하고 `preserved_no_searchable_text`로 기록한다. 검색 가능한 텍스트를 조작해 채우지 않는다.
