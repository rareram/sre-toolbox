# Linux 시스템 점검 결과 Excel 보고서 자동 생성기 (`syschk2xls`)

리눅스 서버(RedHat/Debian 계열)의 디스크 용량, 마운트 상태, 파일시스템 사용률, 프로세스 등 주요 점검 항목 명령어를 실행하고, 그 결과를 서식화된 Excel 보고서(`.xlsx`)로 자동 출력해 주는 유틸리티입니다.

---

## 주요 기능 및 특징

1. **점검 명령어 커스텀 구성 (`template_command.conf`)**:
   - 디스크 용량(`df -PThl`), 마운트 정보, Inode 사용률 등 시스템 진단 명령어를 자유롭게 정의
2. **OS 배포판 자동 감지**:
   - RedHat/CentOS 및 Debian/Ubuntu 계열 배포판 감지 지원
3. **서식화된 Excel 보고서 생성**:
   - `openpyxl` 및 `xlsxwriter`를 기반으로 IT 구성 항목별 진단 결과를 지정된 스타일 서식에 맞게 Excel 파일로 자동 저장

---

## 주요 구성 파일

- `syschk2xls.py`: 점검 명령어 실행 및 Excel 보고서 생성 메인 스크립트
- `template_command.conf`: 점검 시 실행할 쉘 명령어 정의 파일
- `template_styles.conf`: Excel 셀 포맷 및 스타일 설정 파일
- `requirements.txt`: 의존성 라이브러리 목록 (`xlsxwriter`, `openpyxl`)

---

## 환경 설정 및 실행 방법

### 1. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 점검 명령어 설정 (`template_command.conf`)
점검할 시스템 쉘 명령어를 정의하거나 수정합니다.

```ini
# 마운트 및 디스크 용량 점검
MOUNT=mount|egrep -iw "ext4|ext3|xfs|gfs|gfs2|btrfs"|grep -v "loop"|sort -u -t' ' -k1,2
FS_USAGE=df -PThl -x tmpfs -x iso9660 -x devtmpfs -x squashfs|awk '!seen[$1]++'|sort -k6n|tail -n +2
IUSAGE=df -iPThl -x tmpfs -x iso9660 -x devtmpfs -x squashfs|awk '!seen[$1]++'|sort -k6n|tail -n +2
```

### 3. 스크립트 실행
```bash
python syschk2xls.py
```
*(참고: 하드웨어/시스템 커널 정보 수집 시 sudo 권한이 필요할 수 있습니다.)*

---

## 라이선스
MIT License
