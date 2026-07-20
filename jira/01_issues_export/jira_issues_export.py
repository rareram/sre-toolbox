import os
import csv
import requests
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# ======== 조회 조건 설정 ========
# PROJECT_KEY = "TSC"
PROJECT_KEY = "AFF"
ISSUE_TYPES = ["버그", "개선"]
# STATUSES = ["Open", "In Progress", "Done"]
STATUSES = []

CREATED_FROM = "2024-01-01"
CREATED_TO = "2026-03-31"

OUTPUT_CSV = "jira_issues_export.csv"
# =================================

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Authorization": f"Bearer {JIRA_API_TOKEN}"
})

def build_jql():
    parts = []
    parts.append(f'project = "{PROJECT_KEY}"')

    if ISSUE_TYPES:
        types_str = ", ".join(f'"{t}"' for t in ISSUE_TYPES)
        parts.append(f'issuetype in ({types_str})')

    if STATUSES:
        status_str = ", ".join(f'"{s}"' for s in STATUSES)
        parts.append(f'status in ({status_str})')

    if CREATED_FROM and CREATED_TO:
        parts.append(f'created >= "{CREATED_FROM}" AND created <= "{CREATED_TO}"')

    return " AND ".join(parts)

def fetch_issues(jql, max_results=100):
    issues = []
    start_at = 0

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,issuetype,status"
        }

        url = f"{JIRA_BASE_URL}/rest/api/2/search"
        resp = session.get(url, params=params)

        if resp.status_code != 200:
            print("ERROR:", resp.status_code, resp.text)
            return issues

        data = resp.json()
        fetched = data.get("issues", [])
        total = data.get("total", 0)

        issues.extend(fetched)
        print(f"Fetched {len(issues)} / {total}")

        if start_at + max_results >= total:
            break
        start_at += max_results

    return issues

def export_to_csv(issues, filepath):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["IssueKey", "Summary", "IssueType", "Status"])

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "")
            issue_type = (fields.get("issuetype") or {}).get("name", "")
            status = (fields.get("status") or {}).get("name", "")

            writer.writerow([key, summary, issue_type, status])

    print(f"CSV saved to: {filepath}")

def main():
    jql = build_jql()
    print("JQL:", jql)

    issues = fetch_issues(jql)
    print(f"Total issues fetched: {len(issues)}")

    export_to_csv(issues, OUTPUT_CSV)

if __name__ == "__main__":
    main()

