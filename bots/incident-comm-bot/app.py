# -*- coding: utf-8 -*-
import os
import json
import re
import socket
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
from openai import OpenAI

from prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()
app = Flask(__name__)

# LLM Provider 설정 (Local Ollama / vLLM / OpenAI 호환)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL    = os.getenv("LLM_MODEL", "gemma4:e4b")


# 봇 운영 및 식별 메타데이터
BOT_NAME     = os.getenv("BOT_NAME", "incident-comm-bot")
BOT_VERSION  = os.getenv("BOT_VERSION", "v0.2.0")
BOT_OWNER    = os.getenv("BOT_OWNER", "sre-team@company.com")
HOSTNAME     = socket.gethostname()

TEAMS_WEBHOOK = os.getenv("TEAMS_WEBHOOK")

client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY
)

# 메모리 기반 장애 타임라인 저장소:
# { incident_id: { "first_seen": "HH:MM:SS", "first_seen_dt": datetime, "update_count": int, "history": [ {"timestamp": "...", "entry": "..."}, ... ] } }
INCIDENT_STORE = {}

def get_or_create_incident_id(custom_id: str = None) -> str:
    if custom_id and custom_id.strip():
        return custom_id.strip()
    today_str = datetime.now().strftime("%Y%m%d")
    return f"INC-{today_str}-01"

def format_timeline(incident_id: str) -> str:
    store_item = INCIDENT_STORE.get(incident_id)
    if not store_item or not store_item.get("history"):
        return "없음 (최초 발생)"
    lines = []
    for item in store_item["history"]:
        lines.append(f"- [{item['timestamp']}] {item['entry']}")
    return "\n".join(lines)

