# Jira 이슈 일괄 추출 유틸리티 (`01_issues_export`)

Jira REST API (`/rest/api/2/search`)와 동적 JQL 검색을 활용하여 특정 프로젝트 내 이슈 데이터(이슈 키, 요약, 이슈 유형, 상태)를 스캔하고 CSV 파일로 내보내는 추출 도구입니다.

---

## 주요 기능

1. **JQL 동적 조건 필터링**:
   - 프로젝트 키, 이슈 유형, 상태, 생성 일자 범위를 지정하여 맞춤형 이슈 검색
2. **페이지네이션 및 일괄 수집**:
   - REST API 페이지네이션(Pagination)을 통한 대량 이슈 연속 수집
3. **Excel 호환 CSV 출력**:
   - 한글 깨짐 방지를 위한 UTF-8-BOM (`utf-8-sig`) 인코딩 기반 CSV 저장

---

## 환경 설정 및 사전 준비

### 1. 의존성 패키지 설치
```bash
uv sync
```
*(또는 `pip install -r requirements.txt`)*

### 2. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 Jira 접속 주소 및 API 토큰을 설정합니다.

```bash
cp .env.example .env
```

`.env` 설정 예시:
```ini
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-api-token
```

---

## 검색 조건 설정 및 실행

### 1. 검색 필터 설정 (`jira_issues_export.py`)
스크립트 상단의 `======== 조회 조건 설정 ========` 블록에서 필터 항목을 지정합니다.

```python
PROJECT_KEY = "AFF"                         # 대상 Jira 프로젝트 키
ISSUE_TYPES = ["버그", "개선"]               # 대상 이슈 유형 (빈 배열 시 전체)
STATUSES = []                               # 대상 상태 목록 (빈 배열 시 전체)
CREATED_FROM = "2024-01-01"                 # 생성일 시작 지점 (YYYY-MM-DD)
CREATED_TO = "2026-03-31"                   # 생성일 종료 지점 (YYYY-MM-DD)
OUTPUT_CSV = "jira_issues_export.csv"       # 출력 CSV 파일명
```

### 2. 스크립트 실행
```bash
uv run python jira_issues_export.py
```
*(또는 `python jira_issues_export.py`)*

---

## 출력 결과물 (`jira_issues_export.csv`)

- **출력 헤더**: `IssueKey`, `Summary`, `IssueType`, `Status`
- 엑셀 및 데이터 분석 도구에서 직접 호환되는 CSV 파일이 추출됩니다.

---

## 라이선스
MIT License