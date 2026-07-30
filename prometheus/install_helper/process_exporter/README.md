# Linux Process Exporter 설치 유틸리티 (`process_exporter`)

리눅스 서버에서 실행 중인 개별 프로세스별 리소스 사용량(CPU, Memory, IO, FD 등)을 모니터링하는 Process Exporter를 자동 설치하고 수집 룰을 구성하는 대화형 스크립트입니다.

---

## 파일 구성

- `installer.sh`: Process Exporter 설치, 설정 파일(`config.yml`) 구성, 서비스 등록 및 삭제를 처리하는 대화형 Bash 스크립트
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

## 프로세스 수집 방식 가이드

운영 서버의 모니터링 카디널리티(Cardinality) 관리를 위해 적절한 수집 방식을 선택해야 합니다.

1. **상세 수집 모드 (Detailed)**:
   - 프로세스명(`{{.Comm}}`), PID(`{{.PID}}`), 실행 계정(`{{.Username}}`)을 모두 포함하여 수집
   - **용도**: 단일 장비 디버깅 및 개발/테스트 환경
   - **주의**: 프로세스 재시작 시 PID 변경으로 시계열(Time-series) 데이터가 폭증(Cardinality Explosion)할 수 있음
2. **그룹 수집 모드 (Grouped) - 운영 환경 권장**:
   - PID를 수집 대상에서 제외하고 실행 파일명(`{{.Comm}}`) 단위로 그룹화하여 합산 수집
   - **용도**: 대규모 운영 서버 및 컨테이너 환경
   - **장점**: 동일 프로세스의 재기동이나 멀티 프로세스 실행 시에도 메트릭이 그룹 단위로 고정되어 서버 안정성 확보

---

## 참고 문서
- 상세 설정법: [Process Exporter GitHub](https://github.com/ncabatoff/process-exporter)

---

## 라이선스
MIT License
