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
app = FastAPI(title="팀 디지털 트윈·멀티 Agent Worker", version="2.0")


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
    user_id: str | None = None
    farmland_id: str | None = None
    region_id: str | None = None
    scenario_version: str = "caution"
    workflow_version: str = "v23"
    v23_field_profile_id: str | None = None
    v23_profile_user_id: str | None = None


@app.get("/health")
def health():
    blender = Path(os.getenv("BLENDER_EXECUTABLE", "/Applications/Blender.app/Contents/MacOS/Blender"))
    v9_required = [
        SERVICE_ROOT / "agents" / "guidance_v9_workflow.py",
        SERVICE_ROOT / "blender" / "gangnae_inundation_v5.blend",
        SERVICE_ROOT / "output" / "inundation_v5_field_result.json",
    ]
    v23_required = [
        SERVICE_ROOT / "agents" / "guidance_v23_workflow.py",
        SERVICE_ROOT / "data" / "v23" / "fields" / "field_registry_v23.json",
        SERVICE_ROOT / "config" / "runtime_assets_v23.json",
    ]
    asset_root = Path(os.getenv("V23_ASSET_ROOT", SERVICE_ROOT / "runtime_assets" / "v23"))
    v23_assets_ready = v23_catalog_ready(asset_root)
    selected_workflow = os.getenv("FLOOD_WORKER_WORKFLOW_VERSION", "v23").lower()
    selected_ready = all(path.is_file() for path in v9_required) if selected_workflow == "v9" else v23_assets_ready
    return {
        "status": "UP" if blender.is_file() and all(path.is_file() for path in v9_required + v23_required) and selected_ready else "DEGRADED",
        "selected_workflow": selected_workflow,
        "blender": str(blender),
        "blender_available": blender.is_file(),
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "v9_source_files_ready": all(path.is_file() for path in v9_required),
        "v23_source_files_ready": all(path.is_file() for path in v23_required),
        "v23_asset_root": str(asset_root),
        "v23_assets_ready": v23_assets_ready,
    }


