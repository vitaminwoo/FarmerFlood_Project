from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
from v23_runtime_asset_catalog import RuntimeAssetCatalog  # noqa: E402


class RuntimeAssetCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = RuntimeAssetCatalog.load(root=ROOT / "runtime_assets" / "v23")

    def test_all_three_fields_have_independent_cached_media(self):
        flood_ids = set()
        overlay_ids = set()
        for suffix in ("001", "002", "003"):
            selected = self.catalog.select(f"OSONG-FIELD-DEMO-{suffix}", "caution")
            flood_ids.add(selected["field_flood"]["asset_id"])
            overlay_ids.add(selected["field_overlay"]["asset_id"])
            self.assertTrue(selected["field_background"]["path"].endswith(".mp4"))
        self.assertEqual(len(flood_ids), 3)
        self.assertEqual(len(overlay_ids), 3)

    def test_unsupported_scenario_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.catalog.select("OSONG-FIELD-DEMO-001", "severe")

    def test_sokrisan_subscribers_share_the_region_base_video(self):
        selected = self.catalog.select_region("충청북도 보은군 속리산면 백현리")
        self.assertIsNotNone(selected)
        self.assertEqual(selected["region_id"], "KR-CHUNGBUK-BOEUN-SOKRISAN")
        self.assertTrue(Path(selected["asset"]["path"]).is_file())
        self.assertEqual(selected["timeline_policy"], "hold_last_frame_to_60_seconds")

    def test_other_regions_do_not_select_sokrisan_video(self):
        self.assertIsNone(self.catalog.select_region("충청북도 청주시 강내면"))


if __name__ == "__main__":
    unittest.main()
