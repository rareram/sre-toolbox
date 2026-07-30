# Linux 서비스 상태 및 버전 점검 유틸리티 (`service_chk`)

리눅스 서버 환경에서 실행 중인 Docker 컨테이너, 바이너리 프로세스, systemd 서비스의 가동 상태(실행 여부 및 시작 시각)와 주요 소프트웨어의 버전 정보를 수집하여 요약 리포트를 생성하는 스크립트 유틸리티입니다.

---

## 주요 점검 유형 (`service_chk.conf`)

설정 파일(`service_chk.conf`)을 통해 점검 대상을 정의하며 4가지 감지 타입을 지원합니다.

1. **Docker 컨테이너 (`docker`)**:
   - Docker 컨테이너 실행 상태 및 시작 시각(`StartedAt`) 수집
2. **바이너리 프로세스 (`binary`)**:
   - 프로세스명/경로(`pgrep`) 검색을 통한 프로세스 활성화 상태 및 가동 시각 수집
3. **systemd 서비스 (`system`)**:
   - `systemctl` 기반 서비스 상태(`is-active`) 및 시작 시각(`ActiveEnterTimestamp`) 수집
4. **버전 정보 (`version`)**:
   - 주요 런타임 및 도구(Python, Java, Node.js, Docker, MySQL, OpenSSL 등) 버전 수집

---

## 설정 방법 (`service_chk.conf`)

`서비스명:타입:검색어_또는_명령어` 형식으로 점검 항목을 설정합니다.

```ini
# Docker 컨테이너 점검
open-webui:docker:open-webui

# 바이너리 프로세스 점검
promtail:binary:/usr/local/bin/promtail
ollama:binary:/usr/local/bin/ollama

# systemd 시스템 서비스 점검
grafana:system:grafana-server
prometheus:system:prometheus
mysql:system:mysqld

# 소프트웨어 버전 점검
python3:version:python3 -V
java:version:java -version
docker:version:docker --version
```

---

## 실행 및 실무 활용 가이드

### 1. 스크립트 수동 실행
```bash
chmod +x service_chk_time.sh
./service_chk_time.sh
```
- 실행 시 동일 디렉토리에 `service_chk.txt` 리포트 파일이 생성됩니다.

### 2. 실행 권한 및 경로 점검 권고사항
- **프로세스 및 Docker 접근 권한**: 스크립트를 실행하는 유저 계정이 Docker 데몬 조회를 위한 권한(`docker` 그룹 소속 여부) 또는 `systemctl` 상태 조회 권한을 정상적으로 보유하고 있는지 확인하십시오.
- **디렉토리 쓰기 권한**: 스크립트가 구동되는 경로에 로그(`service_chk.log`), 이전 상태 파일(`service_chk_state.txt`), 출력 리포트(`service_chk.txt`)를 작성할 수 있는 쓰기 권한이 있는지 점검하십시오.

### 3. SSH 접속 시 자동 상태 출력 (`~/.bashrc` 연동)
사용자가 서버에 SSH 접속할 때마다 최신 서비스 가동 현황을 터미널에 표시하려면 `~/.bashrc` 또는 `~/.bash_profile` 하단에 아래 구문을 추가합니다.

```bash
# SSH 접속 시 서버 서비스 상태 리포트 출력
if [ -f "/path/to/linux/service_chk/service_chk.txt" ]; then
    cat /path/to/linux/service_chk/service_chk.txt
fi
```

### 4. Cron 주기적 상태 업데이트 (Crontab 연동)
주기적으로 서버 상태를 스캔 및 갱신하도록 `crontab -e`에 등록합니다. (예: 10분 주기)

```cron
*/10 * * * * /path/to/linux/service_chk/service_chk_time.sh >/dev/null 2>&1
```

---

## 출력 결과물 예시 (`service_chk.txt`)

```text
서비스 상태 (마지막 업데이트: 2026-07-30 14:00:00)
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
 ▪ open-webui           docker   실행중 (시작: 2026-07-29 10:15:00)
 ▪ promtail             binary   실행중 (시작: 2026-07-29 10:16:00)
 ▪ grafana              system   실행중 (시작: 2026-07-29 10:16:05)
 ▪ python3              version  3.10.12
 ▪ docker               version  24.0.5
════════════════════════════════════════════════════════════════════
```

---

## 라이선스
MIT License
