# Process Exporter 설치 도우미

이 폴더는 시스템에서 실행 중인 개별 프로세스의 자원(CPU, 메모리, IO 등) 사용량을 모니터링하는 Process Exporter 설치용 스크립트입니다.

## 파일 구성
* `installer.sh` - 설치, 삭제, 관리를 처리하는 대화형 스크립트
* `backup/` - 구버전 스크립트 보관 폴더

## 프로세스 수집 방식 가이드
프로세스 수집 설정(`config.yml`)은 운영 서버의 안정성을 위해 적절한 방식을 선택해야 합니다.

### 1. 상세 수집 (Detailed)
프로세스의 실행 파일명(`{{.Comm}}`)과 함께 **PID(`{{.PID}}`) 및 실행 사용자(`{{.Username}}`)** 정보를 모두 포함하여 수집합니다.
* **용도**: 개발/테스트 환경이나 단일 장비 디버깅용
* **주의**: 프로세스가 재시작되거나 새로운 PID가 생성될 때마다 매번 새로운 메트릭 시계열(Time-series)이 만들어집니다. 프로세스 교체가 빈번한 운영 서버에서는 메트릭이 폭증하여 모니터링 서버(Prometheus)가 뻗을 수 있습니다.

### 2. 그룹 수집 (Grouped) - 운영 권장
개별 PID를 수집 대상에서 제외하고, 실행 파일명(`{{.Comm}}`) 단위로만 그룹화하여 합산 수집합니다.
* **용도**: **대규모 운영 서버** 및 컨테이너 환경
* **장점**: 동일한 프로세스가 재기동되거나 여러 개 실행되더라도 메트릭이 파일명 단위로 묶여 고정되므로, 메트릭 폭증(Cardinality Explosion) 없이 안전하게 운영할 수 있습니다.

**경량 설정 예시 (`config.yml`):**
```yaml
process_names:
  - name: "{{.Comm}}"  # PID와 Username을 빼서 실행파일명으로 그룹화
    cmdline:
    - '.+'
```

---
* 상세 설정법은 [Process Exporter GitHub](https://github.com/ncabatoff/process-exporter)을 참고하세요.