def clean_json_response(raw_content: str) -> dict:
    """LLM 응답에서 마크다운 코드블록(` ```json ... ``` `) 제거 후 JSON 파싱"""
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\n?```$", "", cleaned, flags=re.MULTILINE)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback 구조
        return {
            "dev_markdown": f"## [1. 개발팀 내부 공유용 - Technical Report]\n{raw_content}",
            "leader_markdown": f"## [2. 리더/임원 보고용 - Managerial Summary]\n{raw_content}",
            "customer_markdown": f"## [3. 고객/외부 공지용 - External Notice]\n{raw_content}",
            "remediation_hint": "## [4. 플레이북 긴급 조치 가이드 - Remediation Hint]\n- 원문 로그 및 스택트레이스 유효성 점검 권장",
            "checklist": ["로그 및 스택트레이스 유효성 확인"],
            "timeline_entry": "상황 공유 수신 완료"
        }

def generate_incident_report(raw_incident: str, incident_id: str) -> dict:
    previous_timeline = format_timeline(incident_id)
    user_content = USER_PROMPT_TEMPLATE.format(
        incident_id=incident_id,
        previous_timeline=previous_timeline,
        raw_incident=raw_incident.strip()
    )

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
        )
        raw_output = resp.choices[0].message.content
        parsed = clean_json_response(raw_output)
    except Exception as e:
        app.logger.error(f"LLM Call Error: {e}")
        parsed = {
            "dev_markdown": f"LLM 분석 오류 발생: {str(e)}",
            "leader_markdown": f"장애 리포트 분석 중 오류 발생: {str(e)}",
            "customer_markdown": "현재 관련 부서에서 상황을 파악 중입니다.",
            "remediation_hint": "LLM 연동 상태 및 API Key/Base URL 점검 필요",
            "checklist": ["LLM 연동 상태 및 API Key/Base URL 점검"],
            "timeline_entry": "알림 수신 (분석 실패)"
        }

    # 장애 통계 및 타임라인 업데이트 누적
    now_dt = datetime.now()
    now_time_str = now_dt.strftime("%H:%M:%S")
    entry_text = parsed.get("timeline_entry") or "상황 업데이트 수신"

    if incident_id not in INCIDENT_STORE:
        INCIDENT_STORE[incident_id] = {
            "first_seen": now_time_str,
            "first_seen_dt": now_dt,
            "update_count": 0,
            "history": []
        }

    item = INCIDENT_STORE[incident_id]
    item["update_count"] += 1
    item["history"].append({
        "timestamp": now_time_str,
        "entry": entry_text
    })

    # 지속 시간 계산
    elapsed_seconds = int((now_dt - item["first_seen_dt"]).total_seconds())
    mins, secs = divmod(elapsed_seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        duration_str = f"{hrs}시간 {mins}분 {secs}초 진행 중"
    elif mins > 0:
        duration_str = f"{mins}분 {secs}초 진행 중"
    else:
        duration_str = f"{secs}초 진행 중 (방금 발생)"

    parsed["incident_id"] = incident_id
    parsed["first_seen"] = item["first_seen"]
    parsed["update_count"] = item["update_count"]
    parsed["duration_str"] = duration_str
    parsed["full_timeline"] = item["history"]
    return parsed

def post_to_teams(markdown_text: str, webhook_url: str):
    payload = {"text": markdown_text}
    r = requests.post(webhook_url, data=json.dumps(payload),
                      headers={"Content-Type": "application/json"}, timeout=10)
    r.raise_for_status()

def build_teams_composite_message(parsed_report: dict, section: str = "all") -> str:
    inc_id = parsed_report.get("incident_id", "N/A")
    first_seen = parsed_report.get("first_seen", "N/A")
    update_count = parsed_report.get("update_count", 1)
    duration_str = parsed_report.get("duration_str", "방금 발생")

    checklist_items = parsed_report.get("checklist", [])
    checklist_md = "\n".join([f"- [ ] {item}" for item in checklist_items])
    
    timeline_items = parsed_report.get("full_timeline", [])
    timeline_md = "\n".join([f"- **[{t['timestamp']}]** {t['entry']}" for t in timeline_items])

    # 장애 현황 통계 헤더 부착
    stats_header = f"⏱️ **최초 발생**: `{first_seen}` | ⏳ **지속 시간**: `{duration_str}` | 🔄 **보고 횟수**: `{update_count}차 업데이트`"
    parts = [f"# [장애 대응 리포트] {inc_id}\n{stats_header}"]
    
    if section in ["all", "dev"]:
        parts.append(parsed_report.get("dev_markdown", ""))
    if section in ["all", "leader"]:
        parts.append(parsed_report.get("leader_markdown", ""))
    if section in ["all", "customer"]:
        parts.append(parsed_report.get("customer_markdown", ""))
    
    if parsed_report.get("remediation_hint"):
        parts.append(parsed_report.get("remediation_hint"))
        
    parts.append(f"### [긴급 점검 체크리스트]\n{checklist_md}")
    parts.append(f"### [장애 진행 타임라인]\n{timeline_md}")
    
    # 봇 운영 식별 메타데이터 푸터 부착
    footer = f"*Bot*: `{BOT_NAME}` | *Ver*: `{BOT_VERSION}` | *Host*: `{HOSTNAME}` | *Owner*: `{BOT_OWNER}` | *LLM*: `{LLM_MODEL}`"
    parts.append(footer)

    return "\n\n---\n\n".join(parts)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({
        "status": "ok",
        "bot_name": BOT_NAME,
        "bot_version": BOT_VERSION,
        "bot_owner": BOT_OWNER,
        "hostname": HOSTNAME,
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL,
        "active_incidents": len(INCIDENT_STORE)
    }), 200

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True) or {}
    raw_incident = data.get("raw_incident", "")
    incident_id = get_or_create_incident_id(data.get("incident_id"))
    post_flag = bool(data.get("post_to_teams", False))
    post_section = (data.get("post_section") or "all").lower()

    if not raw_incident.strip():
        return jsonify({"error": "raw_incident is required"}), 400

    report = generate_incident_report(raw_incident, incident_id)

    if post_flag:
        if not TEAMS_WEBHOOK:
            return jsonify({"error": "TEAMS_WEBHOOK environment variable is not set"}), 500
        msg_to_send = build_teams_composite_message(report, post_section)
        try:
            post_to_teams(msg_to_send, TEAMS_WEBHOOK)
            report["posted_to_teams"] = True
        except Exception as e:
            report["posted_to_teams"] = False
            report["teams_post_error"] = str(e)

    return jsonify(report), 200

@app.route("/webhook/grafana", methods=["POST"])
def webhook_grafana():
    """Grafana Alertmanager Webhook Payload 수신"""
    data = request.get_json(force=True) or {}
    alerts = data.get("alerts", [])
    title = data.get("title") or "Grafana Alert Triggered"
    
    alert_details = []
    for a in alerts:
        status = a.get("status", "firing").upper()
        labels = a.get("labels", {})
        annotations = a.get("annotations", {})
        summary = annotations.get("summary") or annotations.get("description") or "No summary provided"
        alert_details.append(f"[{status}] Alert: {labels.get('alertname', 'Unknown')} | Service: {labels.get('service', 'N/A')}\nSummary: {summary}")

    raw_incident = f"Grafana Alert: {title}\n" + "\n".join(alert_details)
    
    common_labels = data.get("commonLabels", {})
    incident_id = get_or_create_incident_id(common_labels.get("incident_id") or common_labels.get("service"))

    report = generate_incident_report(raw_incident, incident_id)

    if TEAMS_WEBHOOK:
        msg_to_send = build_teams_composite_message(report, "all")
        try:
            post_to_teams(msg_to_send, TEAMS_WEBHOOK)
            report["posted_to_teams"] = True
        except Exception as e:
            report["posted_to_teams"] = False
            report["teams_post_error"] = str(e)

    return jsonify(report), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
