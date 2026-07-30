# 윈도우 프로메테우스 에이전트 설치 유틸리티 (`win_exp_inst`)

Windows 서버 환경에서 Prometheus windows_exporter 모니터링 에이전트를 GUI 화면을 통해 설치/제거하고 Windows 시스템 서비스로 등록·관리할 수 있는 유틸리티입니다.

---

## 주요 기능 및 특징

1. **GUI 기반 설치/제거 지원**:
   - Tkinter 기반 사용자 인터페이스 제공으로 윈도우 환경에서 설치 옵션 선택 및 관리
2. **Windows 시스템 서비스 자동 등록**:
   - 서버 재부팅 시에도 모니터링이 자동 재개되도록 Windows Service로 등록 처리
3. **단일 실행 파일(.exe) 빌드 지원**:
   - PyInstaller를 사용하여 타겟 서버에 별도 Python 환경 구축 없이 독립 실행 가능한 `.exe` 바이너리로 컴파일 가능

---

## 환경 설정 및 PyInstaller 빌드 방법

### 1. 패키지 설치
```cmd
pip install -r requirements.txt
```

### 2. 단일 실행 파일(`.exe`) 빌드
```cmd
pip install pyinstaller
pyinstaller -F --noconsole --add-data "github_icon.png;." --add-data "logo.png;." --add-data "web_icon.png;." win_exp_inst.py
```
- 빌드 완료 시 `dist/win_exp_inst.exe` 실행 파일 생성

---

## 주요 의존성 패키지 보안 패치 현황

- `urllib3` (2.7.0): 다운로드 시 Decompression Bomb 및 리다이렉트 보안 취약점 패치
- `setuptools` (83.0.0): 경로 조작으로 인한 임시 파일 덮어쓰기 방지
- `requests` (2.33.0): 파싱 오류로 인한 자격 증명 유출 방지
- `idna` (3.15): 특수 문자 처리 시 CPU 고점 점유 이슈 해결

---

## 라이선스
MIT License
