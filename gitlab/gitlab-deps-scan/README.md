# GitLab 프로젝트 의존성 라이브러리 스캐너 (`gitlab-deps-scan`)

GitLab API를 통해 전체 레포지토리의 매니페스트 및 빌드 설정 파일들을 스캔하여, 프로젝트별로 사용 중인 외부 라이브러리와 버전 정보를 추출 및 집계(EOS 및 보안 조사용)하는 유틸리티입니다.

---

## 주요 지원 언어 및 스캔 대상 매니페스트

- **.NET / C#**: `.csproj`, `Directory.Build.props`, `packages.config`
- **C / C++**: `vcpkg.json`, `conanfile.txt`, `CMakeLists.txt`
- **Java / Kotlin / Scala (JVM)**:
  - Maven: `pom.xml`
  - Gradle: `build.gradle`, `build.gradle.kts`
  - SBT: `build.sbt`

---

## 환경 설정 및 실행 방법

### 1. 의존성 패키지 설치
```bash
uv sync
```
*(또는 `pip install -r requirements.txt`)*

### 2. 환경 변수 설정
`.env.example`을 복사하여 `.env` 생성 후 GitLab 접속 및 스캔 대상을 설정합니다.

```bash
cp .env.example .env
```

`.env` 설정 예시:
```ini
GITLAB_URL=https://your-gitlab-domain.com
GITLAB_TOKEN=your_private_token
GITLAB_NAMESPACE_PREFIX=your_group_name  # 선택 사항: 특정 그룹/네임스페이스 하위만 스캔 시 지정
```

### 3. 스캐너 실행
```bash
python scan_deps.py
```

---

## 출력 결과물 (`deps_inventory.tsv`)

스캔이 완료되면 실행 경로에 `deps_inventory.tsv` (TAB 구분 파일)가 생성됩니다.
- **주요 포함 정보**: Project Path, File Path, Ecosystem Type(Maven, NuGet 등), Dependency Name, Version
- 추출된 TSV 목록을 활용하여 사용 라이브러리의 EOS(End of Support) 및 보안 취약점 상태를 진단할 수 있습니다.

---

## 라이선스
MIT License
