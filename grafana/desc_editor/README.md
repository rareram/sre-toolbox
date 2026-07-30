# Grafana 패널 Description 편집 유틸리티 (`desc_editor`)

Grafana REST API 연동 및 Streamlit 웹 UI를 기반으로, 대시보드 내 개별 패널의 설명(Description) 문구를 조회, 편집, AI 기반 생성 및 일괄 업데이트할 수 있도록 도와주는 도구 모음입니다.

---

## 주요 기능

1. **대시보드 패널 Description 웹 편집기 (Streamlit)**:
   - Grafana 폴더 및 대시보드 구조 웹 브라우저 탐색
   - 패널 타입 및 메트릭별 Description 개별/일괄 편집
   - AI 기반 패널 설명 자동 생성 연동
2. **CLI 기반 대시보드 탐색 및 일괄 처리 스크립트**:
   - 대시보드 및 폴더 목록, UID 조회 유틸리티 제공
   - JSON 기반 패널 Description 일괄 반영 기능 지원

---

## 환경 설정 및 실행 방법

### 1. 의존성 패키지 설치
```bash
uv sync
```
*(또는 `pip install -r requirements.txt`)*

### 2. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 Grafana 접속 정보를 설정합니다.

```bash
cp .env.example .env
```

`.env` 설정 예시:
```ini
GRAFANA_URL=http://localhost:3000
GRAFANA_TOKEN=your_grafana_api_token_here
GRAFANA_ORG_ID=1
SSL_VERIFY=false
```

### 3. 웹 편집기 애플리케이션 실행
```bash
streamlit run main.py
```
- 실행 후 브라우저(`http://localhost:8501`)를 통해 웹 UI 접속

---

## 포함된 주요 CLI 유틸리티 스크립트

- `list_all_dashboards.py` / `list_folders.py`: 전체 대시보드 및 폴더 목록 조회
- `find_uid.py` / `find_dashboard_by_title.py`: 특정 대시보드 타이틀 기반 UID 및 메타 정보 검색
- `update_dashboard_descriptions.py`: 특정 대시보드의 패널 Description 일괄 업데이트
- `analyze_node_exporter_panels.py`: Node Exporter 패널 구조 분석 유틸리티

---

## 라이선스
MIT License
