from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from openai import OpenAI


@dataclass(frozen=True)
class Scene:
    subtitle: str
    narration: str | None
    silent_seconds: float = 0.0


@dataclass(frozen=True)
class TimelineItem:
    index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    subtitle: str
    narration: str | None
    timing: str


class WarningVideoState(TypedDict, total=False):
    """모든 Agent가 공유하는 경고 영상 작업 상태이다."""

    mode: Literal["dry-run", "actual"]
    job_id: str
    location: str
    farmer_name: str
    source_video: str
    work_dir: str
    scenes: list[dict]
    scripts: list[str]
    script_path: str | None
    audio_paths: list[str | None]
    audio_durations: list[float]
    narration_audio: str | None
    subtitle_path: str | None
    timeline: list[dict]
    ffmpeg_command: list[str]
    output_video: str | None
    current_agent: str
    status: str
    message: str
    logs: list[str]
    tts_logs: list[str]
    error: str | None
    api_called: bool
    notice: str


def base_scenes(location: str, farmer_name: str) -> list[Scene]:
    """사용자 위치와 이름을 적용한 기준 대본 장면을 만든다."""
    return [
        Scene(f"{location} {farmer_name}님 논입니다.", f"{location} {farmer_name}님 논입니다."),
        Scene("청주기상지청이 오늘 오후 4시,\n충북 전역에 호우 예비특보를 발표했습니다.\n내일 새벽부터 최대 200mm가 예상됩니다.", "청주기상지청이 오늘 오후 4시, 충북 전역에 호우 예비특보를 발표했습니다. 내일 새벽부터 최대 200밀리미터가 예상됩니다."),
        Scene("[침수 애니메이션 재생]", None, 2.0),
        Scene("이만큼 비가 오면 어르신 논은\n이 정도까지 물이 찰 수 있습니다.", "이만큼 비가 오면 어르신 논은 이 정도까지 물이 찰 수 있습니다."),
        Scene("(환경부 홍수위험지도를 기준으로 그렸습니다.)", None, 2.0),
        Scene("기상청 행동요령은 이렇게 안내합니다.", "기상청 행동요령은 이렇게 안내합니다."),
        Scene("농경지 용·배수로와 논둑을 정비하고, 물꼬를 조정합니다.\n단, 비가 오기 전에만 조치합니다.", "농경지 용·배수로와 논둑을 정비하고, 물꼬를 조정합니다. 단, 비가 오기 전에만 조치합니다."),
        Scene("지금이 그 시간입니다. 비는 내일 새벽에 시작됩니다.\n오늘 해 있을 때 마치시는 게 좋습니다.", "지금이 그 시간입니다. 비는 내일 새벽에 시작됩니다. 오늘 해 있을 때 마치시는 게 좋습니다."),
        Scene("1. 배수로 정비\n2. 농기계 옮기기\n3. 하우스 결박", "첫째, 배수로 정비. 둘째, 농기계 옮기기. 셋째, 하우스 결박."),
        Scene("내일 새벽 5시경 호우경보 발효가 예상됩니다.", "내일 새벽 5시경 호우경보 발효가 예상됩니다."),
        Scene("기상청 행동요령은 호우특보가 발효된 동안\n‘논둑이나 물꼬를 보러 나가지 않습니다’라고 안내합니다.", "기상청 행동요령은 호우특보가 발효된 동안 논둑이나 물꼬를 보러 나가지 않습니다라고 안내합니다."),
        Scene("내일은 논에 나가지 마십시오. 물은 다시 빠집니다.", "내일은 논에 나가지 마십시오. 물은 다시 빠집니다."),
        Scene("이 영상은 AI가 생성한 참고자료이며\n공식 재난경보를 대체하지 않습니다.\n정확한 정보: 안전디딤돌 앱 · 기상청 · 119", None, 5.0),
    ]


