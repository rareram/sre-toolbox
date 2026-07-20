# SVG Converter & Compositor (SVG 변환 및 합성 에디터)

이 프로그램은 여러 이미지 파일(PNG, JPG, SVG, WebP)을 시각적인 캔버스 위에 자유롭게 배치 및 합성하고, 이를 고품질 단일 SVG 파일로 변환하여 출력하는 데스크톱 GUI 애플리케이션입니다.

Grafana 로그인 화면 배경(`g8_login_dark.svg` 등)을 제작할 때, 가이드라인에 맞춘 해상도(FHD)로 회사 로고와 디자인 데코 이미지를 자유롭게 얹고 정밀하게 조정하여 최종 단일 SVG를 완성하는 용도로 매우 유용합니다.

---

## 1. 주요 기능 및 UI 레이아웃

* **캔버스 해상도 조절 (좌측 패널)**:
  * 원본 크기, 4K, 2K, FHD(1920x1080, Grafana 권장), 사용자 정의(Custom) 크기 중 선택 가능합니다.
  * FHD 선택 시 Grafana 로그인 화면 권장 크기 가이드가 활성화됩니다.
* **레이어 조작 및 Z-Index 정렬 (좌측 패널 & 중앙 캔버스)**:
  * `배경 이미지 설정`을 통해 캔버스 꽉 차게 고정되는 바닥 이미지를 지정할 수 있습니다.
  * `오버레이 이미지 추가`로 로고나 장식용 이미지를 얹고, 8방향 모서리 조절점을 드래그하여 비율에 맞춰 확대/축소하거나 마우스 드래그로 자유롭게 이동시킵니다.
  * 좌측의 레이어 목록에서 이미지들을 위아래로 드래그앤드롭하여 겹침 순서(Z-Index)를 직관적으로 조정할 수 있습니다.
* **정밀 편집 및 캔버스 정렬 (우측 패널)**:
  * 마우스 움직임 외에도 X, Y 좌표 및 W, H 크기 스핀박스에 직접 숫자를 입력하여 픽셀 단위로 정밀하게 튜닝할 수 있습니다.
  * 상/하/좌/우/수평중앙/수직중앙 정렬 버튼을 지원하여 간편하게 로고를 화면 정중앙에 수평 정렬시킬 수 있습니다.
* **Base64 무손실 SVG 변환 (우측 패널 & 상단 툴바)**:
  * 캔버스 위에 얹어진 비트맵 파일들을 고화질 Base64 Data URI 데이터로 결합하여 하나의 완벽하게 빌드된 단일 SVG 코드로 생성 및 내보내기합니다.

---

## 2. 파일 구조 설명

* [main.py](file:///home/paul/sandbox/ark-mgmt/grafana/svg-gen/main.py): 프리미엄 다크테마 스타일(QSS)이 내장된 메인 윈도우 인터페이스 및 각 패널 위젯 조립, 이벤트 연동 엔트리 포인트
* [editor.py](file:///home/paul/sandbox/ark-mgmt/grafana/svg-gen/editor.py): 8방향 조작 핸들 및 호버 커서 감지가 들어있는 커스텀 피스 `ImageLayerItem`과 시각 캔버스 `EditorCanvas` 구현
* [exporter.py](file:///home/paul/sandbox/ark-mgmt/grafana/svg-gen/exporter.py): 각 레이어 정보를 취합하여 MIME 타입 매핑 및 Base64 변환을 거쳐 XML 형식의 SVG 파일로 직렬화하는 백엔드 빌더
* [requirements.txt](file:///home/paul/sandbox/ark-mgmt/grafana/svg-gen/requirements.txt): 실행에 필요한 외부 종속 패키지 리스트

---

## 3. 실행 방법 (How to Run)

터미널에서 아래 명령을 차례대로 수행하여 가상환경을 활성화하고 실행하실 수 있습니다.

```bash
# 1. 프로그램 디렉토리로 이동
cd ~/sandbox/ark-mgmt/grafana/svg-gen

# 2. 가상환경 활성화 (이미 venv 폴더가 빌드 완료되었습니다)
source venv/bin/activate

# 3. 의존성 설치 (필요시 최초 1회)
pip install -r requirements.txt

# 4. 에디터 프로그램 실행
python main.py
```
