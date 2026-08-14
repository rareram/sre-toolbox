# Customize Grafana

<p align="left">
  <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/custom_login/custom_login.png" alt="Grafana Custom Login Preview" width="40%" />
</p>

### 실행 방법

root 권한(sudo)으로 실행합니다.

```bash
sudo bash customize_grafana_*.sh
```

### 주의 사항 및 라이선스

- **라이선스 및 활용 범위**: Grafana OSS(AGPLv3) 환경에서 사내 내부 모니터링 목적으로 정적 파일(JS 번들, 이미지)이나 문구를 수정하여 사용하는 것은 라이선스 위반이 아닙니다.
- **적용 방식 및 업데이트**: Grafana Enterprise와 달리 OSS 버전은 별도의 브랜딩/테마 커스텀 기능을 지원하지 않습니다. 본 스크립트는 정적 파일을 직접 교체하므로, **Grafana 업데이트 시 기본 파일로 초기화되므로 스크립트를 다시 실행해야 합니다.**
- **자산 저작권**: 스크립트를 통해 적용하는 개별 배경 이미지, 로고, 문구 등 커스텀 자산의 저작권 준수 및 관리 책임은 스크립트 실행자(사용자)에게 있습니다.

### 주요 기능

- **운영 장애 방지 안전망**: 스크립트 실행 단계별 오류 검증 및 파일 교체 전 복구용 원본 이미지 자동 백업
- **환경 및 권한 즉시 검증**: sudo 권한 및 Grafana 설치 여부(systemctl / which) 이중 검증
- **로그인 문구 맞춤 설정**: "Integrated Monitoring", "E2E Observability" 또는 사용자 직접 입력 지원
- **시각적 프로세스 로깅**: 작업 상태 및 예외 상황을 색상별 구분 로그로 명확히 표시
- **서비스 재시작 및 상태 확인**: 설정 변경 후 Grafana 데몬 재시작 및 헬스 체크

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
