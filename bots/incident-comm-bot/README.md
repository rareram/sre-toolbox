# 🚨 SRE Incident Communication Bot (`incident-comm-bot`)

`incident-comm-bot`은 급박한 장애 대응 상황에서 온콜 엔지니어가 작성한 파편화된 로그/상황 설명 또는 Grafana 알림을 수신하여, **대상 청중(개발팀 / 리더 / 외부 고객)에 맞춘 3타겟 마크다운 리포트, 긴급 조치 체크리스트, 장애 진행 타임라인**을 자동으로 생성 및 업데이트해 주는 경량 SRE 유틸리티 봇입니다.

---

## 🚀 주요 기능 (Key Features)

1. **Local-First LLM 아키텍처**
   * 보안과 비용 절감을 위해 **로컬 LLM (Ollama, vLLM)**을 기본 백엔드로 사용합니다.
   * 필요 시 `.env` 설정 변경만으로 외부 **OpenAI API (`gpt-4o` 등)**로 손쉽게 스위칭됩니다.

2. **JSON Mode 기반 파싱 에러 0% 보장**
   * LLM 응답을 JSON 구조체로 받아 마크다운 이모지나 헤더 변형에 영향을 받지 않고 100% 안전하게 리포트를 정제합니다.

3. **장애 진척 상황 (타임라인) 자동 누적 추적**
   * 동일한 `incident_id`로 추가 진척 정보가 들어오면, 장애 **최초 발생 시각**, **지속 시간**, **갱신 횟수** 및 **시간순 타임라인**을 누적하여 업데이트합니다.

4. **플레이북 긴급 조치 가이드 힌트 (Remediation Hint)**
   * 장애 유형에 적합한 플레이북 점검 팁 및 CLI 명령어 조치 가이드를 자동으로 함께 제안합니다.

5. **운영 메타데이터 푸터 부착 (좀비 봇 방지)**
   * 발송되는 모든 리포트 하단에 봇 이름, 버전, 호스트, 소유권 정보(`bot-name`, `version`, `owner`, `host`)를 자동 부착하여 Webhook 난립 및 식별 문제를 해결합니다.

6. **Grafana Alert Webhook Direct Adapter**
   * Grafana Alertmanager 알림 JSON을 수신받아 장애 요약 문맥을 자동으로 구성합니다.

---

## 📂 프로젝트 구조

```
incident-comm-bot/
├── app.py                # Flask 기반 HTTP API 서버 & 타임라인 스토리지
├── prompt.py             # LLM 구조화 출력 SYSTEM/USER 프롬프트
├── pyproject.toml        # 의존성 및 pytest 설정
├── .env.example          # 환경 변수 샘플 템플릿
├── README.md             # 프로젝트 문서
└── tests/
    └── test_app.py       # 12가지 항목 pytest 단위/통합 테스트 스위트
```

---

## 🛠️ 빠른 시작 (Quick Start)

### 1. 의존성 설치
[uv](https://github.com/astral-sh/uv) 패키지 매니저를 사용하여 의존성을 동기화합니다.
```bash
uv sync
```

### 2. 환경 변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 만들고 환경에 맞게 수정합니다.
```bash
cp .env.example .env
```

`.env` 설정 예시 (Ollama 기준):
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=gemma4:e4b

BOT_NAME=pay-sre-bot
BOT_VERSION=v0.2.0
BOT_OWNER=sre-team@company.com

TEAMS_WEBHOOK=https://outlook.office.com/webhook/xxxxx
PORT=8080
```


### 3. 서버 실행
```bash
uv run python app.py
```

---

## 📡 API 엔드포인트 명세

### 1. 헬스 체크 & 봇 진단 (`GET /healthz`)
* **응답 예시**:
  ```json
  {
    "status": "ok",
    "bot_name": "pay-sre-bot",
    "bot_version": "v0.2.0",
    "bot_owner": "sre-team@company.com",
    "hostname": "k8s-pod-7f9a",
    "llm_base_url": "http://localhost:11434/v1",
    "llm_model": "qwen2.5-coder",
    "active_incidents": 1
  }
  ```

### 2. 장애 리포트 생성 (`POST /generate`)
* **요청 Body 예시**:
  ```json
  {
    "raw_incident": "2026-07-24 12:00 DB Connection Timeout 발생, 서비스 지연 중",
    "incident_id": "INC-PAY-01",       // (선택) 미입력 시 자동 생성
    "post_to_teams": true,               // (선택) Webhook 전송 여부
    "post_section": "all"                // "all" | "dev" | "leader" | "customer"
  }
  ```

### 3. Grafana Alert Webhook 수신 (`POST /webhook/grafana`)
* Grafana Alertmanager의 Contact Point URL로 `http://<server-ip>:8080/webhook/grafana` 를 등록하여 사용합니다.

---

## 🧪 테스트 실행 (Test Execution)

외부 LLM 서버나 Teams Webhook 없이 `pytest`로 1초 만에 전체 핵심 기능을 검증할 수 있습니다.

```bash
uv run pytest
```

---

## 📄 라이선스
MIT License
