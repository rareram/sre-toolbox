import json
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from src.models import Incident, AlertEvent
from src.triage_agent import TriageAgent

def test_clean_json_output_with_markdown_blocks():
    # 마크다운 코드블록 정제 검증: LLM 응답 내 백틱(```json) 제거 및 JSON 파싱 확인
    agent = TriageAgent()
    raw = """```json
    {
      "fact_summary": "DB 연결 고갈 확인",
      "hypothesis": "슬로우 쿼리로 인한 락 경합 추정",
      "recommended_actions": [
        {"label": "최근 로그 확인", "tool_name": "get_recent_logs", "parameters": {"lines": 30}}
      ],
      "reply_text": "현재 DB 커넥션 풀이 포화 상태입니다."
    }
    ```"""
    parsed = agent._clean_json_output(raw)
    assert parsed["fact_summary"] == "DB 연결 고갈 확인"
    assert len(parsed["recommended_actions"]) == 1

def test_clean_json_output_fallback_on_broken_json():
    # 비정형 텍스트 폴백 검증: JSON 파싱 실패 시 기본 응답 구조 반환 확인
    agent = TriageAgent()
    broken = "이것은 유효한 JSON이 아닙니다."
    parsed = agent._clean_json_output(broken)
    assert "JSON 파싱 실패" in parsed["fact_summary"]
    assert len(parsed["recommended_actions"]) > 0

import asyncio

def test_analyze_and_respond_success():
    # 트리아지 응답 생성 검증: 모의 LLM 응답 기반 Fact/Hypothesis 분리 및 추천 액션 확인
    agent = TriageAgent()
    incident = Incident(
        incident_id="INC-MOCK-01",
        service_name="payment-api",
        alerts=[AlertEvent(fingerprint="fp1", alertname="HighErrorRate")]
    )

    mock_llm_response = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "fact_summary": "HighErrorRate 알람 발생",
                    "hypothesis": "PG 결제사 타임아웃 추정",
                    "recommended_actions": [
                        {"label": "PG 응답 확인", "tool_name": "run_diagnostic_ping", "parameters": {"target": "pg.internal"}}
                    ],
                    "reply_text": "결제사 게이트웨이 응답을 확인해야 합니다."
                })
            }
        }]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_llm_response
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = asyncio.run(agent.analyze_and_respond(
            incident=incident,
            user_message="지금 어떤 상황이야?",
            chat_history=[],
            action_results=[]
        ))

    assert res.incident_id == "INC-MOCK-01"
    assert "HighErrorRate" in res.fact_summary
    assert "PG 결제사" in res.hypothesis
    assert len(res.recommended_actions) == 1
    assert res.recommended_actions[0].tool_name == "run_diagnostic_ping"
