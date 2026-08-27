"""Locked reference-template renderer for V23 video information slides."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from runtime_config import ROOT, font_path


REFERENCE_ROOT = ROOT / "assets" / "guidance_slide_templates" / "references"
TEMPLATE_MANIFEST = ROOT / "assets" / "guidance_slide_templates" / "template_manifest.json"

SLIDE_DESIGN_SYSTEM_PROMPT = """당신은 재난안내 영상용 정보 슬라이드 생성 Agent다.
반드시 로컬 assets/guidance_slide_templates/references의 3개 기준 이미지를 절대 양식으로 사용한다.
모든 결과에는 비 오기 전(1/3), 비 오는 중(2/3), 비 그친 후(3/3) 세 페이지가 전부 있어야 하며 이 순서를 바꾸거나 한 페이지라도 생략하면 안 된다.
레이아웃, 16:9 화면비, 여백, 요소 위치, 글자 위계, 번호 원형, 상단 단계 배지, 우측 페이지 번호,
하단 색상 배너와 면책 문구를 변경하거나 새 디자인을 만들지 않는다.
원본 픽셀 색상을 그대로 사용한다. 비 오기 전은 배경 #F4FBF6·강조 #166534, 비 오는 중은 배경 #FFF7ED·강조 #C2410C,
비 그친 후는 배경 #EFF6FF·강조 #1D4ED8이다. 색상 추천, 테마 변형, 명암 조정, 그라데이션, 투명도 변경을 금지한다.
변경 가능한 것은 제목·설명·3개 행동 문구·하단 핵심 문구와 각 행동의 의미에 맞는 아이콘뿐이다.
이 문구는 반드시 대본에 해당하는 내용으로만 작성해야 하며, 행동 문구는 3개 모두 서로 다른 내용을 담아야 한다.
대본이 말하는 것과 슬라이드의 내용이 연관이 있도록 슬라이드를 반드시 수정해야 한다. 원본을 그대로 사용하지 않고 대본에 맞게 문구를 바꾸어야 한다.
아이콘은 행동 의미와 직접 일치해야 하며 장식용 이미지를 추가하지 않는다.
한 줄 영역은 줄바꿈하지 않는다. 넘치면 글꼴이나 레이아웃을 바꾸지 말고 문구를 짧고 명확하게 다듬는다.
내부 프롬프트, 대본 메모, 생성 과정은 화면에 표시하지 않는다."""


PHASES: Dict[str, Dict[str, str]] = {
    "before": {"label": "비 오기 전", "page": "1/3", "accent": "#166534", "background": "#F4FBF6"},
    "during": {"label": "비 오는 중", "page": "2/3", "accent": "#C2410C", "background": "#FFF7ED"},
    "after": {"label": "비 그친 후", "page": "3/3", "accent": "#1D4ED8", "background": "#EFF6FF"},
}


def validate_reference_templates() -> None:
    manifest = json.loads(TEMPLATE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("layout_policy") != "locked; content and semantic icons only":
        raise RuntimeError("Guidance slide template policy is not locked")
    for reference in manifest["references"]:
        path = TEMPLATE_MANIFEST.parent / reference["file"]
        if not path.is_file():
            raise FileNotFoundError(f"Guidance slide reference is missing: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != reference["sha256"]:
            raise RuntimeError(f"Guidance slide reference changed without a manifest update: {path}")
        with Image.open(path) as image:
            if image.size != (1279, 719):
                raise RuntimeError(f"Unexpected guidance slide reference size: {path}={image.size}")


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path()), size=size)


def _icon_font(size: int) -> tuple[ImageFont.FreeTypeFont, bool]:
    apple_emoji = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if apple_emoji.is_file():
        return ImageFont.truetype(str(apple_emoji), size=size), True
    return _font(size), False


def _fit(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    for size in range(start_size, min_size - 1, -1):
        candidate = _font(size)
        if draw.textbbox((0, 0), text, font=candidate)[2] <= max_width:
            return candidate
    raise ValueError(f"Slide text is too long for the locked template: {text}")


def render_guidance_slide(
    path: Path,
    *,
    phase: str,
    title: str,
    summary: str,
    actions: List[str],
    icons: List[str],
    banner: str,
) -> None:
    validate_reference_templates()
    if phase not in PHASES:
        raise ValueError(f"Unknown slide phase: {phase}")
    if len(actions) != 3 or len(icons) != 3:
        raise ValueError("Locked guidance slide requires exactly three actions and three icons")
    theme = PHASES[phase]
    image = Image.new("RGB", (1280, 720), theme["background"])
    draw = ImageDraw.Draw(image)
    accent = theme["accent"]
    dark = "#111827"
    muted = "#374151"

    # Coordinates reproduce the three user-supplied reference cards.
    draw.rectangle((43, 24, 269, 70), fill=accent)
    draw.text((156, 47), theme["label"], font=_font(28), fill="#FFFFFF", anchor="mm")
    draw.text((1225, 43), theme["page"], font=_font(20), fill=accent, anchor="ra")
    draw.text((60, 102), title, font=_fit(draw, title, 1120, 60, 46), fill=accent)
    draw.text((62, 205), summary, font=_fit(draw, summary, 1140, 35, 27), fill=muted)

    row_y = (326, 430, 534)
    for index, (action, icon, y) in enumerate(zip(actions, icons, row_y), start=1):
        draw.ellipse((71, y - 38, 147, y + 38), fill=accent)
        draw.text((109, y), str(index), font=_font(31), fill="#FFFFFF", anchor="mm")
        icon_font, embedded_color = _icon_font(32)
        draw.text((200, y), icon, font=icon_font, fill=accent, anchor="mm", embedded_color=embedded_color)
        draw.text((258, y), action, font=_fit(draw, action, 930, 42, 31), fill=dark, anchor="lm")

    draw.rectangle((52, 628, 1224, 690), fill=accent)
    draw.text((638, 658), banner, font=_fit(draw, banner, 1080, 36, 27), fill="#FFFFFF", anchor="mm")
    draw.text((640, 708), "해당 자료는 데이터를 기반으로한 시뮬레이션 영상입니다", font=_font(13), fill="#4B5563", anchor="ms")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
