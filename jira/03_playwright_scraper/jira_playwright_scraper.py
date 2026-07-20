#!/usr/bin/env python3
"""
Jira Web Scraper using Playwright
로그인해서 Jira 이슈 데이터를 자동으로 수집
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import stealth

# .env 로드
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

# 설정
JIRA_URL = os.getenv("JIRA_URL", "https://lab.idatabank.com/jira")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")

# 세션 저장 경로
SESSION_DIR = os.path.join(current_dir, ".sessions")

# 출력 경로 설정
PROJECT_ROOT = os.path.abspath(os.path.join(current_dir, "..", ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "issues")

async def scrape_issue(issue_key, headless=True):
    if not JIRA_USERNAME or not JIRA_PASSWORD:
        print("에러: JIRA_USERNAME 또는 JIRA_PASSWORD가 .env 파일에 설정되지 않았습니다.")
        return

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {issue_key} 수집 시작 (headless={headless})...")

    os.makedirs(SESSION_DIR, exist_ok=True)

    async with async_playwright() as p:
        # persistent_context를 사용하여 세션 유지 (로그인 상태 및 쿠키 저장)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # stealth 적용 (stealth 모듈 자체가 callable이 아닐 경우를 대비해 처리)
        try:
            if callable(stealth):
                await stealth(page)
            elif hasattr(stealth, 'stealth') and callable(stealth.stealth):
                await stealth.stealth(page)
        except Exception as e:
            print(f"Stealth 적용 중 경고 (무시 가능): {e}")

        # 1. 이슈 페이지 바로 접속 시도 (세션이 살아있으면 바로 보임)
        issue_url = f"{JIRA_URL}/browse/{issue_key}"
        await page.goto(issue_url)
        await page.wait_for_load_state("networkidle")

        # 로그인 페이지로 리다이렉트 되었는지 확인
        if "login.jsp" in page.url or await page.query_selector("#login-form-username"):
            print("로그인이 필요합니다. 로그인을 시도합니다...")
            await page.fill("#login-form-username", JIRA_USERNAME)
            await page.fill("#login-form-password", JIRA_PASSWORD)
            await page.click("#login-form-submit")
            await page.wait_for_load_state("networkidle")
            
            # 로그인 후 다시 이슈 페이지로 이동 (혹시 모르니)
            if issue_url not in page.url:
                await page.goto(issue_url)
                await page.wait_for_load_state("networkidle")

        # 캡챠 체크
        if await page.query_selector(".captcha-image") or "captcha" in await page.content():
            print("!!! 경고: 캡챠가 감지되었습니다 !!!")
            if headless:
                print("Headless 모드에서는 캡챠를 해결할 수 없습니다.")
                print("브라우저를 띄워 직접 로그인하려면 다음을 실행하세요:")
                print(f"uv run {os.path.join('03_playwright_scraper', 'jira_playwright_scraper.py')} {issue_key} --no-headless")
                await context.close()
                return
            else:
                print("브라우저에서 캡챠를 해결하고 로그인을 완료해주세요. (60초 대기 중...)")
                try:
                    # 사용자가 로그인할 때까지 대기 (이슈 요약 요소가 보일 때까지)
                    await page.wait_for_selector("#summary-val", timeout=60000)
                except:
                    print("대기 시간 초과.")
                    await context.close()
                    return

        # 2. 데이터 추출
        try:
            # 기본 정보가 로드될 때까지 대기
            await page.wait_for_selector("#summary-val", timeout=10000)

            # 브라우저 내에서 자바스크립트로 데이터 추출 (훨씬 빠르고 더 많은 정보를 가져옴)
            extracted_data = await page.evaluate("""() => {
                const getText = (sel) => document.querySelector(sel)?.innerText?.trim() || "";
                
                // 1. 기본 필드 수집
                const data = {
                    summary: getText('#summary-val'),
                    status: getText('#status-val'),
                    priority: getText('#priority-val'),
                    resolution: getText('#resolution-val'),
                    type: getText('#type-val'),
                    description: getText('#description-val'),
                    environment: getText('#environment-val'),
                    project: getText('#project-name-val'),
                };

                // 2. 모듈별 키-값 쌍 자동 수집 (커스텀 필드 등 포함)
                // Details, People, Dates 모듈 등을 순회
                const scrapModule = (moduleId) => {
                    const dict = {};
                    const container = document.querySelector(moduleId);
                    if (!container) return dict;
                    
                    // .item 요소들 찾기 (표준 Jira Server 구조)
                    container.querySelectorAll('.item').forEach(item => {
                        const nameElem = item.querySelector('.name');
                        const valElem = item.querySelector('.value');
                        if (nameElem && valElem) {
                            const key = nameElem.innerText.replace(':', '').trim();
                            const val = valElem.innerText.trim();
                            dict[key] = val;
                        }
                    });
                    return dict;
                };

                data.details = scrapModule('#details-module');
                data.people = scrapModule('#people-module');
                data.dates = scrapModule('#datesmodule');

                // 3. 리스트형 데이터 (Labels, Components, Versions)
                data.labels = Array.from(document.querySelectorAll('#wrap-labels .labels .lozenge, .labels-wrap .lozenge'))
                    .map(el => el.innerText.trim());
                
                // 4. 댓글 (Comments)
                data.comments = Array.from(document.querySelectorAll('.activity-comment')).map(comment => {
                    const author = comment.querySelector('.author')?.innerText?.trim() || "Unknown";
                    const time = comment.querySelector('time')?.getAttribute('datetime') || 
                                 comment.querySelector('time')?.innerText?.trim() || "";
                    const body = comment.querySelector('.action-body')?.innerText?.trim() || "";
                    return { author, time, body };
                });

                // 5. 연결된 이슈 (Linked Issues)
                const links = [];
                document.querySelectorAll('.issuelinks-link, .link-content a.issue-link').forEach(link => {
                    links.push({
                        text: link.innerText.trim(),
                        href: link.getAttribute('href'),
                        title: link.getAttribute('title')
                    });
                });
                data.links = links;

                // 6. 첨부파일 (Attachments)
                const attachments = [];
                document.querySelectorAll('#attachmentextensions .attachment-content, .attachments-table tr').forEach(row => {
                     const nameEl = row.querySelector('.attachment-title, .filename');
                     if(nameEl) {
                         attachments.push(nameEl.innerText.trim());
                     }
                });
                data.attachments = attachments;

                return data;
            }""")

            # 파이썬 레벨 메타데이터 합치기
            issue_data = {
                "issue_key": issue_key,
                "url": issue_url,
                "scraped_at": datetime.now().isoformat(),
                **extracted_data
            }

            # 3. 저장
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            filename = f"{datetime.now().strftime('%Y-%m-%d')}-{issue_key}-scraped.json"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(issue_data, f, ensure_ascii=False, indent=2)
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 저장 완료: {filepath}")

        except Exception as e:
            print(f"데이터 추출 중 에러 발생: {e}")
            await page.screenshot(path=f"error_{issue_key}.png")

        await context.close()

async def main():
    if len(sys.argv) < 2:
        print("사용법: uv run jira_playwright_scraper.py <ISSUE_KEY> [--no-headless]")
        sys.exit(1)
    
    issue_key = sys.argv[1]
    headless = "--no-headless" not in sys.argv
    
    await scrape_issue(issue_key, headless=headless)

if __name__ == "__main__":
    asyncio.run(main())