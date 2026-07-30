# SRE Toolbox

프로그램별 설치, 운영 과정에서 귀찮거나 반복하게 되는 작업을 쉽게 도와주는 자동화 도구 모음

---

## 현재까지 정리된 도구 리스트

### 1. GitLab 도구 (`gitlab/`)
- **`gitlab-deps-scan`**: 접근 가능한 프로젝트에 현재 쓰고 있는 라이브러리의 EOS 상태를 스캔
- **`getinfo`**: 커밋 작성자 구분이 통일되지 않았을 경우 (사번, 이메일, 별명 등) 메타 정보를 받아와 정리할때 사용

### 2. Azure 도구 (`azure/`)
- **`security_scan`**: 클라우드(Azure) 방화벽이나 보안 설정이 누락된 자원이 있는지 자동으로 점검할 때 사용

### 3. Grafana 도구 (`grafana/`)
- **`desc_editor`**: 대시보드 그래프 패널에 설명(Description) 문구를 한 번에 입력
- **`dashboard_export`**: 대시보드 설정을 한번에 파일로 일괄 백업
- **`get_userinfo`**: 유저의 권한 목록 조회 (누가 어떤 대시보드와 폴더를 볼 수 있는지)
- **`grafana2teams`**: 그래프 화면을 캡처해서 MS Teams의 특정 채널로 바로 공유
- **`custom_login`**: Grafana 로그인 화면 배경,로고 등을 준비된 이미지로 교체
- **`svg-gen`**: 이미지(png,jpg 등)를 레이어배치 및 SVG로 변환하며 Grafana 로그인 배경 생성

### 4. Jira 도구 (`jira/`)
- **`01_issues_export`**: 특정 프로젝트, 특정 상태의 Jira 티켓을 추출해 csv로 저장
- **`02_issues_status`**: Jira 티켓들의 상태 변화 이력을 일괄 추출해 csv로 저장
- **`03_playwright_scraper`**:  Jira 이슈 데이터를 자동으로 스크랩 (AI로 이슈분석 노드로 활용할때)

### 5. Linux 도구 (`linux/`)
- **`syschk2xls`**: 서버 점검 결과를 엑셀 보고서 형태로 정리.
- **`service_chk`**: 환경에 정의한 주요 프로세스나 데몬 상태 확인 (활용: cron으로 주기적 시행, 결과를 .bashrc에 표시, ssh 접속시마다 상태확인 가능)

### 6. 장애 대응 봇 (`bots/`)
- **`incident-comm-bot`**: Grafana Alert 메시지를 로컬LLM 활용하여 각 보고언어별(개발자/직책자/고객용) 변환 제공 및 간단한 조치 순서(타임라인) 업데이트

### 7. Prometheus 모니터링 (`prometheus/`)
- **`install_helper/*`**: 리눅스 환경에 Prometheus 및 각종 exporter를 쉽게 설치/업데이트를 도와주는 스크립트
- **`win_exp_inst`**: 윈도우 환경에 Prometheus windows_exporter를 쉽게 설치할 수 있도록 도와주는 스크립트

### 8. Tabby 터미널 플러그인 (`tabby/`)
- **`asciinema-helper`**: 서버 CLI 환경의 작업 과정을 영상처럼 녹화하는 Asciinema 를 쉽게 사용할 수 있도록 도와주는 플러그인. 녹화, 업로드, 마스킹 등

---

## 의존성 라이브러리 보안 패치 현황

주요 라이브러리 최신 패치 업데이트 현황:
- **`urllib3` (2.7.0)**: 악의적인 압축 파일로 인한 서버 멈춤(Decompression Bomb) 및 주소 이동 시 비밀번호 유출 방지
- **`setuptools` (83.0.0)**: 파일 경로 조작으로 임시 파일이 덮어씌워지는 현상 방지
- **`requests` (2.33.0)**: 접속 주소 파싱 오류로 비밀번호 파일(.netrc)이 외부로 새어나가는 버그 수정
- **`idna` (3.15)**: 특수 문자 변환 시 서버 CPU가 100%로 솟구치는 현상 방지
- **`python-dotenv` (1.2.2)**: 환경 변수(.env) 설정 변경 시 다른 중요 파일이 실수로 바뀌는 현상 방지
- **`flask` (3.1.3)**: 로그아웃 후 이전 사용자 정보가 웹 화면에 남는 현상 방지
