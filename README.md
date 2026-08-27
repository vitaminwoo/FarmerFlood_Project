# Farmer Flood Trigger

충북 농업인의 등록 농경지를 기준으로 인근 하천 수위와 기상청 단기예보를 판정하고, 조건 충족 시 디지털 트윈·멀티Agent 경고 영상을 제작하는 Spring Boot 서비스입니다.

## 현재 지원 기능

- 한강홍수통제소 충북 관측소의 수위·관심/주의/경계/심각 기준 조회
- 기상청 단기예보의 향후 24시간 강수량 합산
- `관심 이상 → 24시간 예상강수 35mm 이상` 순차 트리거 및 최초 1회 발화
- 공식 충북 팜맵 Polygon 지도 선택, 사용자 농경지 경계·PNU·면적 등록
- 농경지별 실제 인근 관측소 최대 3개 연결과 강내면 시연용 mock_4 연결
- PostgreSQL에 알림, 트리거 상태, 영상 제작 작업, 사용자·농경지·관측소 연결 영속화
- 재시작 후 기존 알림/작업/트리거 상태 복구
- 팀 Python Worker 호출, Blender 디지털 트윈, 대본·안전성 검토·TTS·자막·합성 Agent 실행
- 지역·개인화 농경지·시나리오가 같은 디지털 트윈 원본 영상 재사용
- 8080 대시보드에서 mock 트리거, 제작 상태, 상세 로그와 완성 영상 확인
- Android 농업인·보호자 회원가입과 로그인, 행정구역 이동 후 실제 농경지 선택
- 보호자에게 농업인과 동일한 영상 알림 제공 및 농업인의 최신 영상 확인 여부 실시간 표시
- 완성 영상 Android 시스템 알림과 알림 터치 즉시 재생

## 구성

```text
Spring Boot :8080
  ├─ 한강홍수통제소 / 기상청 API
  ├─ PostgreSQL :5432 (상태·이력·사용자·농경지)
  └─ Python Worker :8091
       ├─ Blender 디지털 트윈
       ├─ 멀티Agent / OpenAI TTS
       └─ FFmpeg·Blender 최종 합성
```

## 저장소 내려받기

```bash
git clone https://github.com/vitaminwoo/FarmerFlood_Project.git
cd FarmerFlood_Project
```

기본 브랜치는 `main`입니다. IntelliJ IDEA나 Android Studio에서 프로젝트를 열어도 같은 Git 저장소와 `main` 브랜치를 인식합니다.

## 최초 설치

필요 도구는 Java 21, Docker, Python 3.13, Blender입니다. 지도 배경은 OpenStreetMap, 농경지 경계는 자체 Spring API를 사용합니다.

```bash
brew install --cask blender
cp .env.example .env.properties
docker compose up -d postgres

cd services/team-flood
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ../..

# 공식 팜맵 최초 적재용 환경(서비스 실행 시에는 불필요)
python3.13 -m venv .farmmap-venv
.farmmap-venv/bin/pip install -r scripts/farmmap-requirements.txt
```

`.env.properties`에 발급 키를 입력합니다. 이 파일과 각 Python 서비스의 `.env`는 `.gitignore` 대상입니다. 인증키와 운영 DB 비밀번호는 Git에 올리지 않습니다.

```properties
HRFCO_API_KEY=...
KMA_SERVICE_KEY=...
OPENAI_API_KEY=...

DB_URL=jdbc:postgresql://127.0.0.1:5432/farmer_flood
DB_USERNAME=farmer_flood
DB_PASSWORD=farmer_flood
```

Docker Compose는 기본적으로 `farmer_flood/farmer_flood` 계정을 사용합니다. 다른 비밀번호가 필요하면 Compose 실행 전 `POSTGRES_PASSWORD`도 같은 값으로 지정합니다. 이미 생성된 Docker 볼륨의 비밀번호는 환경변수 변경만으로 바뀌지 않습니다.

