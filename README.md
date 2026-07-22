# SRE Toolbox

인프라 및 어플리케이션 운영 시 발생하는 관리 사각지대 해소와 점검 자동화를 위한 SRE 툴킷 모음.

---

## Components & Purpose

### 1. GitLab (`gitlab/`)
방치된 저장소 파악 및 관리 주체 추적 목적
- **`gitlab-deps-scan`**: 저장소별 라이브러리 의존성 및 EOS(End of Support) 버전 스캔
- **`getinfo`**: 비표준 커밋 사용자명(이메일, 사번 등)을 인사DB 규격으로 매핑하여 실제 작성자 추적

### 2. Azure (`azure/`)
- **`security_scan`**: 클라우드 자원 보안 설정 누락 및 접근 통제 항목 일괄 점검

### 3. Grafana (`grafana/`)
대시보드 파편화, 설명 누락, 권한 관리 문제 해결 목적
- **`desc_editor`**: 대시보드 패널 Description 일괄 편집 및 가시성 확보
- **`dashboard_export`**: 대시보드 설정 일괄 백업 및 이관
- **`get_userinfo`**: 팀/사용자별 대시보드 및 폴더 접근 권한 감사
- **`grafana2teams`**: Grafana 패널 화면 캡처 후 Teams 채널 전파 브라우저 확장 프로그램
- **`custom_login`**: 로그인 페이지 커스터마이징
- **`svg-gen`**: SVG 생성 및 Grafana Login image 생성기

### 4. Jira (`jira/`)
수동 티켓 처리 절차 최소화 및 운영 데이터 수집 목적
- **`01_issues_export` / `02_issues_status`**: 운영 이슈 상태 변경 이력 수집 및 현황 분석
- **`03_playwright_scraper`**: Playwright 기반 이슈 데이터 자동 수집

### 5. Linux (`linux/`)
대규모 인프라 수동 점검 공수 절감 목적
- **`syschk2xls`**: Linux 점검 결과 데이터 엑셀 보고서 자동 가공
- **`service_chk`**: 주요 데몬 및 서비스 프로세스 상태 점검

### 6. MS Teams (`ms-teams/`)
- **`incident-comm-bot`**: 장애 상황 전파 및 타임라인 소통 지원 봇

### 7. Prometheus (`prometheus/`)
서버 추가 시 에이전트 반복 설치 자동화 목적
- **`install_helper`**: Linux 환경(Server, Node Exporter, Process Exporter) 설치 및 유지보수 스크립트
- **`win_exp_inst`**: Windows Exporter GUI 기반 설치 도구

---

> 상세 실행 방법은 각 디렉터리 내부 `README.md` 참고.

