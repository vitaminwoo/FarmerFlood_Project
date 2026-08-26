"""Small OS-independent helpers shared by the V23 workflow."""
from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List

from mutagen import File as MutagenFile


async def write_openai_audio(client, model: str, voice: str, text: str, speed: float, path: Path) -> None:
    path.unlink(missing_ok=True)
    response = await client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        instructions="고령 농업인이 이해하기 쉽도록 침착하고 또렷한 한국어로 읽으세요. 숫자와 시간은 정확하게 읽으세요.",
        response_format="mp3",
        speed=speed,
        timeout=90.0,
    )
    await asyncio.to_thread(response.write_to_file, path)


async def generate_tts_segment(client, model: str, voice: str, speed: float, audio_dir: Path, index: int, item: Dict[str, Any]):
    path = audio_dir / f"{index:02d}_{item['id']}.mp3"
    target = float(item["duration_seconds"])
    provider = "openai"
    fallback = None
    current_speed = speed
    try:
        if client is None:
            raise RuntimeError("OPENAI_API_KEY is missing")
        duration = 0.0
        for _ in range(4):
            await write_openai_audio(client, model, voice, item["narration"], current_speed, path)
            duration = await asyncio.to_thread(read_audio_duration_seconds, path)
            if duration <= target:
                break
            next_speed = min(2.0, round(current_speed * duration / target * 1.04, 2))
            if next_speed <= current_speed:
                break
            current_speed = next_speed
        if duration > target:
            raise RuntimeError(f"OpenAI TTS exceeds segment: {duration:.3f}/{target:.3f}s")
    except Exception as exc:
        say = Path("/usr/bin/say")
        if not say.is_file():
            raise
        provider = "macos_say"
        fallback = str(exc).replace("\n", " ")[:240]
        rate = int(os.getenv("V23_LOCAL_TTS_RATE", "200"))
        for _ in range(4):
            await asyncio.to_thread(
                subprocess.run,
                [str(say), "-v", os.getenv("V23_LOCAL_TTS_VOICE", "Yuna"), "-r", str(rate), "-o", str(path), item["narration"]],
                check=True,
            )
            duration = await asyncio.to_thread(read_audio_duration_seconds, path)
            if duration <= target:
                break
            rate = max(rate + 1, math.ceil(rate * duration / target * 1.04))
    return item["id"], {
        "path": str(path),
        "bytes": path.stat().st_size,
        "provider": provider,
        "assigned_duration_seconds": item["duration_seconds"],
        "speed": current_speed if provider == "openai" else None,
    }, fallback


def read_audio_duration_seconds(path: Path) -> float:
    media = MutagenFile(path)
    if media is None or media.info is None or not hasattr(media.info, "length"):
        raise RuntimeError(f"Could not inspect TTS audio duration: {path}")
    return float(media.info.length)


def run_logged(command: List[str], cwd: Path, log_path: Path) -> None:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Command failed; inspect {log_path}")


def srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
