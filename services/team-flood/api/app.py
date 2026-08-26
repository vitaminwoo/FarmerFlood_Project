from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

SERVICE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(SERVICE_ROOT.parents[1] / ".env.properties")
load_dotenv(SERVICE_ROOT / ".env", override=True)
JOBS_ROOT = SERVICE_ROOT / "runtime" / "jobs"
JOBS_ROOT.mkdir(parents=True, exist_ok=True)
DIGITAL_TWINS_ROOT = SERVICE_ROOT / "runtime" / "digital-twins"
DIGITAL_TWINS_ROOT.mkdir(parents=True, exist_ok=True)
jobs: dict[str, dict] = {}
lock = threading.Lock()
app = FastAPI(title="팀 디지털 트윈·V9 Agent Worker", version="1.0")


class WorkflowRequest(BaseModel):
    alert_id: str
    storage_name: str
    station_code: str
    station_name: str
    address: str
    nx: int
    ny: int
    water_level_meters: float
    risk_level: str
    forecast_rainfall_mm: float = Field(ge=0)
    triggered_at: str
    farmer_name: str = "농업인"
    farmland_id: str | None = None
    region_id: str | None = None
    scenario_version: str = "gangnae-story-v9-52s"


@app.get("/health")
def health():
    blender = Path(os.getenv("BLENDER_EXECUTABLE", "/Applications/Blender.app/Contents/MacOS/Blender"))
    required = [
        SERVICE_ROOT / "agents" / "guidance_v9_workflow.py",
        SERVICE_ROOT / "blender" / "gangnae_inundation_v5.blend",
        SERVICE_ROOT / "output" / "inundation_v5_field_result.json",
    ]
    return {
        "status": "UP" if blender.is_file() and all(path.is_file() for path in required) else "DEGRADED",
        "blender": str(blender),
        "blender_available": blender.is_file(),
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "source_files_ready": all(path.is_file() for path in required),
    }


@app.post("/api/workflows", status_code=202)
def create_workflow(request: WorkflowRequest):
    job_id = uuid.uuid4().hex
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in request.storage_name).strip("_")
    job_dir = JOBS_ROOT / f"{safe_name}_{job_id[:8]}"
    cache_key = digital_twin_cache_key(request)
    cache_dir = digital_twin_asset_dir(request)
    job = {
        "job_id": job_id,
        "status": "QUEUED",
        "stage": "queued",
        "message": "팀 디지털 트윈 워크플로 실행 대기",
        "progress": 0,
        "storage_name": safe_name,
        "result_url": None,
        "result_path": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "job_dir": str(job_dir),
        "cache": "HIT" if (cache_dir / "digital-twin-base.mp4").is_file() and (cache_dir / "base-render-report.json").is_file() else "MISS",
        "cache_key": cache_key[:12],
    }
    with lock:
        jobs[job_id] = job
        persist_job(job)
    threading.Thread(target=run_workflow, args=(job_id, request, job_dir), daemon=True, name=f"flood-{job_id[:8]}").start()
    return public_job(job)


