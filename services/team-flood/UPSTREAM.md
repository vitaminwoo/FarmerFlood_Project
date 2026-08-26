# Upstream provenance

- Repository: https://github.com/yhdbgit/flood.git
- Branch inspected: `hyeokjae`
- Commit: `bfb0a5de6560ab6aaa393ad500b9968a00050a4a` (`api 연동 전`)
- Previous baseline: `2236e95586f1a5977f7f690d583a4f15331ea1f2`
- Integrated: 2026-08-27

Only runtime source, contracts, demo field metadata, font, setup scripts, and tests required by V9/V23 are vendored. The roughly 3.3 GB V23 pre-rendered media remains an external runtime asset installed under `runtime_assets/v23` or `V23_ASSET_ROOT`.

Minimal integration changes:

- absolute developer paths replaced by environment-based roots;
- progress events written after each LangGraph node;
- fixed rainfall safety check changed to use the Spring trigger input;
- FastAPI wrapper added under `api/`;
- every trigger runs in an isolated `runtime/jobs/` workspace.
- Spring integration adds a cache only for the pre-TTS digital-twin base MP4; personalized final warning videos are never reused;
- Blender stdout is streamed to per-job logs so frame progress can be exposed by the Worker detail API.
- OpenAI TTS is retried with bounded speed adjustment and falls back to the local voice when it still exceeds a scene duration.

V23 integration changes relative to upstream `bfb0a5d`:

- V23 is exposed through the existing asynchronous FastAPI job API and is the FarmerFlood default; V9 remains an explicit compatibility path;
- Spring forwards its real `user_id` and `farmland_id`, and selects the workflow/scenario through configuration;
- each V23 request writes its event and output under the existing isolated job directory;
- LangGraph nodes publish progress through `FLOOD_PROGRESS_FILE`;
- Blender executable aliases and the existing project `.env.properties` loading remain compatible;
- bounded TTS speed adjustment and macOS local-voice fallback are retained;
- upstream event ownership validation and field-specific cached asset selection are unchanged.