## 권장 실행 순서

### 1. PostgreSQL/PostGIS 실행

```bash
docker compose up -d postgres
docker compose ps
```

DB는 Docker 볼륨에 보존됩니다. 중지와 재실행은 다음과 같습니다.

```bash
docker compose stop postgres
docker compose up -d postgres
```

### 2. Spring Boot와 FastAPI Worker 실행

터미널에서는 프로젝트 루트에서 실행합니다.

```bash
./gradlew bootRun
```

IntelliJ IDEA에서는 프로젝트 루트를 Gradle 프로젝트로 연 뒤 `TriggerServiceApplication`의 실행 아이콘 또는 상단의 **Run** 버튼을 눌러도 됩니다. 이 방식도 동일하게 Spring Boot를 8080 포트에서 실행합니다. 이미 터미널에서 Spring이 실행 중이면 IntelliJ Run과 8080 포트가 충돌하므로 둘 중 하나만 실행하십시오.

브라우저에서 `http://localhost:8080`을 엽니다. 기본값은 실제 공공 API 모드이고, Spring이 로컬 Python Worker를 함께 시작합니다. 자동 시작된 Worker 로그는 `runtime/flood-worker.log`에 기록됩니다.

FastAPI Worker는 기본적으로 `FLOOD_WORKER_AUTO_START=true`이므로 Spring 시작 시 `services/team-flood/run.sh`를 통해 8091 포트에서 자동 실행됩니다. 별도 터미널에서 FastAPI를 다시 실행할 필요가 없습니다. 자동 실행을 끄고 직접 관리하려면 다음처럼 실행합니다.

```bash
# 공공 API 대신 전체 mock provider 사용
PROVIDER_MODE=mock ./gradlew bootRun

# Worker 수동 실행
FLOOD_WORKER_AUTO_START=false ./gradlew bootRun
services/team-flood/run.sh
```

주요 설정:

```properties
PROVIDER_MODE=live
RAINFALL_THRESHOLD_MM=80
FORECAST_HOURS=24
POLL_DELAY_MS=600000
FLOOD_WORKER_AUTO_START=true
FLOOD_WORKER_BASE_URL=http://127.0.0.1:8091
FLOOD_WORKER_FARMER_NAME=농업인
PIPELINE_STORAGE_DIR=runtime/media
```

## PostgreSQL과 상태 복구

이 MVP는 Flyway를 사용하지 않습니다. 빈 데이터베이스에서 Hibernate `ddl-auto=update`가 필요한 테이블을 만들고 확장합니다. 따라서 초기 개발은 간단하지만, 운영 전에는 Flyway 같은 명시적 마이그레이션 도구와 백업 절차를 도입해야 합니다.

영속화되는 정보:

- 발생 알림과 트리거별 마지막 상태(`IDLE`, `ARMED`, `FIRED`)
- 영상 제작 작업, 단계, 진행률, Worker 작업 ID, 결과 파일과 오류
- 사용자, 농경지 위치·기상격자·경계 GeoJSON
- 농경지와 인근 수위 관측소 연결 및 거리

Spring 재시작 시 DB 상태를 다시 읽으므로 새로고침이나 서버 재기동으로 이력이 사라지지 않습니다. Python Worker도 각 작업의 `job.json`을 읽어 완성 파일이 존재하는 작업은 완료로 복구하고, 실행 도중 Worker가 종료된 작업은 실패로 확정하여 무한 실행 상태를 남기지 않습니다.

팀원이 같은 데이터를 보며 테스트하려면 공용 PostgreSQL 한 대를 개발망이나 관리형 DB에 두고 모두 동일한 `DB_URL`, `DB_USERNAME`, `DB_PASSWORD`를 사용하면 됩니다. 저장소에는 `.env.example`만 공유하고 실제 접속정보는 팀 비밀관리 도구로 공유하십시오. 동시에 같은 mock 트리거를 조작하는 테스트는 서로 영향을 줄 수 있으므로 사용자·농경지 또는 별도 DB 스키마를 분리하는 것이 안전합니다.

