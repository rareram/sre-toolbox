# GitLab 커밋 유저 메타데이터 수집 및 정규화 도구 (`getinfo`)

GitLab API를 통해 전체 레포지토리 목록, 레포별 커밋 기여자, 계정 메타데이터를 수집하고, 사번/이메일/별명 등 다양하게 파편화된 커밋 작성자 정보를 식별 및 정규화(Mapping)하는 데이터 파이프라인 유틸리티입니다.

---

## 파이프라인 프로세스 및 실행 순서

수집 및 정규화 작업은 단계별 스크립트를 통해 순차적으로 진행되며, 각 단계 결과는 CSV 파일로 저장됩니다.

1. **전체 레포지토리 목록 추출 (`1.get_all_repolist.py`)**
   - GitLab 그룹 내 접근 가능한 전체 프로젝트 및 레포지토리 메타데이터 추출 (`gitlab_repolist.csv`)

2. **레포지토리별 커밋 작성자 추출 (`2.get_all_repo2user.py`)**
   - 각 레포지토리별 커밋 이력을 스캔하여 기여자 목록 추출 (`gitlab_repo2user.csv`)

3. **GitLab 사용자 계정 정보 추출 (`3.get_all_userinfo.py`)**
   - GitLab에 등록된 사용자 계정 메타데이터 추출 (`gitlab_userinfo.csv`)

4. **수집 데이터 일괄 병합 (`4.merge_all_csv.py`)**
   - 프로젝트, 커밋 기여자, 계정 정보를 통합 (`gitlab_merged_info.csv`)

5. **커밋 사용자 식별 정규화 및 매핑 (`5.user_mapping_rule.py` / `5.user_mapping_regex.py`)**
   - 파편화된 커밋 사용자 정보(사번, 이메일, Domain\ID, 한글/영문명 등)에 매핑 규칙 및 정규식을 적용하여 최종 정규화 데이터 생성 (`gitlab_mapped_data.csv`)

---

## 환경 설정 및 사용법

### 1. 환경 변수 설정
`.env` 파일 생성 후 GitLab 호스트 주소 및 API 토큰 설정:

```ini
GITLAB_HOST=https://your-gitlab-domain.com
GITLAB_TOKEN=your_private_token
```

### 2. 매핑 템플릿 생성 및 규칙 적용

```bash
# 1) 매핑 템플릿 생성
python 5.user_mapping_rule.py --create-template

# 2) 생성된 commit_user_mapping.csv 파일 수정 후 매핑 실행
python 5.user_mapping_rule.py
```

---

## 주요 지원 정규화 패턴

- **이메일 주소 전용**: `user@example.com`
- **사번/계정 ID 전용**: `sksdu_1234`
- **도메인\계정 형식**: `COMPANY\sksdu_3243`
- **단일 이름 형식**: 한글 이름(`홍길동`), 영문 이름(`John Doe`)
- **엑셀 매크로 지원**: Excel 환경 사용자를 위한 정규식 추출 코드(`keyword_extraction.vb`) 제공

---

## 라이선스
MIT License