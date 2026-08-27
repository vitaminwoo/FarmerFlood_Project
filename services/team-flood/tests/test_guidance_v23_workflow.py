from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
import guidance_v23_workflow as workflow  # noqa: E402
from guidance_rag import DEFAULT_DB_PATH, retrieve_guidance  # noqa: E402
from guidance_slide_template import PHASES, REFERENCE_ROOT, SLIDE_DESIGN_SYSTEM_PROMPT, render_guidance_slide  # noqa: E402
from runtime_config import ROOT as CONFIG_ROOT, asset_root  # noqa: E402
from v23_field_registry import FieldRegistry  # noqa: E402
from v23_personalized_visual_builder import build_personalized_visual_plan  # noqa: E402


class GuidanceV23WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields = FieldRegistry.load()

    def load_event(self, suffix: str):
        name = "valid_forecast_and_hydrology.json" if suffix == "001" else f"valid_forecast_and_hydrology_field_{suffix}.json"
        return json.loads((ROOT / "data" / "v23" / "events" / name).read_text(encoding="utf-8"))

    def test_graph_has_exactly_four_agents(self):
        graph = workflow.build_graph().get_graph()
        nodes = set(graph.nodes) - {"__start__", "__end__"}
        self.assertEqual(nodes, {"script_agent", "tts_agent", "video_production_agent", "composition_agent"})

    def test_each_field_generates_field_specific_script_and_visual_plan(self):
        for suffix in ("001", "002", "003"):
            event = self.load_event(suffix)
            field = self.fields.resolve_event(event)
            segments = workflow.build_segments(event, field)
            text = " ".join(item["narration"] for item in segments)
            self.assertIn(field["display_name"], text)
            self.assertIn(field["shelter"]["name"], text)
            self.assertEqual(segments[0]["start_frame"], 1)
            self.assertEqual(segments[-1]["end_frame"], 1280)
            plan = build_personalized_visual_plan(event, output_root=ROOT / "output" / "test")
            self.assertEqual(plan["field_id"], field["field_id"])
            self.assertEqual(len(plan["strips"]), 6)
            selected = " ".join(item["strip_id"] for item in plan["strips"])
            self.assertIn(f"field_{suffix}", selected)

    def test_project_root_is_derived_from_source_location(self):
        self.assertEqual(CONFIG_ROOT, ROOT)

    def test_rag_database_retrieves_official_flood_guidance(self):
        self.assertTrue(DEFAULT_DB_PATH.is_file())
        results = retrieve_guidance("농경지 배수로 논둑 물꼬", limit=3)
        self.assertTrue(results)
        combined = " ".join(item["text"] for item in results)
        self.assertTrue(any(term in combined for term in ("배수로", "논둑", "물꼬")))

    def test_script_segments_include_rag_provenance(self):
        event = self.load_event("001")
        field = self.fields.resolve_event(event)
        segments = workflow.build_segments(event, field)
        action = next(item for item in segments if item["id"] == "during_rain_card")
        self.assertTrue(action["rag"]["citations"])
        self.assertTrue(action["rag"]["selected_phrase"])

    def test_all_three_locked_slides_are_always_last_and_ordered(self):
        event = self.load_event("001")
        field = self.fields.resolve_event(event)
        segments = workflow.build_segments(event, field)
        self.assertEqual(
            [item["id"] for item in segments[-3:]],
            ["before_rain_card", "during_rain_card", "after_rain_card"],
        )
        self.assertTrue(all(item["visual_type"] == "information_card" for item in segments[-3:]))
        self.assertEqual([(item["start_frame"], item["end_frame"]) for item in segments[-3:]], [(801, 960), (961, 1120), (1121, 1280)])

    def test_sokrisan_shared_visual_does_not_leak_osong_script_data(self):
        event = self.load_event("001")
        event["metadata"] = {
            "address": "충청북도 보은군 속리산면 백현리",
            "source_farmland_id": "REAL-SOKRISAN-FIELD-001",
        }
        field = self.fields.resolve_event(event)
        segments = workflow.build_segments(event, field)
        text = " ".join(item["subtitle"] + " " + item["narration"] for item in segments)
        self.assertIn("속리산면 등록 농경지", text)
        self.assertNotIn("오송", text)
        self.assertNotIn("85.0", text)
        self.assertNotIn("오송읍복지회관", text)
        visual = workflow.ensure_personalized_visual({"event": event, "field": field, "mode": "plan"})
        self.assertEqual(visual["region_id"], "KR-CHUNGBUK-BOEUN-SOKRISAN")
        self.assertEqual(visual["visual_scope"], "region_shared")

    def test_locked_slide_references_and_prompt_are_present(self):
        self.assertEqual(set(PHASES), {"before", "during", "after"})
        self.assertEqual(len(list(REFERENCE_ROOT.glob("*.png"))), 3)
        self.assertIn("변경 가능한 것은", SLIDE_DESIGN_SYSTEM_PROMPT)
        self.assertIn("아이콘", SLIDE_DESIGN_SYSTEM_PROMPT)
        self.assertIn("한 페이지라도 생략하면 안 된다", SLIDE_DESIGN_SYSTEM_PROMPT)
        self.assertEqual(PHASES["before"]["background"], "#F4FBF6")
        self.assertEqual(PHASES["during"]["background"], "#FFF7ED")
        self.assertEqual(PHASES["after"]["background"], "#EFF6FF")

    def test_locked_slide_renderer_outputs_video_resolution(self):
        from tempfile import TemporaryDirectory
        from PIL import Image
        with TemporaryDirectory() as directory:
            output = Path(directory) / "card.png"
            render_guidance_slide(
                output, phase="before", title="미리 준비하세요", summary="비가 오기 전에 끝내세요.",
                actions=["배수로 정리", "농기계 이동", "시설물 보강"], icons=["💧", "🚜", "🔧"], banner="미리 준비합니다.",
            )
            with Image.open(output) as rendered:
                self.assertEqual(rendered.size, (1280, 720))

    def test_asset_root_can_be_overridden_on_windows_or_macos(self):
        expected = ROOT / "portable-assets"
        with patch.dict(os.environ, {"V23_ASSET_ROOT": str(expected)}):
            self.assertEqual(asset_root(), expected.resolve())


if __name__ == "__main__":
    unittest.main()
