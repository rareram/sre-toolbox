# SRE 장애 상황 알림 봇 (`incident-comm-bot`)

장애 발생 시 비정형 메시지(로그, 상황 요약 등)를 수신하여 수신 대상별(개발팀/직책자/고객용) 보고 문구 및 대응 타임라인을 자동 생성하는 LLM 기반 유틸리티 서비스입니다.

---

## 주요 기능

1. **수신 대상별 보고서 자동 생성**:
   - 장애 메시지를 수신하여 대상(개발팀 상세 기술용, 경영진/직책자 요약용, 사용자 공지용)에 맞춘 문구 자동 변환
2. **장애 타임라인 누적 관리**:
   - 동일 장애 번호(`incident_id`) 기준 경과 시간 계산 및 누적 조치 이력 관리
3. **초기 대응 가이드 제공**:
   - 장애 유형(DB, Web/App 등)에 따른 초기 점검 명령어 및 플레이북 제공

---

## 실행 방법

### 1. 의존성 설치
```bash
uv sync
```
*(또는 `pip install -r requirements.txt`)*

### 2. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 사용할 LLM 엔드포인트(Ollama / vLLM / OpenAI 등) 설정

```bash
cp .env.example .env
```

### 3. 애플리케이션 실행
```bash
uv run python app.py
```

---

## API 엔드포인트

### 1. 헬스 체크 (`GET /healthz`)
- 서비스 정상 동작 상태 확인

### 2. 보고서 생성 요청 (`POST /generate`)
- 장애 raw 메시지 전달 및 수신 대상별 보고서 생성 요청

```json
{
  "raw_incident": "2026-07-24 12:00 DB 서버 응답 없음, 결제 지연 발생 중",
  "incident_id": "INC-PAY-01"
}
```

---

## 라이선스
MIT License
