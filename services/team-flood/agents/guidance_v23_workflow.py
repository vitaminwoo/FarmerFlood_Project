"""V23 four-agent workflow for event-driven personalized flood guidance."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Dict, List

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI
from typing_extensions import TypedDict

import runtime_utils
from runtime_config import ROOT, blender_binary, output_root
from v23_event_contract import load_and_validate_event, validate_event
from v23_field_registry import FieldRegistry
from guidance_rag import compact_citations, dump_retrieval, retrieve_guidance, select_source_sentence
from guidance_slide_template import SLIDE_DESIGN_SYSTEM_PROMPT, render_guidance_slide
from v23_personalized_visual_builder import build_personalized_visual_plan
from v23_runtime_asset_catalog import RuntimeAssetCatalog


DEFAULT_EVENT = ROOT / "data" / "v23" / "events" / "valid_forecast_and_hydrology.json"
DEFAULT_OUTPUT_ROOT = output_root() / "guidance_v23"
PERSONALIZED_ROOT = output_root() / "personalized_visuals" / "v23"
VISUAL_COMPOSER = ROOT / "blender" / "compose_personalized_visual_v23.py"
VISUAL_AUDITOR = ROOT / "blender" / "audit_personalized_visual_v23.py"
FINAL_COMPOSER = ROOT / "blender" / "compose_guidance_video_v23.py"
FPS = 16
PERSONALIZED_VISUAL_END = 960
FRAME_END = 1280
PROGRESS_PATH = Path(os.getenv("FLOOD_PROGRESS_FILE", DEFAULT_OUTPUT_ROOT / "progress.json"))

SCRIPT_RAG_SYSTEM_PROMPT = """당신은 농업인 호우 안내 대본의 근거 선택기다.
사용자·필지·예보 수치는 이벤트 데이터만 사용한다. 행동요령은 제공된 RAG 검색 결과에서 문맥에 맞는 문구를 우선 선택한다.
검색 근거에 없는 새 수치, 기관 지시, 대피소 운영 여부를 만들지 않는다. 비가 시작된 뒤 위험지역 점검을 권하지 않는다.
짧고 명확한 존댓말 명령형으로 다듬되 의미를 바꾸지 않고, 선택한 문구의 source_id와 page_number를 결과에 남긴다."""


class StoryState(TypedDict, total=False):
    run_id: str
    mode: str
    event_path: str
    event: Dict[str, Any]
    field: Dict[str, Any]
    run_dir: str
    segments: List[Dict[str, Any]]
    tts_assets: Dict[str, Dict[str, Any]]
    tts_meta: Dict[str, Any]
    visual_assets: Dict[str, str]
    manifest: Dict[str, Any]
    final_video: str
    trace: List[Dict[str, Any]]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_progress(stage: str, detail: Dict[str, Any] | None = None) -> None:
    payload = {
        "status": "RUNNING",
        "stage": stage,
        "detail": detail or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PROGRESS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(PROGRESS_PATH)
    print(f"[{stage}] {json.dumps(payload['detail'], ensure_ascii=False)}", flush=True)


def traced(state: StoryState, node: str, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    publish_progress(node, detail)
    return [*state.get("trace", []), {"node": node, "status": "ok", **detail}]


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def safe_run_id(event: Dict[str, Any]) -> str:
    identity = f"{event['event_id']}:{event['user_id']}:{event['field_id']}:{event['scenario_id']}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    return f"V23-{slug(event['event_id'])}-{suffix}"


def output_field_id(event: Dict[str, Any], field: Dict[str, Any]) -> str:
    return event.get("metadata", {}).get("source_farmland_id") or field["field_id"]


def segment(identifier: str, start: int, end: int, title: str, subtitle: str, narration: str, visual_key: str) -> Dict[str, Any]:
    return {
        "id": identifier,
        "start_frame": start,
        "end_frame": end,
        "duration_seconds": (end - start + 1) / FPS,
        "title": title,
        "subtitle": subtitle,
        "narration": narration,
        "visual_key": visual_key,
        "visual_type": "dynamic_video" if visual_key == "personalized_visual" else "information_card",
    }


def build_segments(event: Dict[str, Any], field: Dict[str, Any]) -> List[Dict[str, Any]]:
    forecast = event["forecast_summary"]
    hydro = event["hydrology_summary"]
    metrics = field["derived_metrics"]
    shelter = field["shelter"]
    rain = float(forecast["rain_24h_mm"])
    level = float(hydro["water_level_m"])
    overlap = float(metrics["official_flood_intersection_percent"])
    region_visual = RuntimeAssetCatalog.load().select_region(event.get("metadata", {}).get("address"))
    is_sokrisan_shared = bool(region_visual and region_visual["region_id"] == "KR-CHUNGBUK-BOEUN-SOKRISAN")
    field_name = "속리산면 등록 농경지" if is_sokrisan_shared else field["display_name"]
    shelter_name = shelter["name"]
    distance_km = float(shelter["distance_m"]) / 1000.0
    flood_narration = (
        "속리산면 등록 농경지는 집중호우 때 침수 위험이 있습니다. 비가 오기 전에 배수로와 막힌 곳을 확인하고 농기계를 안전한 장소로 옮기십시오."
        if is_sokrisan_shared else
        f"환경부 100년 빈도 홍수위험 범위와 등록 농경지 경계는 약 {overlap:.1f} 퍼센트 겹칩니다. 비가 오기 전에 배수로와 막힌 곳을 확인하고 농기계를 안전한 장소로 옮기십시오."
    )
    shelter_narration = (
        "이동이 필요하면 안전디딤돌이나 보은군의 공식 안내에서 가까운 재해구호시설의 개방 여부와 도로 통제 상황을 먼저 확인하십시오."
        if is_sokrisan_shared else
        f"화면에 표시된 곳은 등록 농경지에서 약 {distance_km:.1f} 킬로미터 떨어진 {shelter_name}입니다. 이동이 필요하면 비가 오기 전에 시설 개방 여부와 도로 통제 상황을 확인하십시오."
    )
    segments = [
        segment(
            "regional_flood", 1, 160,
            "등록 농경지 호우 대비 안내", f"24시간 예상 강수 {rain:.0f}mm",
            f"{field_name} 주변 안내입니다. 기상예보에는 24시간 {rain:.0f} 밀리미터의 비가 예상됩니다. 화면에서 하천 주변 물의 확산 범위를 확인하십시오.",
            "personalized_visual",
        ),
        segment(
            "field_focus", 161, 320,
            "등록 농경지 위치", "범람 이전 상태에서 농경지로 이동",
            f"화면이 범람 이전으로 돌아간 뒤 등록 농경지를 확대합니다. 관측소 수위는 {level:.2f} 미터로 전달됐으며, 계속 갱신되는 기상청과 홍수통제소 정보를 함께 확인해야 합니다.",
            "personalized_visual",
        ),
        segment(
            "field_flood", 321, 480,
            "농경지 침수 위험", "집중호우 침수 위험" if is_sokrisan_shared else f"공식 위험범위 중첩 {overlap:.1f}%",
            flood_narration,
            "personalized_visual",
        ),
        segment(
            "field_final_state", 481, 640,
            "비가 시작되기 전 조치", "농기계 이동 · 시설물 고정",
            "비닐하우스와 지주시설의 결박 상태를 확인하고 이동 가능한 물건은 높은 곳으로 옮기십시오. 안전조치는 반드시 비가 시작되기 전에 마쳐야 합니다.",
            "personalized_visual",
        ),
        segment(
            "shelter_location", 641, 800,
            "가까운 재해구호시설", "공식 개방 정보 확인" if is_sokrisan_shared else shelter_name,
            shelter_narration,
            "personalized_visual",
        ),
        segment(
            "before_rain_card", 801, 960,
            "비 오기 전", "배수로 · 농기계 · 시설물 점검",
            "배수로 확인, 농기계 이동, 시설물 고정은 비가 오기 전에 마치십시오.",
            "before_rain_card",
        ),
        segment(
            "during_rain_card", 961, 1120,
            "비 오는 중", "논밭 · 하천 · 배수로 접근 금지",
            "논 물꼬 조정, 용·배수로 점검 등 야외활동은 하지 맙시다.",
            "during_rain_card",
        ),
        segment(
            "after_rain_card", 1121, 1280,
            "비 그친 후", "안전 확인 · 피해 기록",
            "비가 그친 뒤에도 바로 농경지에 들어가지 마십시오. 물이 빠지고 주변이 안전한지 확인한 뒤 피해 상황을 사진으로 남기십시오.",
            "after_rain_card",
        ),
    ]
    retrieval_specs = {
        "field_flood": ("농경지 침수 예방 배수로 농기계 비 오기 전", ["농경지", "배수로", "농기계", "점검"]),
        "field_final_state": ("비닐하우스 농업시설물 지주 결박 고정 강풍 호우 사전", ["시설", "지주", "고정", "비닐하우스"]),
        "before_rain_card": ("호우 전 농경지 배수로 농기계 시설물 미리 점검 이동", ["배수로", "농기계", "시설물", "미리"]),
        "during_rain_card": ("호우 중 논둑 물꼬 배수로 야외활동 접근 금지", ["논둑", "물꼬", "배수로", "야외활동"]),
        "after_rain_card": ("호우가 지나간 후 농경지 안전 확인 피해 사진 기록", ["지나간 후", "안전", "피해", "사진"]),
    }
    for item in segments:
        spec = retrieval_specs.get(item["id"])
        if not spec:
            item["rag"] = {"query": None, "selected_phrase": None, "citations": []}
            continue
        query, keywords = spec
        results = retrieve_guidance(query, limit=5)
        item["rag"] = {
            "query": query,
            "selected_phrase": select_source_sentence(results, keywords=keywords, fallback=item["narration"]),
            "citations": compact_citations(results),
        }
        if results and item["id"] == "during_rain_card":
            item["narration"] = item["rag"]["selected_phrase"]
    return segments


def script_agent(state: StoryState) -> Dict[str, Any]:
    segments = build_segments(state["event"], state["field"])
    retrieval_path = Path(state["run_dir"]) / "rag_retrieval.json"
    dump_retrieval(retrieval_path, {
        "system_prompt": SCRIPT_RAG_SYSTEM_PROMPT,
        "segments": [{"segment_id": item["id"], **item["rag"]} for item in segments],
    })
    citation_count = sum(len(item["rag"]["citations"]) for item in segments)
    return {
        "segments": segments,
        "trace": traced(state, "script_agent", {
            "provider": "v23_event_plus_sqlite_fts_rag",
            "segment_count": len(segments),
            "rag_citation_count": citation_count,
            "rag_retrieval": str(retrieval_path),
            "tts_starts_at_first_frame": segments[0]["start_frame"] == 1,
            "duration_seconds": FRAME_END / FPS,
        }),
    }


async def tts_agent(state: StoryState) -> Dict[str, Any]:
    publish_progress("tts_agent_running", {"segment_count": len(state["segments"])})
    if state["mode"] == "plan":
        assets = {
            item["id"]: {"path": None, "bytes": 0, "provider": "planned", "assigned_duration_seconds": item["duration_seconds"]}
            for item in state["segments"]
        }
        meta = {"generation_mode": "plan_only", "request_count": 0, "provider_counts": {"planned": len(assets)}}
        return {"tts_assets": assets, "tts_meta": meta, "trace": traced(state, "tts_agent", meta)}
    audio_dir = Path(state["run_dir"]) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    voice = os.getenv("OPENAI_TTS_VOICE", "alloy")
    speed = float(os.getenv("OPENAI_TTS_SPEED_V23", os.getenv("OPENAI_TTS_SPEED_V18", "1.12")))
    client = AsyncOpenAI(timeout=90.0, max_retries=0) if os.getenv("OPENAI_API_KEY") else None
    started = perf_counter()
    try:
        results = await asyncio.gather(*[
            runtime_utils.generate_tts_segment(client, model, voice, speed, audio_dir, index, item)
            for index, item in enumerate(state["segments"], start=1)
        ])
    finally:
        if client is not None:
            await client.close()
    assets: Dict[str, Dict[str, Any]] = {}
    counts = {"openai": 0, "macos_say": 0}
    fallbacks = {}
    for identifier, asset, fallback in results:
        duration = runtime_utils.read_audio_duration_seconds(Path(asset["path"]))
        assigned = float(asset["assigned_duration_seconds"])
        asset["source_duration_seconds"] = round(duration, 3)
        asset["cropped_seconds"] = round(max(0.0, duration - assigned), 3)
        assets[identifier] = asset
        counts[asset["provider"]] += 1
        if fallback:
            fallbacks[identifier] = fallback
    meta = {
        "model": model,
        "voice": voice,
        "generation_mode": "async_parallel",
        "request_count": len(results),
        "provider_counts": counts,
        "fallback_types": fallbacks,
        "audio_crop_policy": "forced_to_segment_end_frame",
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    return {"tts_assets": assets, "tts_meta": meta, "trace": traced(state, "tts_agent", meta)}


def ensure_personalized_visual(state: StoryState) -> Dict[str, Any]:
    event = state["event"]
    field = state["field"]
    region_visual = RuntimeAssetCatalog.load().select_region(event.get("metadata", {}).get("address"))
    if region_visual:
        path = Path(region_visual["asset"]["path"])
        if not path.is_file():
            raise RuntimeError(f"Region shared digital twin is missing: {path}")
        return {
            "status": "ready",
            "video": str(path),
            "report": None,
            "reused": True,
            "visual_scope": "region_shared",
            **{key: region_visual[key] for key in ("region_id", "source_frames", "source_fps", "source_duration_seconds", "timeline_policy")},
        }
    run_dir = PERSONALIZED_ROOT / slug(event["event_id"])
    plan_path = run_dir / "composition_plan_v23.json"
    report_path = run_dir / "composition_report_v23.json"
    video_path = run_dir / f"{slug(field['field_id'])}_personalized_visual_v23.mp4"
    if state["mode"] == "plan":
        return {"status": "planned", "video": str(video_path), "report": str(report_path), "reused": False}
    reusable = False
    if report_path.is_file() and video_path.is_file():
        report = read_json(report_path)
        audit = report.get("decoder_audit", {})
        reusable = (
            report.get("event_id") == event["event_id"]
            and report.get("field_id") == field["field_id"]
            and audit.get("status") == "passed"
            and report.get("video_bytes") == video_path.stat().st_size
        )
    if not reusable:
        plan = build_personalized_visual_plan(event, output_root=PERSONALIZED_ROOT)
        write_json(plan_path, plan)
        logs = Path(state["run_dir"]) / "logs"
        runtime_utils.run_logged(
            [str(blender_binary()), "--background", "--python", str(VISUAL_COMPOSER), "--", "--plan", str(plan_path)],
            ROOT, logs / "personalized_visual_composition.log",
        )
        runtime_utils.run_logged(
            [str(blender_binary()), "--background", "--python", str(VISUAL_AUDITOR), "--", "--report", str(report_path)],
            ROOT, logs / "personalized_visual_audit.log",
        )
    report = read_json(report_path)
    if report.get("decoder_audit", {}).get("status") != "passed":
        raise RuntimeError("V23 personalized visual did not pass the structural audit")
    return {"status": "ready", "video": str(video_path), "report": str(report_path), "reused": reusable}


def video_production_agent(state: StoryState) -> Dict[str, Any]:
    publish_progress("video_production_agent_running", {"field_id": state["field"]["field_id"]})
    run_dir = Path(state["run_dir"])
    visuals_dir = run_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)
    visual = ensure_personalized_visual(state)
    delivery_field_id = output_field_id(state["event"], state["field"])
    before_card = visuals_dir / "01_before_rain.png"
    during_card = visuals_dir / "02_during_rain.png"
    after_card = visuals_dir / "03_after_rain.png"
    if state["mode"] != "plan":
        render_guidance_slide(
            before_card, phase="before", title="미리 준비하세요",
            summary="알림을 받으면, 비가 오기 전에 끝내세요.",
            actions=["배수로·물꼬 정리", "농기계는 높은 곳으로 이동", "시설물 점검·보강"],
            icons=["💧", "🚜", "🔧"], banner="비가 오기 전 준비가 가장 중요합니다.",
        )
        render_guidance_slide(
            during_card, phase="during", title="논·밭에 가지 마세요",
            summary="농작물이 걱정돼도 지금은 사람이 먼저입니다.",
            actions=["논둑·물꼬 확인 금지", "하천·배수로 접근 금지", "위험하면 즉시 대피"],
            icons=["🚫", "🚫", "🏃"], banner="농작물보다 사람의 안전이 먼저입니다.",
        )
        render_guidance_slide(
            after_card, phase="after", title="바로 들어가지 마세요",
            summary="물이 빠지고 주변이 안전한지 먼저 확인하세요.",
            actions=["주변 안전 먼저 확인", "물이 빠진 뒤 농경지 확인", "피해 사진 남기기"],
            icons=["👀", "🌊", "📷"], banner="준비하기 · 가지 않기 · 안전 확인하기",
        )
    visual_assets = {
        "personalized_visual": visual["video"],
        "before_rain_card": str(before_card),
        "during_rain_card": str(during_card),
        "after_rain_card": str(after_card),
    }
    enriched = []
    subtitles: List[str] = []
    for index, item in enumerate(state["segments"], start=1):
        audio = state["tts_assets"][item["id"]]
        enriched.append({**item, "visual_path": visual_assets[item["visual_key"]], "audio_path": audio["path"], "audio_provider": audio["provider"]})
        subtitles.extend([str(index), f"{runtime_utils.srt_time((item['start_frame'] - 1) / FPS)} --> {runtime_utils.srt_time(item['end_frame'] / FPS)}", item["narration"], ""])
    manifest = {
        "schema_version": "1.0",
        "workflow_version": "V23",
        "run_id": state["run_id"],
        "mode": state["mode"],
        "event_id": state["event"]["event_id"],
        "field_id": state["field"]["field_id"],
        "source_farmland_id": state["event"].get("metadata", {}).get("source_farmland_id"),
        "user_id": state["event"]["user_id"],
        "scenario_id": state["event"]["scenario_id"],
        "fps": FPS,
        "resolution": [1280, 720],
        "frame_start": 1,
        "frame_end": FRAME_END,
        "personalized_visual_end_frame": PERSONALIZED_VISUAL_END,
        "duration_seconds": FRAME_END / FPS,
        "visual_mode": "v23_field_specific_cached_visual_plus_information_cards",
        "slide_design_prompt": SLIDE_DESIGN_SYSTEM_PROMPT,
        "base_render_policy": "cached_personalized_visual_reuse_no_3d_rerender",
        "personalized_visual": visual,
        "segments": enriched,
        "tts_meta": state["tts_meta"],
        "output_video": str(run_dir / f"{slug(delivery_field_id)}_guidance_v23.mp4"),
        "output_blend": str(run_dir / f"{slug(delivery_field_id)}_guidance_v23_composition.blend"),
    }
    write_json(run_dir / "guidance_manifest.json", manifest)
    (run_dir / "narration_script.txt").write_text("\n\n".join(f"[{item['title']}]\n{item['narration']}" for item in enriched), encoding="utf-8")
    (run_dir / "guidance_subtitles.srt").write_text("\n".join(subtitles), encoding="utf-8")
    return {
        "visual_assets": visual_assets,
        "manifest": manifest,
        "trace": traced(state, "video_production_agent", {"visual_reused": visual["reused"], "segment_count": len(enriched), "full_3d_rerender": False}),
    }


def composition_agent(state: StoryState) -> Dict[str, Any]:
    publish_progress("composition_agent_running")
    run_dir = Path(state["run_dir"])
    manifest_path = run_dir / "guidance_manifest.json"
    if state["mode"] == "plan":
        trace = traced(state, "composition_agent", {"mode": "plan", "rendered": False})
        write_json(run_dir / "workflow_final_state.json", {"status": "planned", "run_id": state["run_id"], "final_video": None, "trace": trace})
        return {"final_video": "", "trace": trace}
    started = perf_counter()
    runtime_utils.run_logged(
        [str(blender_binary()), "--background", "--python", str(FINAL_COMPOSER), "--", "--manifest", str(manifest_path)],
        ROOT, run_dir / "logs" / "final_composition.log",
    )
    video = Path(state["manifest"]["output_video"])
    if not video.is_file() or video.stat().st_size < 100_000 or b"ftyp" not in video.read_bytes()[:32]:
        raise RuntimeError("V23 final guidance MP4 is missing or invalid")
    trace = traced(state, "composition_agent", {"mode": state["mode"], "rendered": True, "elapsed_seconds": round(perf_counter() - started, 3), "full_3d_rerender": False})
    write_json(run_dir / "workflow_final_state.json", {"status": "completed", "run_id": state["run_id"], "final_video": str(video), "video_bytes": video.stat().st_size, "trace": trace})
    return {"final_video": str(video), "trace": trace}


def build_graph():
    builder = StateGraph(StoryState)
    for name, function in [
        ("script_agent", script_agent),
        ("tts_agent", tts_agent),
        ("video_production_agent", video_production_agent),
        ("composition_agent", composition_agent),
    ]:
        builder.add_node(name, function)
    builder.add_edge(START, "script_agent")
    builder.add_edge("script_agent", "tts_agent")
    builder.add_edge("tts_agent", "video_production_agent")
    builder.add_edge("video_production_agent", "composition_agent")
    builder.add_edge("composition_agent", END)
    return builder.compile()


async def run_workflow_event(event: Dict[str, Any], mode: str, output_root: Path, event_path: Path | None = None) -> Dict[str, Any]:
    event = validate_event(event)
    field = FieldRegistry.load().resolve_event(event)
    run_id = safe_run_id(event)
    run_dir = output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    (run_dir / "langgraph_structure.mmd").write_text(graph.get_graph().draw_mermaid(), encoding="utf-8")
    result = await graph.ainvoke({"run_id": run_id, "mode": mode, "event_path": str(event_path) if event_path else None, "event": event, "field": field, "run_dir": str(run_dir), "trace": []})
    return {
        "status": "planned" if mode == "plan" else "completed",
        "run_id": run_id,
        "event_id": event["event_id"],
        "field_id": field["field_id"],
        "final_video": result.get("final_video") or None,
        "manifest": str(run_dir / "guidance_manifest.json"),
        "trace_nodes": [item["node"] for item in result["trace"]],
        "tts_meta": result["tts_meta"],
    }


async def run_workflow(event_path: Path, mode: str, output_root: Path) -> Dict[str, Any]:
    event_path = event_path.resolve()
    return await run_workflow_event(load_and_validate_event(event_path), mode, output_root, event_path=event_path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, default=DEFAULT_EVENT)
    parser.add_argument("--mode", choices=["plan", "staging", "production"], default="staging")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


async def main():
    args = parse_args()
    load_dotenv(ROOT / ".env")
    result = await run_workflow(args.event, args.mode, args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
