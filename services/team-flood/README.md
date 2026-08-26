# Team Flood V9/V23 Video Worker

This directory contains the vendored V9 runtime and the V23 four-Agent, field-personalized cached-media runtime sourced from `yhdbgit/flood`, plus the FarmerFlood FastAPI adapter. See `UPSTREAM.md` for provenance and integration changes.

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

4. To use V23, install its pre-rendered release assets (about 3.3 GB):

```bash
cd services/team-flood
.venv/bin/python scripts/setup_v23.py
.venv/bin/python scripts/verify_v23_installation.py --decode-media
```

V23 currently supports only the three upstream demo field/user pairs and the `caution` scenario. FarmerFlood defaults to the `OSONG-FIELD-DEMO-003` visual profile while retaining the real user/farmland IDs in event metadata. This is an explicit MVP adapter, not a claim that an arbitrary registered parcel has the demo geometry. V23 does not silently fall back to V9 when assets are missing.

## Run

```bash
services/team-flood/run.sh
```

Health: `GET http://127.0.0.1:8091/health`

Spring sends a complete trigger to `POST /api/workflows`, polls `GET /api/workflows/{jobId}`, and downloads the result from `GET /api/workflows/{jobId}/video`. The default is `v23`/`caution`; V9 is an explicit compatibility option via `FLOOD_WORKER_WORKFLOW_VERSION=v9` and `FLOOD_WORKER_SCENARIO_VERSION=gangnae-story-v9-52s`.

Each trigger is isolated beneath `runtime/jobs/{station}_{time}_{jobId}/workspace`; upstream scripts never share generated outputs across concurrent jobs. V23 only shares immutable pre-rendered assets.
