# SRE Toolbox

시스템 설치 및 운영 과정에서 반복되는 번거로운 작업을 자동화하는 SRE 도구 모음

---

## 도구 목록

### 1. GitLab 도구 (`gitlab/`)
- **`gitlab-deps-scan`**: 접근 가능한 프로젝트에서 사용 중인 라이브러리의 지원 종료(EOS) 상태를 점검
- **`getinfo`**: 커밋 작성자 식별자(사번, 이메일, 닉네임 등)가 통일되지 않았을 때 메타데이터를 수집하여 정리

### 2. Azure 도구 (`azure/`)
- **`security_scan`**: Azure 클라우드 환경에서 방화벽 및 보안 설정이 누락된 리소스를 자동 점검

### 3. Grafana 도구 (`grafana/`)
- **`desc_editor`**: 대시보드 패널 설명(Description)을 일괄 등록 및 편집
- **`dashboard_export`**: 대시보드 설정을 파일로 일괄 내보내기 및 백업
- **`get_userinfo`**: 사용자별 대시보드 및 폴더 접근 권한 목록 조회
- **`grafana2teams`**: Grafana 패널 화면을 캡처하여 MS Teams 채널로 전송
- **`custom_login`**: Grafana 로그인 화면의 배경과 로고를 맞춤 이미지로 교체
  <p align="left">
    <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/custom_login/custom_login.png" alt="Grafana Custom Login Preview" width="40%" />
  </p>
- **`svg-gen`**: 래스터 이미지(PNG, JPG 등)를 레이어로 배치하고 SVG로 변환하여 Grafana 로그인 배경 생성
  <p align="left">
    <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/svg-gen/svg-gen.png" alt="SVG Gen Interface Preview" width="40%" />
  </p>

### 4. Jira 도구 (`jira/`)
- **`01_issues_export`**: 특정 프로젝트 및 상태의 Jira 이슈를 조회하여 CSV 파일로 저장
- **`02_issues_status`**: Jira 이슈의 상태 변경 이력을 일괄 추출하여 CSV 파일로 저장
- **`03_playwright_scraper`**: Jira 이슈 데이터를 자동 수집하여 AI 분석 파이프라인과 연동

### 5. Linux 도구 (`linux/`)
- **`syschk2xls`**: 리눅스 서버 점검 결과를 엑셀(.xlsx) 보고서로 생성
- **`service_chk`**: 지정한 주요 프로세스 및 데몬 상태 점검 (cron 주기 실행, .bashrc 연동, SSH 접속 시 상태 안내)

### 6. 장애 대응 봇 (`bots/`)
- **`incident-comm-bot`**: Grafana 알림을 로컬 LLM으로 가공하여 대상별(엔지니어/관리자/고객용) 맞춤 메시지 생성 및 장애 대응 타임라인 자동 업데이트

### 7. Prometheus 모니터링 (`prometheus/`)
- **`install_helper/*`**: Linux 환경에서 Prometheus 및 Exporter 제품군을 설치하고 업데이트하는 스크립트
- **`win_exp_inst`**: Windows 환경에서 windows_exporter를 간편하게 설치하는 스크립트

### 8. Tabby 터미널 플러그인 (`tabby/`)
- **`asciinema-helper`**: 터미널 세션 및 백그라운드 프로세스(Docker, Tmux, Herdr 멀티에이전트) 작업 내용을 .cast 포맷으로 녹화하는 Tabby 플러그인.
  <p align="left">
    <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/asciinema-helper/asciinema_1.png" alt="Session Discovery Modal" width="40%" />
    <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/asciinema-helper/asciinema_2.png" alt="Plugin Settings Tab" width="40%" />
  </p>

---

## 의존성 라이브러리 보안 패치 현황

주요 라이브러리 최신 패치 업데이트 현황:
- **`urllib3` (2.7.0)**: 압축 해제 폭탄(Decompression Bomb) 방지 및 리다이렉트 시 자격 증명 유출 방지
- **`setuptools` (83.0.0)**: 파일 경로 조작으로 인한 임시 파일 덮어쓰기 방지
- **`requests` (2.33.0)**: 접속 주소 파싱 오류로 인한 자격 증명(.netrc) 유출 방지
- **`idna` (3.15)**: 특수 문자 처리 시 CPU 고점 점유 현상 방지
- **`python-dotenv` (1.2.2)**: 환경 변수(.env) 설정 변경 시 비의도적 파일 수정 방지
- **`flask` (3.1.3)**: 세션 종료 후 이전 사용자 정보 잔존 방지