@app.get("/api/workflows/{job_id}")
def get_workflow(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    refresh_progress(job)
    return public_job(job)


@app.get("/api/workflows/{job_id}/detail")
def get_workflow_detail(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    refresh_progress(job)
    job_dir = Path(job["job_dir"])
    process = job.get("process")
    logs = {}
    for source, relative in log_sources().items():
        path = job_dir / relative
        logs[source] = {
            "available": path.is_file(),
            "size": path.stat().st_size if path.is_file() else 0,
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else None,
        }
    created = datetime.fromisoformat(job["created_at"])
    return {
        **public_job(job),
        "elapsed_seconds": max(0, int((datetime.now(timezone.utc) - created).total_seconds())),
        "active_process": {"name": "Python workflow", "running": process is not None and process.poll() is None},
        "progress_detail": job.get("progress_detail", {}),
        "cache": job.get("cache", {}),
        "logs": logs,
    }


@app.get("/api/workflows/{job_id}/logs")
def get_workflow_logs(job_id: str, source: str = "workflow", after: int = 0):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    relative = log_sources().get(source)
    if relative is None:
        raise HTTPException(400, "지원하지 않는 로그 종류입니다.")
    path = Path(job["job_dir"]) / relative
    if not path.is_file():
        return {"source": source, "after": max(0, after), "next": max(0, after), "text": "", "available": False}
    size = path.stat().st_size
    offset = min(max(0, after), size)
    with path.open("rb") as stream:
        stream.seek(offset)
        content = stream.read(128_000)
    return {"source": source, "after": offset, "next": offset + len(content), "text": content.decode("utf-8", errors="replace"), "available": True}


@app.get("/api/workflows/{job_id}/video")
def get_video(job_id: str):
    job = jobs.get(job_id)
    path = Path(job["result_path"]) if job and job.get("result_path") else None
    if path is None or not path.is_file():
        raise HTTPException(404, "완성된 영상이 없습니다.")
    return FileResponse(path, media_type="video/mp4", filename=f"{job['storage_name']}_warning.mp4")


def run_workflow(job_id: str, request: WorkflowRequest, job_dir: Path):
    try:
        workspace = job_dir / "workspace"
        prepare_workspace(workspace, request)
        progress_file = job_dir / "progress.json"
        update(job_id, status="RUNNING", stage="context_agent", message="입력 데이터 준비 중", progress=5)
        env = os.environ.copy()
        env.update({
            "FLOOD_ROOT": str(workspace),
            "FLOOD_PROGRESS_FILE": str(progress_file),
            "FLOOD_RUN_ID": request.alert_id,
            "FLOOD_DT_CACHE_DIR": str(digital_twin_asset_dir(request)),
        })
        log_path = job_dir / "workflow.log"
        process = subprocess.Popen(
            [sys.executable, str(workspace / "agents" / "guidance_v9_workflow.py")],
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        jobs[job_id]["process"] = process
        with log_path.open("w", encoding="utf-8") as output:
            for line in process.stdout or []:
                output.write(line)
                output.flush()
        returncode = process.wait()
        jobs[job_id]["process"] = None
        final_video = workspace / "output" / "guidance_v9" / "gangnae_guidance_v9_60s.mp4"
        if returncode != 0 or not final_video.is_file():
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-1500:] if log_path.is_file() else ""
            if "Blender.app/Contents/MacOS/Blender" in tail and "FileNotFoundError" in tail:
                raise RuntimeError(f"Blender 실행 파일을 찾을 수 없습니다. BLENDER_EXECUTABLE을 확인하세요. 상세 로그: {log_path}")
            raise RuntimeError(f"팀 V9 워크플로 실패. 상세 로그: {log_path}. 원인: {tail[-500:]}")
        update(
            job_id,
            status="DONE",
            stage="completed",
            message="디지털 트윈·멀티Agent 경고 영상 제작 완료",
            progress=100,
            result_url=f"/api/workflows/{job_id}/video",
            result_path=str(final_video),
        )
    except Exception as exc:
        job = jobs[job_id]
        refresh_progress(job)
        update(job_id, status="FAILED", message=f"{job.get('message', '팀 영상 워크플로')} 단계에서 실패", error=str(exc))


def prepare_workspace(workspace: Path, request: WorkflowRequest):
    shutil.copytree(SERVICE_ROOT / "agents", workspace / "agents")
    (workspace / "blender").mkdir(parents=True)
    for script in (SERVICE_ROOT / "blender").glob("*.py"):
        shutil.copy2(script, workspace / "blender" / script.name)
    source_blend = workspace / "blender" / "gangnae_inundation_v5.blend"
    source_blend.symlink_to(SERVICE_ROOT / "blender" / "gangnae_inundation_v5.blend")
    (workspace / "config").mkdir(parents=True)
    (workspace / "output").mkdir(parents=True)
    shutil.copy2(SERVICE_ROOT / "output" / "inundation_v5_field_result.json", workspace / "output")
    input_data = {
        "schema_version": "1.0",
        "mode": "spring_trigger_live_input",
        "recipient_label": f"{request.farmer_name}",
        "location_label": request.address,
        "field_id": request.station_code,
        "farmland_id": request.farmland_id or request.station_code,
        "region_id": request.region_id or request.address,
        "scenario_version": request.scenario_version,
        "station_name": request.station_name,
        "grid": {"nx": request.nx, "ny": request.ny},
        "water_level_meters": request.water_level_meters,
        "risk_level": request.risk_level,
        "forecast": {
            "source": "spring_trigger",
            "decision_time_label": request.triggered_at,
            "rain_start_label": "예보 기간 내",
            "predicted_24h_rain_mm": request.forecast_rainfall_mm,
            "is_live": True,
        },
        "digital_twin_video": str(workspace / "output" / "guidance_v9" / "gangnae_story_v9_base.mp4"),
        "field_result": str(workspace / "output" / "inundation_v5_field_result.json"),
        "voice": {"name": "Yuna", "rate": 200},
        "target_duration_seconds": [60, 60],
    }
    (workspace / "config" / "guidance_demo_input.json").write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")


def digital_twin_cache_key(request: WorkflowRequest) -> str:
    source = SERVICE_ROOT / "blender" / "gangnae_inundation_v5.blend"
    identity = {
        "scenario_version": request.scenario_version,
        "source_size": source.stat().st_size,
        "source_mtime_ns": source.stat().st_mtime_ns,
        "farmland_id": request.farmland_id or request.station_code,
        "region_id": request.region_id or request.address,
    }
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def safe_segment(value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in value).strip("_")
    return cleaned[:100] or "unknown"


def digital_twin_asset_dir(request: WorkflowRequest) -> Path:
    return DIGITAL_TWINS_ROOT / safe_segment(request.region_id or request.address) / safe_segment(request.farmland_id or request.station_code) / safe_segment(request.scenario_version)


def log_sources():
    return {
        "workflow": Path("workflow.log"),
        "base_render": Path("workspace/output/guidance_v9/base_render.log"),
        "composition": Path("workspace/output/guidance_v9/composition.log"),
    }


STAGES = {
    "context_agent": (8, "트리거·필지 입력 확인"),
    "script_agent": (15, "대본 Agent 완료"),
    "safety_agent": (22, "안전성 검사 Agent 완료"),
    "visual_asset_agent": (30, "시각자료 Agent 완료"),
    "base_render_agent_running": (35, "Blender 디지털 트윈 렌더링 중"),
    "base_render_agent": (58, "Blender 디지털 트윈 녹화 완료"),
    "tts_agent_running": (62, "OpenAI TTS Agent 실행 중"),
    "tts_agent": (72, "TTS Agent 완료"),
    "manifest_agent": (82, "자막·매니페스트 Agent 완료"),
    "composition_agent_running": (86, "Blender VSE 영상 합성 중"),
    "composition_agent": (94, "Blender 영상 합성 Agent 완료"),
    "final_report_agent": (98, "최종 검증 Agent 완료"),
}


def refresh_progress(job: dict):
    if job["status"] != "RUNNING":
        return
    path = Path(job["job_dir"]) / "progress.json"
    if not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stage = payload.get("stage")
        if stage in STAGES:
            progress, message = STAGES[stage]
            detail = payload.get("detail") or {}
            if stage == "base_render_agent_running" and detail.get("frame"):
                progress = 35 + round(23 * min(detail["frame"], detail.get("total_frames", 1248)) / detail.get("total_frames", 1248))
                message = f"Blender 디지털 트윈 렌더링 중 ({detail['frame']}/{detail.get('total_frames', 1248)} 프레임)"
            job.update(stage=stage, progress=progress, message=message, updated_at=datetime.now(timezone.utc).isoformat())
            job["progress_detail"] = detail
            if detail.get("cache"):
                job["cache"] = detail["cache"]
    except (OSError, json.JSONDecodeError):
        pass


def update(job_id: str, **values):
    with lock:
        jobs[job_id].update(values, updated_at=datetime.now(timezone.utc).isoformat())
        persist_job(jobs[job_id])


def public_job(job: dict):
    return {key: value for key, value in job.items() if key not in {"job_dir", "result_path", "process"}}


def persist_job(job: dict):
    path = Path(job["job_dir"]) / "job.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {key: value for key, value in job.items() if key != "process"}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def recover_jobs():
    for path in JOBS_ROOT.glob("*/job.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
            job["job_dir"] = str(path.parent)
            job["process"] = None
            final_video = path.parent / "workspace/output/guidance_v9/gangnae_guidance_v9_60s.mp4"
            if final_video.is_file() and final_video.stat().st_size >= 100_000:
                job.update(status="DONE",stage="completed",message="재시작 후 완성 영상 복구",progress=100,result_url=f"/api/workflows/{job['job_id']}/video",result_path=str(final_video))
            elif job.get("status") in {"QUEUED","RUNNING"}:
                job.update(status="FAILED",message="Worker 재시작으로 중단된 작업",error="작업 프로세스가 종료되었습니다. 다시 실행해야 합니다.")
            jobs[job["job_id"]] = job
            persist_job(job)
        except (OSError,ValueError,KeyError) as exc:
            print(f"[worker-recovery] skipped {path}: {exc}",flush=True)


recover_jobs()
