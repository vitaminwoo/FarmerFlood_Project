# Upstream provenance

- Repository: https://github.com/yhdbgit/flood.git
- Branch inspected: `main`
- Commit: `2236e95586f1a5977f7f690d583a4f15331ea1f2`
- Integrated: 2026-08-23

Only the files required by the V9 runtime are vendored because the upstream repository contains multi-gigabyte archive and generated output assets. Original Blender and Agent files are kept under `agents/`, `blender/`, `config/`, and `output/`.

Minimal integration changes:

- absolute developer paths replaced by environment-based roots;
- progress events written after each LangGraph node;
- fixed rainfall safety check changed to use the Spring trigger input;
- FastAPI wrapper added under `api/`;
- every trigger runs in an isolated `runtime/jobs/` workspace.
- Spring integration adds a cache only for the pre-TTS digital-twin base MP4; personalized final warning videos are never reused;
- Blender stdout is streamed to per-job logs so frame progress can be exposed by the Worker detail API.
- OpenAI TTS is retried with bounded speed adjustment and falls back to the local voice when it still exceeds a scene duration.
