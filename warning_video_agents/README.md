# 경고 영상 멀티에이전트

디지털 트윈 녹화가 끝난 뒤 호출할 독립 Python 파이프라인입니다.

세 Agent는 LangGraph `StateGraph`에서 하나의 `WarningVideoState`를 공유합니다.

```text
START → 입력 검증 → ScriptAgent → TtsAgent → VideoAgent → 결과 정리 → END
                    └──────── 오류 발생 시 ErrorHandler ─────────┘
```

1. `ScriptAgent`: `ChatOpenAI.invoke()`로 기준 대본을 확인하고 장면과 낭독문을 State에 저장합니다.
2. `TtsAgent`: 읽는 문장을 OpenAI TTS로 음성화하고 실제 길이를 State에 저장합니다.
3. `VideoAgent`: State의 녹화 영상, 음성, 시간 정보로 자막과 최종 영상을 만듭니다.

실행은 초기 State를 `WarningVideoGraph.invoke()`에 전달하고 최종 State를 받는 구조입니다.
실제 실행과 dry-run 모두 같은 그래프를 사용합니다.

## 임시 확인 화면 실행

Python 3.11 이상과 `ffmpeg`/`ffprobe`가 필요합니다.

```bash
cd warning_video_agents
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='...'
uvicorn app:app --reload --port 8090
```

또는 `warning_video_agents/.env`에 `OPENAI_API_KEY=...`를 저장할 수 있습니다.
`.env`는 Git 제외 대상입니다. Spring의 `application.yml`은 별도 Python 프로세스가
자동으로 읽지 않으므로, 운영에서는 두 프로세스 모두에 환경변수/Secret Manager로
키를 주입하는 방식을 권장합니다.

브라우저에서 `http://localhost:8090`을 열고 녹화 영상을 올립니다. 결과는
`warning_video_agents/output/<job-id>/warning.mp4`에 저장됩니다.

## 이후 트리거 연결

두 트리거 충족 → 디지털 트윈 녹화 → 녹화 완료 콜백 순서에서 아래 API를
호출하면 됩니다. 현재 Spring의 `MediaPipeline` 구현을 이 API 호출로 교체할 수
있도록 별도 서비스로 두었습니다.

```bash
curl -F location='○○리' -F farmer_name='김○○' \
  -F video=@recording.mp4 http://localhost:8090/api/jobs
```

`GET /api/jobs/{job_id}`로 진행 상태와 결과 경로를 확인합니다.

`POST /api/jobs`의 선택 필드 `mode`는 `actual`(기본값) 또는 `mock`입니다. `mock`은 업로드 영상을 결과 영상으로 복사하여 Spring→FastAPI→최종 영상 다운로드 계약을 API 비용 없이 끝까지 검증합니다.

## 비용 없이 검증

확인 화면에서 **API 없이 검증**을 누르면 영상 파일이나 API 키 없이 다음 내용을
확인할 수 있습니다.

- TTS가 읽을 문장과 읽지 않을 자막
- 장면별 예상 시작·종료 시각
- 최종 합성에 사용할 FFmpeg 명령

`GET /api/preview?location=미원리&farmer_name=홍길동`으로 JSON도 확인할 수 있습니다.
예상 시간은 글자 수 기반이며, 실제 실행 때는 각 MP3를 `ffprobe`로 측정한 정확한
시간이 `output/<job-id>/manifest.json`에 기록됩니다.
