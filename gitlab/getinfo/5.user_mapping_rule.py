import pandas as pd
import csv
import os
import sys

# 파일 경로 설정
INTEGRATED_DATA = "gitlab_integrated_data.csv"  # 통합된 데이터
MAPPING_RULES = "commit_user_mapping.csv"       # 매핑 룰 파일
OUTPUT_FILE = "gitlab_mapped_data.csv"          # 매핑 적용된 출력 파일

def load_mapping_rules():
    """매핑 룰 파일을 로드합니다. 없으면 샘플을 생성합니다."""
    if not os.path.exists(MAPPING_RULES):
        print(f"⚠️ 매핑 룰 파일이 없습니다: {MAPPING_RULES}")
        create_sample_mapping_file()
        print(f"✅ 샘플 매핑 파일 생성됨: {MAPPING_RULES}")
        print("⚠️ 매핑 룰 파일을 편집한 후 스크립트를 다시 실행하세요.")
        return None
    
    try:
        mapping = {}
        with open(MAPPING_RULES, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)  # 헤더 건너뛰기
            
            for row in reader:
                if len(row) >= 2:
                    as_is = row[0].strip()
                    to_be = row[1].strip()
                    if as_is and to_be:
                        mapping[as_is] = to_be
        
        print(f"✅ 매핑 룰 {len(mapping)}개 로드 완료")
        return mapping
    except Exception as e:
        print(f"❌ 매핑 룰 파일 로드 실패: {e}")
        return None

def create_sample_mapping_file():
    """샘플 매핑 룰 파일을 생성합니다."""
    try:
        with open(MAPPING_RULES, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["AS-IS", "TO-BE", "비고"])
            writer.writerow(["홍길동A", "홍길동(emp_2832)", "예시 - ID가 다른 경우"])
            writer.writerow(["emp_3779", "김철수(emp_3779)", "예시 - 이름 누락"])
            writer.writerow(["COMPANY\\emp_1234", "이영희(emp_1234)", "예시 - 도메인 포함"])
            writer.writerow(["test@example.com", "박지훈(emp_4567)", "예시 - 이메일만 있는 경우"])
        return True
    except Exception as e:
        print(f"❌ 샘플 매핑 파일 생성 실패: {e}")
        return False

def extract_unique_commit_users(df):
    """통합 데이터에서 고유한 커밋 사용자 목록을 추출합니다."""
    commit_users = set()
    commit_cols = [col for col in df.columns if col.startswith('commit_user')]
    
    for _, row in df.iterrows():
        for col in commit_cols:
            user = row.get(col)
            if user and isinstance(user, str) and user.strip():
                commit_users.add(user.strip())
    
    return sorted(list(commit_users))

def create_mapping_template(df):
    """기존 커밋 사용자를 기반으로 매핑 템플릿을 생성합니다."""
    commit_users = extract_unique_commit_users(df)
    template_file = "commit_user_template.csv"
    
    try:
        with open(template_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["AS-IS", "TO-BE", "비고"])
            
            for user in commit_users:
                writer.writerow([user, "", ""])
        
        print(f"✅ 매핑 템플릿 생성 완료: {template_file}")
        print(f"📝 총 {len(commit_users)}개의 고유 커밋 사용자가 템플릿에 추가됨")
        return True
    except Exception as e:
        print(f"❌ 매핑 템플릿 생성 실패: {e}")
        return False

def apply_mapping_rules():
    """매핑 룰을 적용하여 커밋 사용자 정보를 변환합니다."""
    print("🚀 커밋 사용자 매핑 시작...")
    
    # 1. 데이터 로드
    try:
        df = pd.read_csv(INTEGRATED_DATA)
        print(f"✅ 통합 데이터 로드 완료: {len(df)}개 레코드")
    except Exception as e:
        print(f"❌ 통합 데이터 로드 실패: {e}")
        return False
    
    # 2. 매핑 룰 로드
    mapping_rules = load_mapping_rules()
    if mapping_rules is None:
        return False
    
    # 3. 템플릿 생성 모드 확인
    if "--create-template" in sys.argv:
        return create_mapping_template(df)
    
    # 4. 매핑 적용
    commit_user_cols = [col for col in df.columns if col.startswith('commit_user')]
    mapped_count = 0
    total_count = 0
    
    # 새 컬럼 추가 (매핑된 사용자 정보)
    for i, col in enumerate(commit_user_cols, 1):
        df[f'mapped_user{i}'] = df[col]
    
    # 매핑 적용
    for idx, row in df.iterrows():
        for i, col in enumerate(commit_user_cols, 1):
            user = row.get(col)
            if user and isinstance(user, str) and user.strip():
                total_count += 1
                
                user = user.strip()
                if user in mapping_rules:
                    df.at[idx, f'mapped_user{i}'] = mapping_rules[user]
                    mapped_count += 1
    
    # 5. 결과 저장
    try:
        # NaN 값을 빈 문자열로 대체
        df = df.fillna("")
        
        # CSV 저장
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        
        # 매핑 통계
        mapped_percent = (mapped_count / total_count * 100) if total_count > 0 else 0
        print(f"\n📊 매핑 통계:")
        print(f"  - 총 커밋 사용자: {total_count}개")
        print(f"  - 매핑 적용: {mapped_count}개 ({mapped_percent:.2f}%)")
        print(f"  - 매핑 미적용: {total_count - mapped_count}개 ({100 - mapped_percent:.2f}%)")
        
        print(f"\n✅ 매핑 적용된 데이터 저장 완료: {OUTPUT_FILE}")
        
        # 매핑 미적용 사용자 확인
        if mapped_count < total_count:
            print("\n⚠️ 매핑되지 않은 커밋 사용자가 있습니다.")
            print("  매핑 템플릿을 생성하려면 --create-template 옵션을 사용하세요.")
        
        return True
    except Exception as e:
        print(f"❌ 매핑 적용 실패: {e}")
        return False

if __name__ == "__main__":
    apply_mapping_rules()
