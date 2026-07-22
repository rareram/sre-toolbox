# SVG Converter & Compositor

여러 이미지 파일(PNG, JPG, SVG, WebP)을 캔버스 상에 배치 및 합성하여 단일 SVG 파일로 변환하는 데스크톱 GUI 애플리케이션입니다.

Grafana 로그인 화면 배경(`g8_login_dark.svg` 등) 제작 시 규격에 맞게 로고와 데코 이미지를 정밀하게 배치하여 하나의 SVG 파일로 내보낼 때 사용합니다.

---

## 1. 주요 기능

* **캔버스 해상도 설정**: FHD(1920x1080, Grafana 권장), 2K, 4K 및 커스텀 해상도 지원
* **레이어 편집 및 순서 조절**:
  * 배경 이미지 및 오버레이 레이어 추가
  * 마우스 드래그 및 방향키(1px / Shift+방향키 10px)를 이용한 위치 이동
  * 리사이즈 핸들 조절 (Shift 키 또는 옵션 체크로 가로세로 비율 고정)
  * 레이어 목록 드래그앤드롭을 통한 겹침 순서(Z-Index) 조정
* **정렬 및 속성 편집**: 상/하/좌/우/중앙 정렬 버튼 및 X, Y, W, H 수치 직접 입력
* **SVG 변환**: 이미지 레이어들을 Base64 Data URI로 결합하여 단일 SVG 코드로 생성 및 내보내기

---

## 2. 파일 구조

* [main.py](file:///Users/paul/sandbox/sre-toolbox/grafana/svg-gen/main.py): 메인 윈도우 인터페이스 및 UI 조립
* [editor.py](file:///Users/paul/sandbox/sre-toolbox/grafana/svg-gen/editor.py): 캔버스(`EditorCanvas`) 및 레이어 아이템(`ImageLayerItem`) 조작 구현
* [exporter.py](file:///Users/paul/sandbox/sre-toolbox/grafana/svg-gen/exporter.py): 레이어 정보를 취합하여 SVG 파일로 직렬화하는 내보내기 로직
* [pyproject.toml](file:///Users/paul/sandbox/sre-toolbox/grafana/svg-gen/pyproject.toml): 프로젝트 설정 및 의존성 정의

---

## 3. 실행 방법 (How to Run)

`uv`를 통한 실행을 권장합니다.

```bash
# uv로 실행 (의존성 자동 관리 및 실행)
uv run main.py
```

<details>
<summary>기본 python 가상환경 사용 시</summary>

```bash
# 의존성 설치 후 실행
pip install -r requirements.txt
python main.py
```
</details>
