# SRE Incident Triage Bot (`incident-triage-bot`)

Grafana 알람을 받아 동일 서비스 단위로 장애를 묶고, 엔지니어와 대화하며 증상 지표와 원인 지표를 분리해 1차 원인 분석과 점검 플레이북을 안내하는 경량 SRE 트리아지 엔진입니다.

---

## 1. 시스템 의존성 구분 (필수 vs 선택)

이 봇은 외부 모니터링 인프라가 완전히 갖춰지지 않은 환경에서도 즉시 구동할 수 있도록 설계했습니다.

### 필수 시스템 (Minimal Essentials)
외부 관측성 도구 없이도 봇 자체의 판단, 대화, 서버 정보 검색 기능은 100% 동작합니다.
- **Python 3.10 이상**: `uv` 또는 표준 `venv` 환경
- **LLM 추론 엔드포인트**:
  - 로컬 개발: Ollama (`gemma4`, `llama3.1` 등)
  - 폐쇄망/사내 서버: vLLM, TGI, LocalAI
  - 퍼블릭 클라우드: OpenAI, Azure OpenAI
- **서버 인벤토리 CSV (`config/servers.csv`)**: 서버 IP, 호스트명, 물리 랙 위치, 담당자, 점검 명령어가 담긴 파일 (샘플 템플릿 기본 제공)
- **로컬 파일 저장소 (SQLite)**: 장애 발생 시 주 시스템 DB 장애와 격리하기 위해 자체 파일 DB(`triage.db`, WAL 모드) 사용

> Prometheus나 Loki가 없어도 기본 모의 러너(Mock Runner)가 동작하므로, 로컬 환경이나 격리망에서 즉시 테스트할 수 있습니다.

### 선택 시스템 (Extended Observability)
실제 운영 인프라에 연결하면 봇이 실측 데이터를 자동으로 수집해 더 정밀하게 진단합니다.
- **Grafana**: Alertmanager 웹훅을 봇(`POST /webhook/grafana`)으로 전송해 알람 자동 수집 및 인시던트 생성
- **Prometheus**: 실시간 PromQL 지표 추세 수집 (P99 레이턴시, 5xx 에러율, DB 커넥션 풀, CPU/메모리 추세)
- **Loki**: 알람 발생 전후 15분간의 서비스/파드 에러 로그(LogQL) 스냅샷 자동 수집
- **Pyroscope**: CPU 및 메모리 스파이크 시점의 Continuous Profiling 화염 그래프 조회
- **Laya / Kev**: 10~30ms 내 단일 순전파로 상태를 분절화하는 System 1 실시간 판단 모델

---

## 2. 환경 설정 (.env)

`.env.example` 파일을 복사해 `.env`를 생성합니다.

```bash
cp .env.example .env
```

### 최소 구동 설정 (로컬 Ollama 기준)
외부 모니터링 연동 없이 로컬에서 바로 띄울 때의 설정입니다.

```properties
# 1. LLM 설정
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=gemma4:e4b-mlx

# 2. 서버 인벤토리 및 DB
INVENTORY_FILE_PATH=config/servers.example.csv
DATABASE_PATH=triage.db
CORRELATION_WINDOW_SECONDS=60
INCIDENT_MAX_IDLE_SECONDS=1800
```

### 실측 관측성 스택 연동 설정 (운영 환경)
실제 Prometheus와 Loki를 연결할 때는 환경변수 플래그와 접속 정보를 활성화합니다.

```properties
# 실측 텔레메트리 및 도구 활성화 플래그
USE_REAL_TELEMETRY=true
USE_REAL_TOOLS=true

# Prometheus (오픈소스 기본은 무인증, 프록시 환경에 따라 Basic/Bearer 선택)
PROMETHEUS_URL=http://prometheus.internal:9090
PROMETHEUS_BEARER_TOKEN=

# Loki (사내 멀티테넌트 환경 지원)
LOKI_URL=http://loki.internal:3100
LOKI_TENANT_ID=fake
LOKI_BEARER_TOKEN=
```

### 판단 모델 설정 (일반 vs 고급 옵션)
- **일반 옵션**: 일상적인 모델 백엔드 지정
  ```properties
  DECISION_BACKEND=rule   # rule | laya | kev | jev
  DECISION_API_URL=http://localhost:8000
  ```