class ScriptAgent:
    """기준 대본을 LLM으로 확인하고 State에 저장하는 Agent이다."""

    def __init__(self, llm: ChatOpenAI | None):
        """실제 실행에 사용할 LangChain LLM을 주입한다."""
        self.llm = llm

    def run(self, state: WarningVideoState) -> dict:
        """위치와 이름이 적용된 장면 및 낭독 대본을 생성한다."""
        expected = base_scenes(state["location"], state["farmer_name"])
        if state["mode"] == "dry-run":
            actual = expected
        else:
            if self.llm is None:
                raise RuntimeError("ScriptAgent의 LLM이 설정되지 않았습니다.")
            system_message = SystemMessage(content=(
                "당신은 농경지 침수 경고 대본 생성 Agent입니다. "
                "모든 답변은 한국어 JSON 배열만 출력합니다."
            ))
            human_message = HumanMessage(content=json.dumps({
                "위치": state["location"],
                "이름": state["farmer_name"],
                "규칙": "주어진 JSON의 문구, 순서, 읽기 여부를 바꾸지 말고 그대로 반환하세요. 다른 설명은 쓰지 마세요.",
                "장면": [asdict(scene) for scene in expected],
            }, ensure_ascii=False))
            response = self.llm.invoke([system_message, human_message])
            try:
                raw = re.sub(r"^```(?:json)?|```$", "", str(response.content).strip()).strip()
                actual = [Scene(**item) for item in json.loads(raw)]
            except (json.JSONDecodeError, TypeError, KeyError) as exc:
                raise RuntimeError("ScriptAgent가 올바른 JSON을 반환하지 않았습니다.") from exc
            if actual != expected:
                raise RuntimeError("ScriptAgent가 기준 문구를 변경했습니다. 안전을 위해 작업을 중단합니다.")

        work_dir = state.get("work_dir")
        script_path = str(Path(work_dir) / "script.json") if work_dir else None
        if script_path:
            Path(script_path).write_text(json.dumps([asdict(scene) for scene in actual], ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "scenes": [asdict(scene) for scene in actual],
            "scripts": [scene.narration for scene in actual if scene.narration],
            "script_path": script_path,
            "api_called": state["mode"] == "actual",
        }


class TtsAgent:
    """State의 낭독 대본을 장면별 음성 및 시간 정보로 바꾸는 Agent이다."""

    def __init__(self, client: OpenAI | None, model: str, voice: str, progress: Callable[[str, str], None] | None = None):
        """실제 실행에 사용할 OpenAI 음성 클라이언트와 설정을 주입한다."""
        self.client, self.model, self.voice = client, model, voice
        self.progress = progress or (lambda *_: None)

    def run(self, state: WarningVideoState) -> dict:
        """각 장면의 음성 파일과 실제 또는 예상 재생 시간을 만든다."""
        scenes = [Scene(**scene) for scene in state["scenes"]]
        audio_paths: list[str | None] = []
        durations: list[float] = []
        audio_dir = Path(state["work_dir"]) / "audio" if state.get("work_dir") else None
        if audio_dir:
            audio_dir.mkdir(parents=True, exist_ok=True)
        tts_logs = []

        for index, scene in enumerate(scenes, 1):
            scene_message = f"TTS Agent 장면 {index}/{len(scenes)} 처리"
            self.progress("TTS", scene_message)
            tts_logs.append(scene_message)
            if scene.narration is None:
                audio_paths.append(None)
                durations.append(scene.silent_seconds)
                continue
            if state["mode"] == "dry-run":
                audio_paths.append(None)
                durations.append(estimate_speech_seconds(scene.narration))
                continue
            if self.client is None or audio_dir is None:
                raise RuntimeError("TtsAgent의 OpenAI 클라이언트 또는 작업 폴더가 없습니다.")
            path = audio_dir / f"scene_{index:02d}.mp3"
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=scene.narration,
                instructions="차분하고 명료한 한국어 재난 안내 음성. 과장하지 말고 천천히 읽습니다.",
            ) as response:
                response.stream_to_file(path)
            audio_paths.append(str(path))
            durations.append(media_duration(path))

        timing = "estimated" if state["mode"] == "dry-run" else "actual"
        timeline = build_timeline(scenes, durations, timing)
        return {
            "audio_paths": audio_paths,
            "audio_durations": durations,
            "timeline": [asdict(item) for item in timeline],
            "tts_logs": tts_logs,
            "notice": "음성 생성 전 예상 시간입니다. 실제 실행에서는 생성된 MP3 길이를 ffprobe로 측정합니다." if state["mode"] == "dry-run" else "생성된 MP3의 실제 길이입니다.",
        }


