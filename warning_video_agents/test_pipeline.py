import unittest

from warning_video_agents.pipeline import WarningVideoGraph, base_scenes, create_dry_run_plan, srt_time


class PipelineTest(unittest.TestCase):
    def test_only_name_and_location_are_inserted(self):
        """기준 대본에는 위치와 이름만 올바르게 들어가는지 확인한다."""
        scenes = base_scenes("미원리", "홍길동")
        self.assertEqual(scenes[0].subtitle, "미원리 홍길동님 논입니다.")
        self.assertEqual(scenes[2].narration, None)
        self.assertIn("공식 재난경보를 대체하지 않습니다", scenes[-1].subtitle)

    def test_srt_time(self):
        """초 단위 값이 올바른 SRT 타임코드로 변환되는지 확인한다."""
        self.assertEqual(srt_time(3661.234), "01:01:01,234")

    def test_dry_run_never_calls_api(self):
        """Dry-run 그래프가 API 호출 없이 전체 결과를 만드는지 확인한다."""
        plan = create_dry_run_plan("미원리", "홍길동")
        self.assertFalse(plan["api_called"])
        self.assertEqual(len(plan["timeline"]), 13)
        self.assertIsNone(plan["timeline"][2]["narration"])
        self.assertEqual(plan["ffmpeg_command"][0], "ffmpeg")
        self.assertIn("TTS Agent 장면 13/13 처리", plan["logs"])

    def test_graph_contains_agent_nodes(self):
        """StateGraph에 세 Agent와 오류 처리 노드가 등록됐는지 확인한다."""
        nodes = WarningVideoGraph("dry-run").graph.get_graph().nodes
        self.assertTrue({"script_agent", "tts_agent", "video_agent", "error_handler"}.issubset(nodes))

    def test_invalid_input_routes_to_error_handler(self):
        """필수 입력 오류가 ErrorHandler를 거쳐 실패 State로 끝나는지 확인한다."""
        state = WarningVideoGraph("dry-run").invoke({"location": "", "farmer_name": "홍길동"})
        self.assertEqual(state["status"], "FAILED")
        self.assertEqual(state["current_agent"], "INPUT")
        self.assertIn("사용자 위치와 이름", state["error"])


if __name__ == "__main__":
    unittest.main()