로컬 DB 데이터는 `farmer-flood-postgres-data` Docker 볼륨에 남습니다. 다음 명령은 컨테이너만 중지하며 데이터는 보존합니다.

```bash
docker compose stop postgres
```

## 공식 충북 팜맵

첨부된 2025년 충청북도 팜맵의 `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`를 한 세트로 읽습니다. 원본 좌표계인 Korea 2000 Unified CS를 WGS84(`EPSG:4326`)로 변환하고, 유효하지 않은 도형을 보정한 뒤 PostGIS `MultiPolygon`으로 저장합니다. 현재 전체 11개 시·군 752,299개 농경지가 적재되며 강내면은 6,730개입니다.

원본 ZIP은 용량과 배포권한 때문에 Git에 포함하지 않습니다. 팀원은 공식 파일을 전달받아 아래 명령으로 동일한 DB를 구성하거나, 공용 개발 PostgreSQL을 사용합니다. 재실행은 `source_id` 기준 upsert라 중복을 만들지 않습니다.

```bash
.farmmap-venv/bin/python scripts/import_farmmap.py \
  /absolute/path/to/충청북도_팜맵.zip --batch-size 1000

# 특정 지역만 빠르게 적재
.farmmap-venv/bin/python scripts/import_farmmap.py \
  /absolute/path/to/충청북도_팜맵.zip --district 청주시 --locality 강내면

# 압축을 풀어 받은 Shapefile 세트도 .shp 경로로 바로 적재 가능
.farmmap-venv/bin/python scripts/import_farmmap.py \
  /absolute/path/to/2025_충청북도_보은군.shp --district 보은군 --locality 속리산면
```

저장 필드는 원본 식별자, UID, PNU, 작물 분류, 면적, 전체 주소, 시·군, 읍·면·동, 기준연도, 실제 Polygon입니다. 화면은 현재 지도 경계(`bbox`) 안의 도형만 GeoJSON으로 조회하여 전체 데이터를 한 번에 전송하지 않습니다.

- `GET /api/mobile/farm-map/parcels?district=청주시&locality=강내면&bbox=minLng,minLat,maxLng,maxLat`: 화면 범위 농경지 GeoJSON
- `GET /api/mobile/farm-map/parcels/{sourceId}`: 선택 농경지 상세 정보
- `GET /mobile/farm-map?district=청주시&locality=강내면`: Android WebView용 선택 지도

## 사용자·농경지 API

사용자 생성:

```http
POST /api/users
Content-Type: application/json

{"name":"홍길동","email":"farmer@example.com"}
```

농경지 등록:

```http
POST /api/farmlands
Content-Type: application/json

{
  "userId":"사용자 UUID",
  "name":"괴산 논 1",
  "address":"충청북도 괴산군 불정면",
  "province":"충청북도",
  "district":"괴산군",
  "locality":"불정면",
  "regionId":"chungbuk-goesan",
  "latitude":36.874,
  "longitude":127.854,
  "nx":76,
  "ny":113,
  "sourceParcelId":"431133103000040",
  "pnu":"4311331030101460000",
  "areaSquareMeters":29012.18,
  "boundaryGeoJson":"{\"type\":\"Polygon\",\"coordinates\":[...]}"
}
```

- `GET /api/farmlands?userId={UUID}`: 사용자의 농경지와 연결 관측소 조회
- `POST /api/farmlands/{farmlandId}/monitoring-stations/relink`: 최신 관측소 제원으로 다시 연결