class VideoAgent:
    """State의 영상, 음성, 자막을 FFmpeg로 합성하는 Agent이다."""

    def run(self, state: WarningVideoState) -> dict:
        """합성 명령을 기록하고 실제 모드에서는 최종 MP4를 렌더링한다."""
        dry_run = state["mode"] == "dry-run"
        work_dir = Path(state["work_dir"]) if state.get("work_dir") else None
        source_video = Path(state["source_video"]) if state.get("source_video") else Path("<digital-twin-recording.mp4>")
        narration_audio = work_dir / "narration.wav" if work_dir else Path("<narration.wav>")
        subtitle_path = work_dir / "subtitles.srt" if work_dir else Path("<subtitles.srt>")
        output_video = work_dir / "warning.mp4" if work_dir else Path("<warning.mp4>")
        command = self.build_final_command(source_video, narration_audio, subtitle_path, output_video)
        if dry_run:
            return {
                "narration_audio": None,
                "subtitle_path": None,
                "ffmpeg_command": command,
                "output_video": None,
            }

        require_command("ffmpeg")
        require_command("ffprobe")
        scenes = [Scene(**scene) for scene in state["scenes"]]
        audio = [(Path(path) if path else None, duration) for path, duration in zip(state["audio_paths"], state["audio_durations"])]
        self._join_audio(audio, narration_audio)
        self._write_srt(scenes, audio, subtitle_path)
        run_command(command)
        return {
            "narration_audio": str(narration_audio),
            "subtitle_path": str(subtitle_path),
            "ffmpeg_command": command,
            "output_video": str(output_video),
        }

    @staticmethod
    def build_final_command(source_video: Path, audio_path: Path, subtitle_path: Path, output_path: Path) -> list[str]:
        """최종 영상 렌더링에 사용할 FFmpeg 명령을 만든다."""
        subtitle_filter = f"subtitles='{escape_filter_path(subtitle_path)}':force_style='FontSize=20,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=48'"
        return [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(source_video), "-i", str(audio_path),
            "-vf", subtitle_filter, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
            "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", "-movflags", "+faststart", str(output_path),
        ]

    @staticmethod
    def _join_audio(audio: list[tuple[Path | None, float]], output: Path) -> None:
        """장면별 음성과 무음 구간을 하나의 WAV 파일로 연결한다."""
        inputs, filters, labels = [], [], []
        for index, (path, duration) in enumerate(audio):
            if path:
                inputs += ["-i", str(path)]
                filters.append(f"[{index}:a]aresample=44100,aformat=channel_layouts=mono[a{index}]")
            else:
                inputs += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=r=44100:cl=mono"]
                filters.append(f"[{index}:a]anull[a{index}]")
            labels.append(f"[a{index}]")
        filters.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]")
        run_command(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", str(output)])

    @staticmethod
    def _write_srt(scenes: list[Scene], audio: list[tuple[Path | None, float]], output: Path) -> None:
        """장면별 실제 음성 길이를 이용해 SRT 자막을 작성한다."""
        cursor, blocks = 0.0, []
        for index, (scene, (_, duration)) in enumerate(zip(scenes, audio), 1):
            end = cursor + duration
            blocks.append(f"{index}\n{srt_time(cursor)} --> {srt_time(end)}\n{scene.subtitle}\n")
            cursor = end
        output.write_text("\n".join(blocks), encoding="utf-8")


class WarningVideoGraph:
    """세 Agent를 공유 State로 연결하는 LangGraph 실행기이다."""

    def __init__(self, mode: Literal["dry-run", "actual"], progress: Callable[[str, str], None] | None = None):
        """실행 모드에 맞는 Agent와 StateGraph를 준비한다."""
        self.mode = mode
        self.progress = progress or (lambda *_: None)
        if mode == "actual":
            llm = ChatOpenAI(model=os.getenv("SCRIPT_MODEL", "gpt-4.1-mini"), temperature=0)
            client = OpenAI()
        else:
            llm, client = None, None
        self.script_agent = ScriptAgent(llm)
        self.tts_agent = TtsAgent(client, os.getenv("TTS_MODEL", "gpt-4o-mini-tts"), os.getenv("TTS_VOICE", "alloy"), self.progress)
        self.video_agent = VideoAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Agent 노드와 오류 경로를 연결한 StateGraph를 컴파일한다."""
        builder = StateGraph(WarningVideoState)
        builder.add_node("validate_input", self._validate_input)
        builder.add_node("script_agent", self._script_node)
        builder.add_node("tts_agent", self._tts_node)
        builder.add_node("video_agent", self._video_node)
        builder.add_node("finalize", self._finalize)
        builder.add_node("error_handler", self._error_handler)
        builder.add_edge(START, "validate_input")
        builder.add_conditional_edges("validate_input", self._route, {"continue": "script_agent", "error": "error_handler"})
        builder.add_conditional_edges("script_agent", self._route, {"continue": "tts_agent", "error": "error_handler"})
        builder.add_conditional_edges("tts_agent", self._route, {"continue": "video_agent", "error": "error_handler"})
        builder.add_conditional_edges("video_agent", self._route, {"continue": "finalize", "error": "error_handler"})
        builder.add_edge("finalize", END)
        builder.add_edge("error_handler", END)
        return builder.compile()

    def invoke(self, initial_state: WarningVideoState) -> WarningVideoState:
        """초기 State를 그래프에 전달하고 최종 State를 반환한다."""
        state = dict(initial_state)
        state.update(mode=self.mode, logs=[], error=None, api_called=False, status="QUEUED")
        return self.graph.invoke(state)

    def _validate_input(self, state: WarningVideoState) -> dict:
        """필수 입력과 실제 실행 파일을 검증한다."""
        try:
            if not state.get("location", "").strip() or not state.get("farmer_name", "").strip():
                raise ValueError("사용자 위치와 이름이 필요합니다.")
            if state["mode"] == "actual":
                if not state.get("source_video") or not Path(state["source_video"]).is_file():
                    raise ValueError("디지털 트윈 녹화 영상이 없습니다.")
                if not state.get("work_dir"):
                    raise ValueError("작업 폴더가 없습니다.")
            return self._success(state, "INPUT", "입력 검증 완료")
        except Exception as exc:
            return self._failure(state, "INPUT", exc)

    def _script_node(self, state: WarningVideoState) -> dict:
        """ScriptAgent를 실행하고 대본 결과를 State에 합친다."""
        self.progress("SCRIPT", "대본 생성 Agent 실행 중")
        try:
            return {**self.script_agent.run(state), **self._success(state, "SCRIPT", "대본 생성 Agent 완료")}
        except Exception as exc:
            return self._failure(state, "SCRIPT", exc)

    def _tts_node(self, state: WarningVideoState) -> dict:
        """TtsAgent를 실행하고 음성 결과를 State에 합친다."""
        self.progress("TTS", "TTS Agent 실행 중")
        try:
            result = self.tts_agent.run(state)
            success = self._success(state, "TTS", "TTS Agent 완료")
            success["logs"] = [*state.get("logs", []), *result["tts_logs"], "TTS Agent 완료"]
            return {**result, **success}
        except Exception as exc:
            return self._failure(state, "TTS", exc)

    def _video_node(self, state: WarningVideoState) -> dict:
        """VideoAgent를 실행하고 영상 결과를 State에 합친다."""
        self.progress("VIDEO", "영상제작 Agent 실행 중")
        try:
            return {**self.video_agent.run(state), **self._success(state, "VIDEO", "영상제작 Agent 완료")}
        except Exception as exc:
            return self._failure(state, "VIDEO", exc)

    def _finalize(self, state: WarningVideoState) -> dict:
        """최종 State를 manifest 파일과 완료 상태로 정리한다."""
        work_dir = state.get("work_dir")
        if work_dir:
            write_manifest(Path(work_dir) / "manifest.json", state)
        message = "Dry-run 검증 완료" if state["mode"] == "dry-run" else "경고 영상 제작 완료"
        self.progress("DONE", message)
        return {"current_agent": "DONE", "status": "DONE", "message": message, "logs": [*state.get("logs", []), message]}

    def _error_handler(self, state: WarningVideoState) -> dict:
        """Agent 오류를 최종 실패 상태로 정리한다."""
        message = f"{state.get('current_agent', 'UNKNOWN')} 단계 실패"
        self.progress("FAILED", message)
        return {"status": "FAILED", "message": message}

    def _route(self, state: WarningVideoState) -> Literal["continue", "error"]:
        """State의 오류 유무에 따라 다음 Agent 또는 오류 노드로 분기한다."""
        return "error" if state.get("error") else "continue"

    @staticmethod
    def _success(state: WarningVideoState, agent: str, message: str) -> dict:
        """노드의 성공 상태와 로그를 만든다."""
        return {"current_agent": agent, "status": agent, "message": message, "logs": [*state.get("logs", []), message], "error": None}

    @staticmethod
    def _failure(state: WarningVideoState, agent: str, exc: Exception) -> dict:
        """노드의 예외를 실패 State와 로그로 변환한다."""
        error = str(exc)
        return {"current_agent": agent, "status": "FAILED", "message": f"{agent} 단계 실패", "logs": [*state.get("logs", []), f"{agent} 실패: {error}"], "error": error}


class WarningVideoPipeline:
    """기존 API에서 LangGraph 실행기를 호출하기 위한 호환 진입점이다."""

    def run(self, source_video: Path, location: str, farmer_name: str, work_dir: Path, progress: Callable[[str, str], None] = lambda *_: None) -> Path:
        """실제 모드 그래프를 실행하고 완성된 영상 경로를 반환한다."""
        final_state = WarningVideoGraph("actual", progress).invoke({
            "source_video": str(source_video),
            "location": location,
            "farmer_name": farmer_name,
            "work_dir": str(work_dir),
        })
        if final_state["status"] == "FAILED":
            raise RuntimeError(final_state.get("error", "경고 영상 제작에 실패했습니다."))
        return Path(final_state["output_video"])


def create_dry_run_plan(location: str, farmer_name: str) -> dict:
    """동일한 StateGraph를 API와 FFmpeg 실행 없이 검증한다."""
    final_state = WarningVideoGraph("dry-run").invoke({"location": location, "farmer_name": farmer_name})
    if final_state["status"] == "FAILED":
        raise RuntimeError(final_state.get("error", "Dry-run 검증에 실패했습니다."))
    timeline = final_state["timeline"]
    return {
        "mode": final_state["mode"],
        "api_called": final_state["api_called"],
        "notice": final_state["notice"],
        "total_seconds": timeline[-1]["end_seconds"] if timeline else 0,
        "timeline": timeline,
        "ffmpeg_command": final_state["ffmpeg_command"],
        "logs": final_state["logs"],
    }


def estimate_speech_seconds(text: str) -> float:
    """한국어 글자 수로 느린 안내 음성의 재생 시간을 추정한다."""
    meaningful = len(re.sub(r"\s+", "", text))
    return max(1.5, round(meaningful / 4.2, 2))


def build_timeline(scenes: list[Scene], durations: list[float], timing: str) -> list[TimelineItem]:
    """장면별 길이를 누적해 자막 시작 및 종료 시간을 만든다."""
    cursor, result = 0.0, []
    for index, (scene, duration) in enumerate(zip(scenes, durations), 1):
        end = round(cursor + duration, 3)
        result.append(TimelineItem(index, round(cursor, 3), end, round(duration, 3), scene.subtitle, scene.narration, timing))
        cursor = end
    return result


def write_manifest(path: Path, state: WarningVideoState) -> None:
    """검수에 필요한 최종 State 항목을 JSON 파일로 저장한다."""
    keys = ["mode", "api_called", "scenes", "scripts", "audio_paths", "audio_durations", "narration_audio", "subtitle_path", "timeline", "ffmpeg_command", "output_video", "logs"]
    path.write_text(json.dumps({key: state.get(key) for key in keys}, ensure_ascii=False, indent=2), encoding="utf-8")


def require_command(name: str) -> None:
    """필수 외부 명령이 설치되어 있는지 확인한다."""
    if not shutil.which(name):
        raise RuntimeError(f"{name} 명령을 찾을 수 없습니다.")


def run_command(command: list[str]) -> None:
    """외부 명령을 실행하고 실패 내용을 예외로 전달한다."""
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr[-2000:])


def media_duration(path: Path) -> float:
    """ffprobe로 음성 또는 영상 파일의 실제 재생 시간을 구한다."""
    require_command("ffprobe")
    completed = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(completed.stdout.strip())


def srt_time(seconds: float) -> str:
    """초 단위 시간을 SRT 타임코드 문자열로 변환한다."""
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def escape_filter_path(path: Path) -> str:
    """파일 경로를 FFmpeg 자막 필터에서 안전한 형태로 이스케이프한다."""
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
