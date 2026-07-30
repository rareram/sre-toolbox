# Grafana 대시보드 백업 및 복구 유틸리티 (`dashboard_export`)

Grafana REST API 또는 Grafana SQLite DB 파일에서 대시보드를 JSON 형태로 일괄 추출(Export)하고, UID 보존 및 버전 관리를 지원하며 업로드(Import)하는 유틸리티 모음입니다.

---

## 주요 구성 파일

- `export_all_dashboards.py`: Grafana REST API 기반 전체 대시보드 JSON 백업 (Pagination 및 폴더 구조 유지)
- `import_dashboard.py`: JSON 대시보드 파일 업로드/복구 (UID 보존 및 백업 기능)
- `export_dashboard_via_sqlite.py`: Grafana SQLite DB 파일(`grafana.db`)에서 대시보드 직접 추출
- `.env.example`: Grafana API 접속 정보 환경 변수 템플릿

---

## 환경 설정 및 사전 준비

### 1. 의존성 설치
```bash
pip install requests python-dotenv
```

### 2. Grafana API 서비스 계정(Service Account) 생성
1. Grafana 웹 UI 접속 (`Administration` > `Users and access` > `Service accounts`)
2. `Create service account` 클릭 (Role: `Admin` 지정)
3. `Add service account token`을 클릭하여 API 토큰 생성 및 복사

### 3. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 접속 정보를 설정합니다.

```bash
cp .env.example .env
```

`.env` 설정 예시:
```ini
GRAFANA_URL=http://your-grafana-server:3000
GRAFANA_TOKEN=your-admin-api-token-here
```

---

## 사용법

### 1. Grafana API를 통한 전체 대시보드 추출
```bash
python export_all_dashboards.py
```
- **결과물**: `grafana_export_YYYYMMDD_HHMMSS/` 디렉토리에 폴더별로 JSON 파일 저장
- **파일명 형식**: `{UID}_{제목}_v{버전}.json`

### 2. SQLite DB 파일에서 직접 추출
API 접근이 불가능하거나 서버 로컬 DB 파일(`grafana.db`)을 다룰 때 사용합니다.

```bash
# 동일 경로에 grafana.db 위치 후 실행
python export_dashboard_via_sqlite.py
```
- **결과물**: `dashboards_from_db_export/` 디렉토리에 폴더별 JSON 파일 추출

### 3. 대시보드 업로드 및 복구
```bash
# 기본 업로드 (자동 백업 수행)
python import_dashboard.py path/to/dashboard.json

# 백업 없이 즉시 업로드
python import_dashboard.py path/to/dashboard.json --no-backup
```

---

## 주요 검증 포인트 및 유의사항

1. **UID 보존**:
   - 대시보드의 UID가 변경되면 연결된 Grafana Alert(알람) 및 외부 링크가 유실되므로 업로드 시 UID 보존 여부를 반드시 확인해야 합니다.
2. **Revision 버전 자동 관리**:
   - 동일 UID 대시보드 업로드 시 Grafana 내부 버전(Revision)이 자동으로 1 증가합니다.
3. **패널 Description 연동**:
   - 추출된 JSON 내 `panels[].description` 속성을 조작한 뒤 업로드하여 패널별 설명 문구를 일괄 업데이트할 수 있습니다.

---

## 라이선스
MIT License
