# Jira 이슈 익스포터

이 스크립트는 Jira 프로젝트의 이슈를 가져와 CSV 파일로 내보냅니다.

## 사용 방법

1.  **의존성 설치:**
    `uv`를 사용하여 필요한 패키지를 설치합니다.
    ```bash
    uv add python-dotenv requests
    ```

2.  **환경 파일 생성:**
    루트 디렉토리에 `.env` 파일을 만들고 Jira 기본 URL과 API 토큰을 추가합니다. `.env.example` 파일을 템플릿으로 사용할 수 있습니다.

    ```
    JIRA_BASE_URL=https://your-domain.atlassian.net
    JIRA_API_TOKEN=your-api-token
    ```
    > **참고:** API 토큰은 [여기](https://id.atlassian.com/manage-profile/security/api-tokens)에서 생성할 수 있습니다.

3.  **검색 조건 설정 (선택 사항):**
    `jira_issues_export.py` 파일을 열고 `======== 조회 조건 설정 ========` 섹션 아래의 변수를 수정하여 내보낼 이슈를 필터링합니다.

    - `PROJECT_KEY`: Jira 프로젝트의 키 (예: "AFC").
    - `ISSUE_TYPES`: 포함할 이슈 유형 목록 (예: `["버그", "개선"]`).
    - `STATUSES`: 포함할 상태 목록. 비워두면(`[]`) 모든 상태를 포함합니다.
    - `CREATED_FROM` / `CREATED_TO`: 이슈가 생성된 날짜 범위 (YYYY-MM-DD).
    - `OUTPUT_CSV`: 출력 CSV 파일의 이름.

4.  **스크립트 실행:**
    ```bash
    uv run python jira_issues_export.py
    ```

5.  **출력 확인:**
    스크립트가 실행되면 루트 디렉토리에 내보낸 이슈가 포함된 CSV 파일(예: `jira_issues_export.csv`)이 생성됩니다.