- **고급 옵션 (Advanced)**: 기본값 유지를 강력히 권장합니다. 값을 올리면 장애 시점 텔레메트리 쿼리 폭증과 응답 지연을 부를 수 있습니다.
  ```properties
  DECISION_MAX_LOOPBACK_HOPS=1           # 불확실 시 추가 관측 최대 횟수 (기본값: 1)
  DECISION_LOOPBACK_TIMEOUT_SECONDS=1.5  # 루프백 1회당 최대 타임아웃
  DECISION_CONFIDENCE_THRESHOLD=0.85     # 즉시 확정 신뢰도 임계치
  ```

---

## 3. 설치 및 실행 (Deploy & Run)

### 1) 로컬 개발 환경 구동

의존성을 설치하고 FastAPI 서버를 띄웁니다.

```bash
# 가상환경 생성 및 패키지 설치
uv sync

# 서버 실행 (기본 포트: 8080)
uv run uvicorn src.app:app --host 0.0.0.0 --port 8080 --reload
```

서버 정상 동작 확인:
```bash
curl http://localhost:8080/healthz
```

### 2) 전체 테스트 검증 (41개 테스트)

모든 단위 기능, 회귀 방지, 수명주기 격리 테스트를 1초 이내에 검증합니다.

```bash
uv run pytest
```

### 3) 프로덕션 서비스 배포 (Systemd 등록 예시)

단일 VM이나 관리 서버에서 데몬으로 띄울 경우 systemd 유닛 파일을 사용합니다.

`/etc/systemd/system/incident-triage-bot.service`:
```ini
[Unit]
Description=SRE Incident Triage Bot Service
After=network.target

[Service]
Type=simple
User=sre
WorkingDirectory=/opt/sre-toolbox/bots/incident-triage-bot
EnvironmentFile=/opt/sre-toolbox/bots/incident-triage-bot/.env
ExecStart=/opt/sre-toolbox/bots/incident-triage-bot/.venv/bin/uvicorn src.app:app --host 0.0.0.0 --port 8080 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now incident-triage-bot
```

### 4) 컨테이너 배포 (Dockerfile 예시)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv sync --no-dev

COPY config/ config/
COPY src/ src/

EXPOSE 8080
CMD [".venv/bin/uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 4. 실무 운영 및 활용 가이드

### A. 긴급 상황 대화창 단축 명령어
야간이나 이동 중 빠른 장비 식별이 필요할 때, LLM 추론을 거치지 않고 O(1) 인메모리 카탈로그에서 즉시 검색해 0.01초 내에 응답합니다.
- `/server 10.19.20.104` 또는 `/서버 10.19.20.104`: IP로 서버 물리 위치, 랙 번호, 담당자, 점검 명령어 조회
- `/server spark-worker-04`: 호스트명으로 장비 메타데이터 단건 조회
- `/lookup MySQL`: 역할이나 서비스 키워드로 관련 장비 다건 검색

### B. 자연어 트리아지 질의
- 대화창에 `"결제 서버 에러 로그 확인해줘"` 또는 `"DB 지연 원인이 뭐야?"`를 입력하면, 봇이 사전에 수집한 P99 지표 추세와 최근 에러 로그 스냅샷을 결합해 증상(결과)과 원인 과정을 분리해 답변합니다.
- 최근 30분 이내 배포가 있었다면 복잡한 디버깅 대신 롤백을 최우선 실행 버튼으로 제안합니다.

---

## 5. 주요 API 엔드포인트

| Method | 경로 | 용도 | 비고 |
|:---|:---|:---|:---|
| `GET` | `/healthz` | 서비스 헬스체크 및 설정 로딩 상태 확인 | k8s Liveness/Readiness 프로브 연동 |
| `POST` | `/webhook/grafana` | Grafana Alertmanager 웹훅 수신 | 60초 윈도우 기반 단일 인시던트 자동 병합 |
| `POST` | `/api/chat` | 메신저 봇 대화 및 트리아지 질의 | 단축 명령어(`/server`) 및 LLM 추론 지원 |
| `POST` | `/api/action` | 점검 도구 실행 | 안전한 읽기 전용 도구만 화이트리스트 실행 |
| `GET` | `/api/incidents/{id}` | 인시던트 전체 타임라인 및 점검 이력 조회 | 대화 내역 및 실행 결과 통합 반환 |
| `POST` | `/api/incidents/{id}/status` | 인시던트 상태 갱신 | `RESOLVED` 처리 시 후속 알람 분리 |
| `GET` | `/api/catalog/search` | 서버 인벤토리 키워드 부분 검색 | REST API 연동 (`?q=keyword&limit=5`) |
| `GET` | `/api/catalog/servers/{key}` | 서버 IP 또는 호스트명 단건 상세 조회 | O(1) 인메모리 캐시 조회 |
