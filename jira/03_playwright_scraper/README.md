# Playwright 기반 Jira 웹 스크래퍼 (`03_playwright_scraper`)

API 토큰 사용이 제한되거나 웹 기반 인터페이스 접근이 필요한 환경에서, Playwright 헤드리스 브라우저 자동화를 통해 Jira 이슈 화면의 상세 본문, 상태, 댓글 등의 데이터를 직접 스크랩하여 JSON으로 내보내는 유틸리티입니다. (AI 이슈 분석 노드 입력 데이터 수집 등에 활용)

---

## 주요 기능

1. **자동 로그인 및 세션 지속성 (Persistent Session)**:
   - 처음 로그인 성공 후 브라우저 세션 상태(`.sessions/`)를 저장하여 재실행 시 로그인 과정 생략
2. **봇 감지 방지 (Stealth Mode)**:
   - `playwright-stealth` 모듈을 적용하여 웹 자동화 탐지 및 블록 방지
3. **구조화된 JSON 데이터 출력**:
   - 스크랩된 이슈 데이터를 AI 노드 및 2차 가공 시스템에서 소비할 수 있는 표준 JSON 포맷으로 저장

---

## 환경 설정 및 사전 준비

### 1. 의존성 패키지 및 브라우저 설치
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 웹 로그인 계정 정보를 입력합니다.

```bash
cp .env.example .env
```

`.env` 설정 예시:
```ini
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your_username
JIRA_PASSWORD=your_password
```

---

## 사용법

```bash
python jira_playwright_scraper.py <ISSUE_KEY>
```
*예시:*
```bash
python jira_playwright_scraper.py TSC-1234
```

- **출력 결과물**: `issues/<ISSUE_KEY>.json` (프로젝트 루트 하위 `issues/` 디렉토리에 저장)

---

## 라이선스
MIT License