현재 인근 관측소 계산은 선택 Polygon 내부점과 한강홍수통제소 실제 관측소 사이의 Haversine 거리를 계산하여 50km 이내 상위 3개를 연결합니다. 강내면은 시연 조작이 가능한 `MOCK-004`를 추가로 우선 연결하되, 실제 최근접인 청주시(미호강교)도 함께 저장합니다. 이는 MVP용 근사치이며 운영 전에는 유역·하천망·제방·고도와 상하류 관계를 반영한 공간 분석으로 교체해야 합니다. 정확한 Polygon은 향후 침수예상지역과의 교차 분석 및 Blender 개인화 영역 표시에 그대로 사용할 수 있습니다.

## Android 모바일 앱

Android Studio에서 `mobile-android` 디렉터리를 프로젝트로 엽니다. 앱은 Android 8.0(API 26) 이상을 지원하고 Android 16 QPR2 SDK로 빌드합니다. Android Studio의 정확한 메뉴 명칭은 **Tools → Device Manager**입니다. 여기에서 Pixel 에뮬레이터 두 대(예: 농업인용 Pixel과 보호자용 Pixel 9 Pro (2))를 생성하고 각각 실행합니다. Pixel 에뮬레이터에서는 백엔드를 `10.0.2.2:8080`으로 접근하도록 이미 설정되어 있습니다.

터미널 빌드:

```bash
cd mobile-android
ANDROID_HOME="$HOME/Library/Android/sdk" ../gradlew assembleDebug
```

생성 APK:

```text
mobile-android/app/build/outputs/apk/debug/app-debug.apk
```

실행 중인 에뮬레이터 확인과 APK 설치:

```bash
ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
"$ANDROID_SDK_ROOT/platform-tools/adb" devices

# 모든 실행 중 에뮬레이터에 같은 APK 설치(각 serial은 adb devices 결과 사용)
"$ANDROID_SDK_ROOT/platform-tools/adb" -s emulator-5554 install -r \
  mobile-android/app/build/outputs/apk/debug/app-debug.apk
"$ANDROID_SDK_ROOT/platform-tools/adb" -s emulator-5556 install -r \
  mobile-android/app/build/outputs/apk/debug/app-debug.apk
```

`-r`은 기존 로그인 정보와 앱 데이터를 유지하면서 새 APK를 덮어씁니다. 완전히 새 가입 흐름을 시험하려면 에뮬레이터 설정에서 앱 데이터를 삭제하거나 앱을 제거한 뒤 다시 설치합니다. 에뮬레이터 serial은 실행 순서에 따라 달라질 수 있으므로 항상 `adb devices` 결과를 먼저 확인하십시오.

앱 이용 흐름:

1. `처음 가입하기`에서 이름과 전화번호 입력
2. 충청북도 → 시/군 → 읍/면/동 선택
3. 해당 지역 지도로 이동해 공식 팜맵 Polygon 중 본인 농경지를 터치하고 확인
4. 백엔드가 선택 Polygon·PNU·면적·대표좌표를 저장하고 인근 관측소를 연결
5. 연결 관측소의 트리거 조건 충족 시 등록 농경지만 영상 제작
6. 영상 제작 완료 후 Android 시스템 알림 표시
7. 알림을 누르면 앱이 열리고 해당 MP4를 즉시 재생

보호자 이용 흐름:

1. 가입 유형에서 `보호자 가입` 선택
2. 보호자 이름과 이미 가입한 농업인의 이름·전화번호 입력
3. 농업인의 농경지와 최신 영상 알림을 동일하게 조회
4. 농업인이 최신 영상을 열기 전에는 빨간 미확인 상태, 연 뒤에는 파란 확인 상태 표시

보호자 화면은 미확인 상태를 5초마다 갱신합니다. 확인이 감지되면 반복 조회를 멈추며, 새로운 영상 알림이 도착하면 앱 내부 신호로 최신 영상 기준 조회를 다시 시작합니다. 보호자가 영상을 재생한 것은 농업인의 확인으로 처리하지 않습니다.

