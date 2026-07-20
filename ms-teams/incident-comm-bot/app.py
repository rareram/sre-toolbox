# -*- coding: utf-8 -*-
import os
import json
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# OpenAI SDK (>=1.x)
from openai import OpenAI

from prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()
app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-5")  # 환경에 맞게 변경 가능
TEAMS_WEBHOOK  = os.getenv("TEAMS_WEBHOOK")          # 선택 사항

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_three_layers(raw_incident: str) -> str:
    user = USER_PROMPT_TEMPLATE.format(raw_incident=raw_incident.strip())
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content

def post_to_teams(markdown_text: str, webhook_url: str):
    # Teams Incoming Webhook: 단순 text payload 지원
    payload = {"text": markdown_text}
    r = requests.post(webhook_url, data=json.dumps(payload),
                      headers={"Content-Type": "application/json"})
    r.raise_for_status()

@app.route("/healthz", methods=["GET"])
def healthz():
    return "ok", 200

@app.route("/generate", methods=["POST"])
def generate():
    """
    JSON body 예:
    {
      "raw_incident": "2025-10-23 20:12:45 ... 코어덤프 ... 역할 ...",
      "post_to_teams": true,
      "post_section": "leader"  // "dev" | "leader" | "customer"
    }
    """
    data = request.get_json(force=True)
    raw_incident = data.get("raw_incident", "")
    post_flag = bool(data.get("post_to_teams", False))
    post_section = (data.get("post_section") or "").lower()

    if not raw_incident.strip():
        return jsonify({"error": "raw_incident is required"}), 400

    full_md = generate_three_layers(raw_incident)

    # 섹션별 발췌(간단 파서)
    # --- 구분 헤더를 기준으로 자릅니다.
    dev_md, leader_md, customer_md = None, None, None
    parts = full_md.split("## ")
    for p in parts:
        q = p.strip()
        if q.startswith("🧑‍💻 ① 개발팀 내부 공유용"):
            dev_md = "## " + q
        elif q.startswith("🧭 ② 리더·임원 보고용"):
            leader_md = "## " + q
        elif q.startswith("🤝 ③ 고객 및 대표 보고용"):
            customer_md = "## " + q

    result = {
        "full_markdown": full_md,
        "dev_markdown": dev_md,
        "leader_markdown": leader_md,
        "customer_markdown": customer_md,
    }

    if post_flag:
        if not TEAMS_WEBHOOK:
            return jsonify({"error": "TEAMS_WEBHOOK not set in environment"}), 500
        section_map = {
            "dev": dev_md or "",
            "leader": leader_md or "",
            "customer": customer_md or "",
        }
        post_body = section_map.get(post_section) or full_md
        post_to_teams(post_body, TEAMS_WEBHOOK)

        result["posted"] = post_section or "full"

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))

