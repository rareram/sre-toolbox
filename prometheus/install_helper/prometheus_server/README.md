# Prometheus Server 설치 및 관리 유틸리티 (`prometheus_server`)

Prometheus Server의 자동 설치, OS 패키지 환경 마이그레이션, TSDB 스토리지 스냅샷 생성 및 버전 업데이트/롤백 등 서버 운영 전반을 지원하는 대화형 유틸리티 스크립트입니다.

---

## 파일 구성

- `installer.sh`: Prometheus Server 설치, 스냅샷 관리, 패키지 마이그레이션을 처리하는 대화형 Bash 스크립트
- `backup/`: 이전 버전 스크립트 보관 디렉토리

---

## 실행 방법 및 요구사항

### 1. 실행 권한 부여 및 스크립트 실행
```bash
chmod +x installer.sh
sudo ./installer.sh
```
*(참고: systemd 서비스 등록 및 데이터 디렉토리 관리를 위해 root/sudo 권한이 필요합니다.)*

---

## 주요 지원 기능

대화형 메뉴를 통해 다음 운영 관리 기능을 수행할 수 있습니다.

1. **스토리지 및 스냅샷 관리**:
   - TSDB 스토리지 디스크 사용량 및 파일 구성 검사
   - 실시간 TSDB 데이터 스냅샷 생성 및 목록 조회
2. **패키지 환경 마이그레이션**:
   - OS 패키지(YUM/APT)로 설치된 기존 Prometheus 환경을 독립 바이너리 구성으로 정제 마이그레이션 (기존 데이터 및 설정 보존)
3. **버전 업데이트 및 롤백**:
   - 명시한 특정 버전으로 Prometheus Server 업데이트 및 롤백 지원
   - 임시 다운로드 바이너리 정리 기능 제공
4. **TSDB 데이터 동기화**:
   - 데이터 정합성 검사 및 TSDB 스토리지 상태 동기화 처리

---

## 참고 문서
- Prometheus 공식 문서: [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

---

## 라이선스
MIT License
