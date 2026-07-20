import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# .env: JIRA_BASE_URL, JIRA_API_TOKEN
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# 수집 대상 설정
# PROJECTS = ["AFC", "AFF", "AFO", "TSC"]
PROJECTS = ["TSC"]
# ISSUE_TYPES = ["버그", "작업", "큰틀"]  # SE 등록 타입 전수 수집
ISSUE_TYPES = ["버그"]  # SE 등록 타입 전수 수집
CREATED_FROM = "2020-01-01"
OUTPUT_CSV = f"지라_스냅샷_{datetime.now().strftime('%Y%m%d')}.csv"

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Authorization": f"Bearer {JIRA_API_TOKEN}"
})

def fetch_issues():
    proj_str = ", ".join(f'"{p}"' for p in PROJECTS)
    type_str = ", ".join(f'"{t}"' for t in ISSUE_TYPES)
    jql = f'project in ({proj_str}) AND issuetype in ({type_str}) AND created >= "{CREATED_FROM}"'
    
    issues = []
    start_at = 0
    max_results = 50

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 수집 시작: {jql}")

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,issuetype,status,created,resolutiondate,priority,description,comment"
        }
        url = f"{JIRA_BASE_URL}/rest/api/2/search"
        resp = session.get(url, params=params)
        if resp.status_code != 200: break

        data = resp.json()
        fetched = data.get("issues", [])
        if not fetched: break

        for issue in fetched:
            f = issue.get("fields", {})
            issues.append({
                "IssueKey": issue.get("key"),
                "Project": issue.get("key").split("-")[0],
                "Summary": f.get("summary", ""),
                "IssueType": (f.get("issuetype") or {}).get("name", ""),
                "Status": (f.get("status") or {}).get("name", ""),
                "Created": f.get("created", ""),
                "Resolved": f.get("resolutiondate", ""),
                "Priority": (f.get("priority") or {}).get("name", ""),
                "Description": f.get("description", ""),
                "Comments": str(f.get("comment", {}).get("comments", ""))
            })
        
        start_at += max_results
        if start_at >= data.get("total", 0): break
        print(f"진행: {len(issues)} / {data.get('total')}")

    pd.DataFrame(issues).to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {OUTPUT_CSV}")

if __name__ == "__main__":
    fetch_issues()