@app.post("/api/workflows", status_code=202)
def create_workflow(request: WorkflowRequest):
    workflow_version = request.workflow_version.lower()
    if workflow_version not in {"v9", "v23"}:
        raise HTTPException(422, "workflow_version은 v9 또는 v23이어야 합니다.")
    if workflow_version == "v23" and (not request.user_id or not request.farmland_id):
        raise HTTPException(422, "V23은 user_id와 farmland_id가 필요합니다.")
    if workflow_version == "v23" and not v23_assets_ready(request):
        raise HTTPException(503, "V23 사전 렌더 자산이 없거나 선택한 필지·시나리오를 지원하지 않습니다. scripts/setup_v23.py를 실행하세요.")
    job_id = uuid.uuid4().hex
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in request.storage_name).strip("_")
    job_dir = JOBS_ROOT / f"{safe_name}_{job_id[:8]}"
    cache_key = digital_twin_cache_key(request) if workflow_version == "v9" else v23_asset_selection_key(request)
    cache_dir = digital_twin_asset_dir(request) if workflow_version == "v9" else None
    job = {
        "job_id": job_id,
        "status": "QUEUED",
        "stage": "queued",
        "message": "팀 디지털 트윈 워크플로 실행 대기",
        "progress": 0,
        "storage_name": safe_name,
        "workflow_version": workflow_version,
        "v23_field_profile_id": effective_v23_field_id(request) if workflow_version == "v23" else None,
        "source_farmland_id": request.farmland_id,
        "result_url": None,
        "result_path": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "job_dir": str(job_dir),
        "cache": (
            "HIT" if workflow_version == "v23" and v23_assets_ready(request)
            else "HIT" if (cache_dir / "digital-twin-base.mp4").is_file() and (cache_dir / "base-render-report.json").is_file()
            else "MISS"
        ),
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
    for source in log_sources():
        path = resolve_log_path(job, source)
        logs[source] = {
            "available": path.is_file(),
            "size": path.stat().st_size if path.is_file() else 0,
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else None,
        }
    created = datetime.fromisoformat(job["created_at"])
    terminal = job["status"] in {"DONE", "FAILED"}
    elapsed_end = datetime.fromisoformat(job["updated_at"]) if terminal else datetime.now(timezone.utc)
    return {
        **public_job(job),
        "elapsed_seconds": max(0, int((elapsed_end - created).total_seconds())),
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
    if source not in log_sources():
        raise HTTPException(400, "지원하지 않는 로그 종류입니다.")
    path = resolve_log_path(job, source)
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
    if request.workflow_version.lower() == "v23":
        run_v23_workflow(job_id, request, job_dir)
    else:
        run_v9_workflow(job_id, request, job_dir)


def run_v9_workflow(job_id: str, request: WorkflowRequest, job_dir: Path):
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


def run_v23_workflow(job_id: str, request: WorkflowRequest, job_dir: Path):
    try:
        event_path = job_dir / "event_v23.json"
        output_root = job_dir / "workspace" / "output" / "guidance_v23"
        progress_file = job_dir / "progress.json"
        event_path.parent.mkdir(parents=True, exist_ok=True)
        event_path.write_text(json.dumps(v23_event(request), ensure_ascii=False, indent=2), encoding="utf-8")
        update(job_id, status="RUNNING", stage="event_validation", message="V23 이벤트·농경지 소유권 확인 중", progress=5)
        env = os.environ.copy()
        env.update({
            "FLOOD_PROGRESS_FILE": str(progress_file),
            "V23_OUTPUT_ROOT": str(job_dir / "workspace" / "output"),
            "V23_ASSET_ROOT": os.getenv("V23_ASSET_ROOT", str(SERVICE_ROOT / "runtime_assets" / "v23")),
            "BLENDER_BIN": os.getenv("BLENDER_BIN", os.getenv("BLENDER_EXECUTABLE", "/Applications/Blender.app/Contents/MacOS/Blender")),
        })
        log_path = job_dir / "workflow.log"
        process = subprocess.Popen(
            [sys.executable, str(SERVICE_ROOT / "agents" / "guidance_v23_workflow.py"), "--event", str(event_path), "--mode", "production", "--output-root", str(output_root)],
            cwd=SERVICE_ROOT,
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
        final_state_paths = list(output_root.glob("*/workflow_final_state.json"))
        final_state = json.loads(final_state_paths[0].read_text(encoding="utf-8")) if len(final_state_paths) == 1 else {}
        final_video = Path(final_state["final_video"]) if final_state.get("final_video") else None
        if returncode != 0 or final_video is None or not final_video.is_file():
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-1500:] if log_path.is_file() else ""
            raise RuntimeError(f"팀 V23 워크플로 실패. 상세 로그: {log_path}. 원인: {tail[-700:]}")
        update(
            job_id,
            status="DONE",
            stage="completed",
            message="V23 농경지 맞춤형 디지털 트윈·멀티 Agent 영상 제작 완료",
            progress=100,
            result_url=f"/api/workflows/{job_id}/video",
            result_path=str(final_video),
        )
    except Exception as exc:
        job = jobs[job_id]
        refresh_progress(job)
        update(job_id, status="FAILED", message=f"{job.get('message', 'V23 영상 워크플로')} 단계에서 실패", error=str(exc))


def v23_event(request: WorkflowRequest) -> dict:
    triggered = request.triggered_at
    profile_field_id = effective_v23_field_id(request)
    profile_user_id = effective_v23_user_id(request)
    return {
        "schema_version": "1.0",
        "event_type": "flood_guidance_requested",
        "event_id": request.alert_id,
        "user_id": profile_user_id,
        "field_id": profile_field_id,
        "scenario_id": request.scenario_version if request.scenario_version in {"caution"} else "caution",
        "triggered_at": triggered,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "source": {"system_id": "farmer-flood-trigger-service", "trigger_version": "v1"},
        "forecast_summary": {
            "rain_24h_mm": request.forecast_rainfall_mm,
            "summary_text": f"24시간 예상 강수량 {request.forecast_rainfall_mm:g}mm",
        },
        "hydrology_summary": {
            "station_id": request.station_code,
            "observed_at": triggered,
            "water_level_m": request.water_level_meters,
            "alert_level": request.risk_level,
        },
        "metadata": {
            "station_name": request.station_name,
            "address": request.address,
            "grid": {"nx": request.nx, "ny": request.ny},
            "farmer_name": request.farmer_name,
            "source_user_id": request.user_id,
            "source_farmland_id": request.farmland_id,
            "visual_profile_mode": "region_shared_sokrisan_base" if "속리산면" in request.address else ("configured_v23_demo_profile" if request.v23_field_profile_id else "native_v23_registry"),
        },
    }


def v23_asset_selection_key(request: WorkflowRequest) -> str:
    visual_key = "KR-CHUNGBUK-BOEUN-SOKRISAN" if "속리산면" in request.address else effective_v23_field_id(request)
    identity = f"v23-assets-1.0.0:{visual_key}:{request.scenario_version}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def effective_v23_field_id(request: WorkflowRequest) -> str | None:
    return request.v23_field_profile_id or request.farmland_id


def effective_v23_user_id(request: WorkflowRequest) -> str | None:
    return request.v23_profile_user_id or request.user_id


def v23_assets_ready(request: WorkflowRequest) -> bool:
    try:
        catalog = json.loads((SERVICE_ROOT / "config" / "runtime_assets_v23.json").read_text(encoding="utf-8"))
        if request.scenario_version != "caution":
            return False
        root = Path(os.getenv("V23_ASSET_ROOT", SERVICE_ROOT / "runtime_assets" / "v23"))
        if "속리산면" in request.address:
            region = catalog["region_shared_visuals"]["KR-CHUNGBUK-BOEUN-SOKRISAN"]
            item = next(item for item in catalog["assets"] if item["asset_id"] == region["asset"])
            return (root / item["relative_path"]).is_file()
        selection = catalog["selection_by_field_id"][effective_v23_field_id(request)]
        asset_ids = {
            catalog["shared"]["common_background"],
            catalog["shared"]["shelter_flood"],
            catalog["shared"]["shelter_overlay"],
            selection["field_background"],
            selection["field_overlay"],
            selection["field_flood"],
        }
        relative_paths = {item["asset_id"]: item["relative_path"] for item in catalog["assets"]}
        return all((root / relative_paths[asset_id]).is_file() for asset_id in asset_ids)
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


def v23_catalog_ready(root: Path) -> bool:
    try:
        catalog = json.loads((SERVICE_ROOT / "config" / "runtime_assets_v23.json").read_text(encoding="utf-8"))
        return all((root / item["relative_path"]).is_file() for item in catalog["assets"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


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
        "personalized_visual": None,
    }


def resolve_log_path(job: dict, source: str) -> Path:
    job_dir = Path(job["job_dir"])
    if job.get("workflow_version") == "v23":
        logs = list((job_dir / "workspace/output/guidance_v23").glob("*/logs"))
        if logs:
            if source == "composition":
                return logs[0] / "final_composition.log"
            if source in {"base_render", "personalized_visual"}:
                return logs[0] / "personalized_visual_composition.log"
    relative = log_sources().get(source)
    return job_dir / relative if relative is not None else job_dir / "unavailable.log"


STAGES = {
    "event_validation": (8, "V23 이벤트·농경지 소유권 확인"),
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
    "video_production_agent_running": (55, "V23 필지별 캐시 영상 합성 중"),
    "video_production_agent": (75, "V23 필지별 영상·안내 카드 준비 완료"),
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
            candidates = [path.parent / "workspace/output/guidance_v9/gangnae_guidance_v9_60s.mp4"]
            candidates.extend((path.parent / "workspace/output/guidance_v23").glob("*/*_guidance_v23.mp4"))
            final_video = next((candidate for candidate in candidates if candidate.is_file() and candidate.stat().st_size >= 100_000), None)
            if final_video is not None:
                job.update(status="DONE",stage="completed",message="재시작 후 완성 영상 복구",progress=100,result_url=f"/api/workflows/{job['job_id']}/video",result_path=str(final_video))
            elif job.get("status") in {"QUEUED","RUNNING"}:
                job.update(status="FAILED",message="Worker 재시작으로 중단된 작업",error="작업 프로세스가 종료되었습니다. 다시 실행해야 합니다.")
            jobs[job["job_id"]] = job
            persist_job(job)
        except (OSError,ValueError,KeyError) as exc:
            print(f"[worker-recovery] skipped {path}: {exc}",flush=True)


recover_jobs()