로그인 토큰은 Android `SharedPreferences`에 저장되므로 앱을 종료하거나 다시 실행해도 로그인이 유지됩니다. 로그아웃하면 토큰과 마지막 알림 위치를 제거합니다. 회원 탈퇴는 홈 우측 하단 버튼에서 재확인 후 처리되며, 계정·농경지·관측소 연결은 삭제하고 과거 재난 제작 이력은 사용자 식별정보를 익명화하여 보존합니다.

모바일 API:

- `GET /api/mobile/regions`: 충북 전체 시·군과 읍·면·동 선택 데이터
- `POST /api/mobile/auth/signup`: 이름·전화번호·행정구역·선택한 팜맵 `parcelId`로 가입
- `POST /api/mobile/auth/login`: 이름·전화번호 로그인
- `POST /api/mobile/auth/guardian/signup`: 보호자 이름과 농업인 이름·전화번호로 연결 가입
- `POST /api/mobile/auth/guardian/login`: 동일한 연결 정보로 보호자 로그인
- `GET /api/mobile/me`: 저장된 토큰으로 사용자·농경지 복구
- `GET /api/mobile/notifications`: 영상 제작이 완료된 사용자 알림 조회
- `POST /api/mobile/notifications/{id}/read`: 알림 읽음 처리
- `DELETE /api/mobile/me`: 확인 절차 후 회원·세션·농경지·알림 수신정보 삭제

현재 MVP/에뮬레이터 시연에서는 앱의 foreground 알림 릴레이가 3초 간격으로 백엔드의 완성 알림을 확인해 Android 고우선순위 시스템 알림으로 표시합니다. 따라서 Firebase 프로젝트나 `google-services.json` 없이 Pixel 에뮬레이터에서 바로 시연할 수 있습니다. 실제 배포 시에는 동일한 DB 알림 발행 지점에 Firebase Cloud Messaging 발송 어댑터를 추가하고, 앱의 릴레이 서비스를 FCM 수신 서비스로 교체하는 것이 권장됩니다.

시연 순서:

```text
PostgreSQL 실행 → Spring 실행 → Pixel 앱에서 청주시/강내면 가입
→ 8080에서 강내면_mock_4 선택 → 트리거발생
→ 영상 제작 100% → Pixel 시스템 알림 터치 → 영상 자동재생
```

## 트리거와 관측 API

수위가 관심 이상이면 `ARMED`, 그 상태에서 향후 24시간 예보 강수 합계가 임계값 이상이면 `FIRED`가 되고 한 번만 알림과 영상 작업을 만듭니다. 조건이 정상으로 돌아온 뒤 다시 충족되어야 새 작업이 생깁니다.

- `GET /api/stations`: 충북 관측소 현재 수위·위험등급 목록
- `GET /api/stations?district=괴산군`: 시군 필터
- `GET /api/stations/{stationCode}`: 기준수위와 시간대별 24시간 강수예보
- `GET /api/alerts`: 발생 알림 이력
- `GET /api/production-jobs`: 영상 제작 작업 이력

mock 1은 관심/80mm, mock 2는 관심/50mm, mock 3은 괴산군 수동 검증용입니다. `강내면_mock_4`는 실제 `청주시(미호강교)`의 위치·기준수위를 사용하며 `트리거발생`과 `정상Return` 버튼을 제공합니다. 강내면 가입 농경지가 있으면 농경지별로 영상 제작 후 송신하고, 없으면 트리거 이력만 남깁니다. 시작과 동시에 mock 영상을 만들던 과거 동작은 기본적으로 꺼져 있습니다.

8080 트리거 목록의 파란 `영상 제작 후 송신` 표시는 등록 사용자·농경지가 연결된 경우이고, 빨간 `영상 제작 하지 않음`은 관측 조건은 충족했지만 송신할 가입 농경지가 없는 경우입니다. 트리거 기록과 영상 제작 여부를 분리했기 때문에 관제 이력은 누락되지 않습니다.

