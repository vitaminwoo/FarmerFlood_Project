# Team Flood Video Worker

This directory contains the minimum V9 runtime sourced from `yhdbgit/flood` plus a thin FastAPI integration adapter. See `UPSTREAM.md` for provenance and the intentionally small upstream changes.

## One-time setup

1. Install Blender and keep it at `/Applications/Blender.app`, or set `BLENDER_EXECUTABLE`.
2. Create the worker environment:

```bash
cd services/team-flood
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

3. Put only `OPENAI_API_KEY` in `.env`. The worker also reads the project-root `.env.properties` for local convenience.

## Run

```bash
services/team-flood/run.sh
```

Health: `GET http://127.0.0.1:8091/health`

Spring sends a complete trigger to `POST /api/workflows`, polls `GET /api/workflows/{jobId}`, and downloads the result from `GET /api/workflows/{jobId}/video`.

Each trigger is isolated beneath `runtime/jobs/{station}_{time}_{jobId}/workspace`; upstream scripts never share generated files across concurrent jobs.
