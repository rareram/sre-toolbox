import json
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from src.app import app, repo, correlation_engine
from src.models import IncidentStatus

from src.storage import SqliteRepository
from src.correlation import CorrelationEngine
import src.app as app_module

@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path):
    db_file = tmp_path / "api_test.db"
    new_repo = SqliteRepository(str(db_file))
    new_engine = CorrelationEngine(new_repo, window_seconds=60)

    app_module.repo = new_repo
    app_module.correlation_engine = new_engine
    yield

client = TestClient(app)

def test_healthz_endpoint():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data
    assert "llm_model" in data

def test_webhook_grafana_and_correlation():
    grafana_payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "PodCrashLooping",
                    "service": "order-service",
                    "severity": "critical"
                },
                "annotations": {
                    "summary": "Pod order-service-xxx is crash looping"
                }
            }
        ]
    }

    # 1차 알람 수신 검증: 최초 알람 발생 시 신규 인시던트 생성(is_new=True) 확인
    resp1 = client.post("/webhook/grafana", json=grafana_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()["results"][0]
    assert data1["is_new_incident"] is True
    inc_id = data1["incident_id"]

    # 연속 알람 수신 검증: 동일 서비스/시간 윈도우 내 기존 인시던트 병합(is_new=False) 확인
    resp2 = client.post("/webhook/grafana", json=grafana_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()["results"][0]
    assert data2["is_new_incident"] is False
    assert data2["incident_id"] == inc_id
    assert data2["total_alerts_count"] == 2

@patch("src.triage_agent.TriageAgent.analyze_and_respond")
def test_chat_and_action_flow(mock_analyze):
    from src.models import TriageResponse, ActionButton

    # 테스트용 인시던트 준비: inventory-api 대상 모의 알람 주입
    alert_payload = {
        "labels": {"service": "inventory-api", "alertname": "StockMismatch"}
    }
    hook_res = client.post("/webhook/grafana", json={"alerts": [alert_payload]})
    inc_id = hook_res.json()["results"][0]["incident_id"]

    # LLM 추론 모의 설정: Fact/Hypothesis/추천 액션 반환 스텁 구성
    mock_analyze.return_value = TriageResponse(
        incident_id=inc_id,
        fact_summary="재고 불일치 감지",
        hypothesis="비동기 메시지 유실 추정",
        recommended_actions=[
            ActionButton(label="최근 로그 확인", tool_name="get_recent_logs", parameters={"lines": 10})
        ],
        reply_text="메시지 큐 지연 여부를 점검해야 합니다."
    )

    # 1. 자연어 질문/답변 검증: 엔지니어 질문 전달 및 봇 응답 스키마 확인
    chat_res = client.post("/api/chat", json={
        "incident_id": inc_id,
        "message": "현재 인벤토리 상태 어때?"
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["fact_summary"] == "재고 불일치 감지"
    assert len(chat_data["recommended_actions"]) == 1

    # 2. 추천 점검 버튼 실행 검증: get_recent_logs 실행 및 성공 상태 확인
    action_res = client.post("/api/action", json={
        "incident_id": inc_id,
        "tool_name": "get_recent_logs",
        "parameters": {"lines": 10}
    })
    assert action_res.status_code == 200
    assert action_res.json()["success"] is True

    # 3. 인시던트 이력 저장 검증: 대화 내역(user/bot) 및 도구 실행 결과 DB 저장 확인
    detail_res = client.get(f"/api/incidents/{inc_id}")
    assert detail_res.status_code == 200
    details = detail_res.json()
    assert len(details["chat_history"]) == 2  # user + bot
    assert len(details["action_results"]) == 1

    # 4. 인시던트 종료 검증: 상태 RESOLVED 변경 확인
    status_res = client.post(f"/api/incidents/{inc_id}/status", json={"status": "RESOLVED"})
    assert status_res.status_code == 200
    assert status_res.json()["updated_status"] == "RESOLVED"
