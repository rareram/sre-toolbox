# Jira 이슈 상태 분석 및 통계 리포터 (`02_issues_status`)

Jira REST API를 통해 특정 프로젝트의 이슈 스냅샷 데이터를 수집하고, 이슈 분류(버그, 지원작업, 기획/관리 등) 및 해결률, 주간(7d) 신규/완료 건수, 30일 이상 미결 방치건 등의 수치 지표를 자동으로 분석하여 통계 리포트 CSV를 생성하는 유틸리티입니다.

---

## 파이프라인 프로세스 및 주요 기능

수집과 통계 분석 2단계 프로세스로 구성됩니다.

1. **이슈 스냅샷 데이터 수집 (`1_jira_issues_collector.py`)**:
   - 지정된 프로젝트 및 이슈 유형의 전체 현황 데이터(이슈 키, 요약, 유형, 상태, 생성일, 해결일, 우선순위, 상세설명, 댓글)를 스캔
   - 수집 결과는 `지라_스냅샷_YYYYMMDD.csv` 형태로 저장됨

2. **이슈 통계 분석 및 요약 생성 (`2_jira_analyzer.py`)**:
   - 스냅샷 CSV를 읽어 업무 카테고리(버그, 개발/개선, 지원작업, 기획/관리 등) 세부 정교 분류
   - 주요 통계 지표 산출 및 리포트 파일(`리포트_요약_YYYYMMDD_HHMM.csv`) 생성
   - 산출 지표: 전체 건수, 해결/미결 건수, 7일 이내 신규/완료, 30일 이상 미결 방치건, 긴급건, 해결률(%)

---

## 환경 설정 및 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 Jira 접속 주소 및 API 토큰 설정:

```bash
cp .env.example .env
```

`.env` 설정 예시:
```ini
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your_api_token_here
```

### 3. 파이프라인 실행

```bash
# 1단계: 스냅샷 수집 실행
python 1_jira_issues_collector.py

# 2단계: 통계 분석 실행 (대상 스냅샷 CSV 파일 번호 선택)
python 2_jira_analyzer.py
```

---

## 출력 결과물

- `지라_스냅샷_YYYYMMDD.csv`: 개별 이슈별 정제 데이터 및 분석 지표 마킹 파일
- `리포트_요약_YYYYMMDD_HHMM.csv`: 프로젝트 및 카테고리별 집계 통계 파일

---

## 라이선스
MIT License