## 경고 영상 제작과 저장 정책

기본 V9 처리 순서:

```text
트리거 → 컨텍스트 → 대본 Agent → 안전성 검토 Agent → 시각 자료
       → 디지털 트윈 원본 확보 → OpenAI TTS → 자막·영상 합성 → 최종 검증
```

Spring은 `services/team-flood`의 통합 Worker를 호출하며 기본값은 V23 사전 렌더 자산 기반 4-Agent 경로입니다. 현재 upstream은 오송 데모 필지·사용자 3쌍만 제공하므로 MVP 기본 프로필은 화면과 같은 `OSONG-FIELD-DEMO-003`/`USER-DEMO-003`이고, 원래 FarmerFlood 사용자·농지 ID는 이벤트 metadata에 별도로 보존됩니다. 실제 등록 농지별 V23 자산이 준비되면 이 데모 프로필 매핑을 제거해야 합니다. V23 자산이 없을 때는 기존 V9으로 조용히 후퇴하지 않고 요청을 실패시킵니다. 기존 `warning_video_agents`는 참고·회귀용으로 보존하지만 연결은 끊겨 있습니다. 원본 provenance와 통합 변경은 `services/team-flood/UPSTREAM.md`에 기록합니다.

V23 처리 순서:

```text
검증된 트리거 이벤트 → 필지 소유권 확인 → 대본 Agent → 병렬 TTS Agent
  → 필지별 사전 렌더 자산 선택·합성 Agent → 최종 80초 합성 Agent
```

```text
services/team-flood/runtime/
  digital-twins/{지역}/{개인화영역}/{시나리오버전}/
    digital-twin-base.mp4       # 자막·TTS 전 원본, 공유·재사용
    base-render-report.json
  jobs/{관측소}_{시각}_{worker-id}/
    job.json, progress.json, workflow.log
    workspace/                  # 대본, TTS, 자막, 합성과 작업별 로그

runtime/media/{관측소}_{시각}/
  final-warning.mp4             # 개인화된 최종 결과, 매번 신규 생성
```

디지털 트윈 원본 재사용 조건은 화면 자체를 결정하는 **지역, 개인화 농경지, 시나리오 버전**입니다. 기상격자·실시간 수위·위험등급·예상강수량은 대본·TTS·자막만 바꾸므로 캐시 키에 포함하지 않습니다. `시나리오 버전`은 카메라 이동, 침수 단계, 수면 표현, 최대 침수 범위 등 디지털 트윈 연출이 변경됐을 때 기존 영상을 무효화하기 위한 식별자입니다.

작업 폴더에는 중앙 원본 MP4와 원본 `.blend`를 복사하지 않고 심볼릭 링크로 연결합니다. 따라서 같은 농경지·시나리오의 반복 트리거는 긴 Blender 렌더링을 생략하지만, `runtime/media/.../final-warning.mp4`는 사용자별 대본·TTS·자막 결과이므로 절대 재사용하지 않습니다. MVP에서는 작업 이력을 자동 삭제하지 않으며, 향후 보관기한을 정할 때 DB 작업 상태와 최종 파일을 함께 정리해야 합니다.

영상 카드의 `상세보기`는 단계, Worker 생존 여부, Blender 프레임, 캐시 적중 여부와 전체·렌더·합성 로그를 보여줍니다. 진행 중일 때만 2초 간격으로 갱신하며 완료·실패 후에는 폴링을 중단합니다.

## 검증

```bash
./gradlew test
cd services/team-flood
PYTHONPYCACHEPREFIX=/tmp/farmer-flood-pycache \
  .venv/bin/python -m compileall -q api agents
```

DB 연결은 `http://localhost:8080/actuator/health`에서 확인할 수 있습니다. 실제 OpenAI TTS까지 실행하려면 유효한 `OPENAI_API_KEY`가 필요합니다.
