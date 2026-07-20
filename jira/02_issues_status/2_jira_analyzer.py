import os
import re
import pandas as pd
from datetime import datetime, timedelta

def extract_date_from_filename(filename):
    match = re.search(r'\d{8}', filename)
    return datetime.strptime(match.group(), '%Y%m%d') if match else datetime.now()

def select_csv_file():
    files = sorted([f for f in os.listdir('.') if f.endswith('.csv') and '리포트_요약' not in f], reverse=True)
    if not files: return None
    print("\n--- [분석 대상 파일 선택] ---")
    for i, f in enumerate(files, 1):
        print(f"  [{i}] {f}")
    return files[int(input("\n번호 선택 > "))-1]

def analyze_and_enrich(csv_file):
    ref_date = extract_date_from_filename(csv_file)
    print(f"\n기준일: {ref_date.strftime('%Y-%m-%d')} | 분석 중...")
    
    df = pd.read_csv(csv_file)
    one_week_ago = ref_date - timedelta(days=7)

    # 날짜 정제
    df['Created'] = pd.to_datetime(df['Created']).dt.tz_localize(None)
    df['Resolved'] = pd.to_datetime(df['Resolved']).dt.tz_localize(None)

    # [핵심] 정교한 업무 분류 로직
    def categorize_detail(row):
        summary = str(row.get('Summary', ''))
        i_type = str(row.get('IssueType', ''))
        
        if i_type == "버그":
            if any(x in summary for x in ["[이슈]", "이슈 |"]): return "버그(진짜)"
            if any(x in summary for x in ["[개발요청]", "[개선]"]): return "개발/개선"
            return "버그(미분류)"
        elif i_type == "작업": return "지원작업(SE)"
        elif i_type == "큰틀": return "기획/관리"
        return "기타"

    df['상세구분'] = df.apply(categorize_detail, axis=1)

    # 지표 마킹
    done_list = ["해결됨", "종료됨", "Closed", "Resolved", "Done"]
    df['완료여부'] = df['Status'].apply(lambda x: '완료' if str(x) in done_list else '미결')
    df['신규(7d)'] = df['Created'].apply(lambda x: 'O' if one_week_ago <= x <= ref_date else '')
    df['완료(7d)'] = df.apply(lambda r: 'O' if (r['완료여부'] == '완료' and not pd.isna(r['Resolved']) and one_week_ago <= r['Resolved'] <= ref_date) else '', axis=1)
    df['방치(>30d)'] = df.apply(lambda r: 'O' if (r['완료여부'] == '미결' and (ref_date - r['Created']).days > 30) else '', axis=1)
    df['긴급(Crit)'] = df['Priority'].apply(lambda x: 'O' if str(x) in ["Highest", "Critical", "긴급", "최우선"] else '')

    # 통계 요약
    stats = df.groupby(['Project', '상세구분']).agg(
        전체=('IssueKey', 'count'),
        해결=('완료여부', lambda x: (x == '완료').sum()),
        신규_7d=('신규(7d)', lambda x: (x == 'O').sum()),
        완료_7d=('완료(7d)', lambda x: (x == 'O').sum()),
        긴급_Crit=('긴급(Crit)', lambda x: (x == 'O').sum()),
        방치_30d=('방치(>30d)', lambda x: (x == 'O').sum())
    ).reset_index()

    stats['미결'] = stats['전체'] - stats['해결']
    stats['해결률'] = (stats['해결'] / stats['전체'] * 100).round(1).astype(str) + '%'

    # 출력 및 저장
    print("\n" + "="*105)
    print(f"{'제품':<8} | {'상세구분':<12} | {'전체':>5} | {'해결':>5} | {'미결':>5} | {'신규(7d)':>6} | {'완료(7d)':>6} | {'긴급':>4} | {'방치':>5} | {'해결률':>6}")
    print("-" * 105)
    for _, r in stats.iterrows():
        print(f"{r['Project']:<8} | {r['상세구분']:<12} | {r['전체']:>7} | {r['해결']:>7} | {r['미결']:>7} | {r['신규_7d']:>10} | {r['완료_7d']:>10} | {r['긴급_Crit']:>6} | {r['방치_30d']:>7} | {r['해결률']:>8}")
    
    # 파일 저장 (원본 업데이트 + 요약 생성)
    summary_file = f"리포트_요약_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    stats.to_csv(summary_file, index=False, encoding="utf-8-sig")
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"\n[완료] 원본 파일 컬럼 업데이트 및 요약 리포트({summary_file}) 생성 완료")

if __name__ == "__main__":
    selected = select_csv_file()
    if selected: analyze_and_enrich(selected)
