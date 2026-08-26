from __future__ import annotations

import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from dotenv import load_dotenv

try:
    from .pipeline import WarningVideoPipeline, create_dry_run_plan
except ImportError:  # warning_video_agents 폴더에서 uvicorn app:app 실행 시
    from pipeline import WarningVideoPipeline, create_dry_run_plan

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
jobs: dict[str, dict] = {}
lock = threading.Lock()
app = FastAPI(title="경고 영상 멀티에이전트")


@app.get("/", response_class=HTMLResponse)
def home():
    """멀티에이전트 임시 확인 화면을 반환한다."""
    return HTMLResponse((ROOT / "index.html").read_text(encoding="utf-8"))


@app.post("/api/jobs", status_code=202)
async def create_job(background: BackgroundTasks, location: str = Form(...), farmer_name: str = Form(...), storage_name: str = Form(""), mode: str = Form("actual"), video: UploadFile = File(...)):
    """녹화 영상을 저장하고 실제 LangGraph 작업을 등록한다."""
    if mode != "mock" and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "OPENAI_API_KEY가 설정되지 않았습니다.")
    job_id = uuid.uuid4().hex
    safe_storage_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in storage_name).strip("_")
    work_dir = OUTPUT / (safe_storage_name or job_id)
    work_dir.mkdir(parents=True)
    suffix = Path(video.filename or "recording.mp4").suffix or ".mp4"
    source = work_dir / f"recording{suffix}"
    with source.open("wb") as target:
        while chunk := await video.read(1024 * 1024):
            target.write(chunk)
    jobs[job_id] = {"job_id": job_id, "status": "QUEUED", "message": "실행 대기 중", "result_url": None, "error": None}
    if mode == "mock":
        background.add_task(run_mock_job, job_id, source, work_dir)
    else:
        background.add_task(run_job, job_id, source, location.strip(), farmer_name.strip(), work_dir)
    return jobs[job_id]


@app.get("/api/preview")
def preview(location: str, farmer_name: str):
    """API 호출 없는 LangGraph dry-run 결과를 반환한다."""
    return create_dry_run_plan(location.strip(), farmer_name.strip())


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    """지정한 영상 제작 작업의 현재 상태를 반환한다."""
    if job_id not in jobs:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    return jobs[job_id]


@app.get("/api/jobs/{job_id}/video")
def get_video(job_id: str):
    """완성된 경고 영상을 MP4 파일로 반환한다."""
    job = jobs.get(job_id)
    path = Path(job["result_path"]) if job and job.get("result_path") else None
    if path is None or not path.is_file():
        raise HTTPException(404, "완성된 영상이 없습니다.")
    return FileResponse(path, media_type="video/mp4", filename=f"warning-{job_id}.mp4")


def run_job(job_id: str, source: Path, location: str, farmer_name: str, work_dir: Path):
    """백그라운드에서 실제 LangGraph를 실행하고 작업 상태를 갱신한다."""
    def progress(status: str, message: str):
        """LangGraph 노드 진행 상태를 메모리 작업 정보에 반영한다."""
        with lock:
            jobs[job_id].update(status=status, message=message)
    try:
        result = WarningVideoPipeline().run(source, location, farmer_name, work_dir, progress)
        with lock:
            jobs[job_id].update(status="DONE", message="경고 영상 제작 완료", result_url=f"/api/jobs/{job_id}/video", result_path=str(result))
    except Exception as exc:
        with lock:
            jobs[job_id].update(status="FAILED", message="작업 실패", error=str(exc))


def run_mock_job(job_id: str, source: Path, work_dir: Path):
    """외부 AI 비용 없이 자막을 실제 합성해 Spring→FastAPI 계약을 검증한다."""
    try:
        with lock:
            jobs[job_id].update(status="VIDEO", message="mock 경고 영상 합성 중")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("mock 자막 합성에도 ffmpeg가 필요합니다. ffmpeg를 설치하거나 PATH를 설정하세요.")
        subtitle = work_dir / "mock-subtitles.srt"
        subtitle.write_text("1\n00:00:00,000 --> 00:00:05,000\n[MOCK] 트리거 영상 파이프라인 처리 완료\n", encoding="utf-8")
        result = work_dir / "warning.mp4"
        escaped = str(subtitle.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        command = ["ffmpeg", "-y", "-i", str(source), "-vf", f"subtitles='{escaped}':force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Alignment=2,MarginV=44'", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "copy", "-movflags", "+faststart", str(result)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        with lock:
            jobs[job_id].update(status="DONE", message="mock 경고 영상 제작 완료", result_url=f"/api/jobs/{job_id}/video", result_path=str(result))
    except Exception as exc:
        with lock:
            jobs[job_id].update(status="FAILED", message="mock 작업 실패", error=str(exc))
