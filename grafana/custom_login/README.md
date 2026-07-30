# Customize Grafana

### 주의 사항 및 라이선스

- **라이선스 및 활용 범위**: Grafana OSS(AGPLv3) 환경에서 사내 내부 모니터링 목적으로 정적 파일(JS 번들, 이미지)이나 문구를 수정하여 사용하는 것은 라이선스 위반이 아닙니다.
- **적용 방식 및 업데이트**: Grafana Enterprise와 달리 OSS 버전은 별도의 브랜딩/테마 커스텀 기능을 지원하지 않습니다. 본 스크립트는 정적 자산을 직접 치환하므로, **Grafana 버전 업데이트 시 파일이 원복되어 스크립트 재적용이 필요합니다.**
- **자산 저작권**: 스크립트를 통해 적용하는 개별 배경 이미지, 로고, 문구 등 커스텀 자산의 저작권 준수 및 관리 책임은 스크립트 실행자(사용자)에게 있습니다.

### 주요 기능

- sudo 권한 체크: 스크립트 실행 시 즉시 확인
- Grafana 설치 확인: systemctl과 which 명령어로 이중 확인
- 원본 이미지 백업: 사용자 선택에 따라 백업 생성
- 로그인 문구 선택: "Integrated Monitoring", "E2E Observability" 또는 사용자 직접 입력
- 안전한 파일 교체: 각 단계별 오류 대응
- 로그 종류 표시: 색상별 로그 메시지
- 서비스 재시작: 설정 변경 후 프로세스 재시작 및 상태 확인

### 폴더 구조

```
custom_login/
├── customize_grafana_v0.7.sh
├── README.md
└── img/
    ├── default/
    │   ├── fav32.png
    │   ├── g8_login_dark.svg
    │   ├── g8_login_light.svg
    │   └── grafana_icon.svg
    ├── Hack/
    │   └── ...
    └── Serene/
        └── ...
```

### 출처

- 로그인 배경 샘플 이미지: [Pexels](https://www.pexels.com/search/background/)
