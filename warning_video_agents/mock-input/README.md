# 디지털 트윈 mock 입력 영상

로컬 파이프라인 검증에 사용할 디지털 트윈 녹화 MP4를 이 폴더에 아래 이름으로 넣습니다.

`digital-twin-sample.mp4`

다른 위치의 영상을 사용하려면 프로젝트 루트 `.env.properties`에 절대 또는 프로젝트 루트 기준 상대 경로를 지정합니다.

```properties
DIGITAL_TWIN_MOCK_SOURCE=/absolute/path/to/my-recording.mp4
```

이 파일은 디지털 트윈의 녹화 결과를 흉내 내는 입력입니다. FastAPI의 `mock` 모드는 이 입력에 `[MOCK] 트리거 영상 파이프라인 처리 완료` 자막을 FFmpeg로 합성하여 `warning.mp4`를 만듭니다.
