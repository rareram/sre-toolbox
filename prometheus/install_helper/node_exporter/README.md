# Linux Node Exporter 설치 유틸리티 (`node_exporter`)

리눅스 서버의 하드웨어 및 기본 OS 자원(CPU, Memory, Disk, Network 등)을 모니터링하는 Prometheus Node Exporter를 자동 설치, 수집 모드 구성 및 관리하는 대화형 스크립트입니다.

---

## 파일 구성

- `installer.sh`: Node Exporter 설치, 수집 옵션 설정, 서비스 등록 및 삭제를 수행하는 대화형 Bash 스크립트
- `backup/`: 이전 버전 설치 스크립트 보관 디렉토리

---

## 실행 방법 및 요구사항

### 1. 실행 권한 부여 및 스크립트 실행
```bash
chmod +x installer.sh
sudo ./installer.sh
```
*(참고: systemd 서비스 등록 및 바이너리 설치를 위해 root/sudo 권한이 필요합니다.)*

---

## 수집 모드 선택 가이드

설치 진행 시 모니터링 환경 규모에 따라 2가지 수집 모드 중 선택이 가능합니다.

1. **전체 수집 모드 (Standard)**:
   - Node Exporter의 모든 기본 수집기를 활성화
   - 대상 서버가 소규모(수십 대 이하)이며 커널/파일시스템의 상세 지표까지 확인이 필요한 경우 사용
2. **경량 수집 모드 (Lightweight) - 대규모 권장**:
   - CPU, Memory, Disk, Network 등 핵심 지표는 수집하되, 부하 및 시계열 데이터 폭증을 유발하는 비핵심 수집기 제외
   - **제외되는 주요 수집기**: `arp`, `nfs`/`nfsd`, `wifi`, `zfs`, `ipvs`, `entropy`, `bcache`

---

## 참고 문서
- 상세 메트릭 명세: [Node Exporter GitHub](https://github.com/prometheus/node_exporter)

---

## 라이선스
MIT License
