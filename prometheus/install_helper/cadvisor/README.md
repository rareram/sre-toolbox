# Google cAdvisor Exporter 설치 유틸리티 (`cadvisor`)

컨테이너(Docker, Podman, containerd 등)의 CPU, 메모리, 네트워크, 디스크 I/O 자원 사용량을 모니터링하는 Google cAdvisor Exporter 자동 설치, 수집 모드 구성 및 관리 대화형 스크립트입니다.

---

## 파일 구성

- `installer.sh`: cAdvisor 설치, 수집 옵션 설정, systemd 서비스 등록, 미사용 바이너리 정리 및 삭제를 처리하는 대화형 Bash 스크립트
- `samples/`: 시나리오별 실행 인수 샘플 파일
  - `samples/args.standard`: 전체 수집 모드 실행 인수 예시
  - `samples/args.lightweight`: 경량 수집 모드 실행 인수 예시
- `backup/`: 이전 버전 스크립트 보관 디렉토리

---

## 실행 방법 및 요구사항

### 1. 실행 권한 부여 및 스크립트 실행
```bash
chmod +x installer.sh
sudo ./installer.sh
```
*(참고: systemd 서비스 등록 및 컨테이너 자원 모니터링을 위해 root/sudo 권한이 필요합니다.)*

---

## 수집 모드 선택 가이드

컨테이너 환경은 프로세스 및 네트워크 인터페이스 생성이 자주 일어나므로 수집 모드를 적절히 선택해야 모니터링 서버(Prometheus)의 부하 및 TSDB 시계열 폭증(Cardinality Explosion)을 방지할 수 있습니다.

1. **전체 수집 모드 (Standard)**:
   - cAdvisor 기본 설정대로 모든 컨테이너 메트릭 수집
   - 소규모 환경이나 단일 컨테이너 상세 디버깅용으로 적합
2. **경량 수집 모드 (Lightweight) - 운영 권장**:
   - 대규모 컨테이너 환경을 모니터링할 때 권장
   - CPU, 메모리, 네트워크 트래픽 등 핵심 지표는 유지하면서, 부하를 유발하는 비핵심 지표 및 과도한 수집 주기 조절
   - **적용 옵션**:
     - `--housekeeping_interval=10s` (수집 주기를 1초 ➔ 10초로 확장)
     - `--disable_metrics=disk,udp,percpu,sched,tcp` (비핵심 지표 비활성화)

---

## 수신 포트 및 메트릭 확인

- **기본 포트**: `8080` (이미 사용 중일 경우 `9101` 번부터 사용 가능한 포트로 자동 변경)
- **메트릭 엔드포인트**: `http://<SERVER_IP>:8080/metrics`

---

## 참고 문서
- 상세 메트릭 명세: [cAdvisor GitHub](https://github.com/google/cadvisor)

---

## 라이선스
MIT License

