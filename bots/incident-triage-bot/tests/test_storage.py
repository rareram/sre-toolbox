import os
import pytest
from datetime import datetime
from src.models import Incident, AlertEvent, IncidentStatus, ChatMessage, ActionResult
from src.storage import SqliteRepository

@pytest.fixture
def temp_repo(tmp_path):
    # 테스트 격리: 테스트 케이스별 독립 임시 SQLite 인스턴스를 생성하여 데이터 오염 방지
    db_file = tmp_path / "test_triage.db"
    return SqliteRepository(str(db_file))

def test_save_and_get_incident(temp_repo):
    incident = Incident(
        incident_id="INC-20260909-PAY-01",
        service_name="payment-api",
        environment="production",
        current_status=IncidentStatus.NEW,
        severity="critical",
        summary="Payment failure spike"
    )
    temp_repo.save_incident(incident)

    fetched = temp_repo.get_incident("INC-20260909-PAY-01")
    assert fetched is not None
    assert fetched.service_name == "payment-api"
    assert fetched.current_status == IncidentStatus.NEW
    assert fetched.severity == "critical"

def test_add_alert_and_cascade_load(temp_repo):
    incident = Incident(
        incident_id="INC-20260909-AUTH-01",
        service_name="auth-service",
        summary="Auth failure"
    )
    temp_repo.save_incident(incident)

    alert = AlertEvent(
        fingerprint="fp12345",
        alertname="HighTokenErrorRate",
        labels={"service": "auth-service", "severity": "critical"},
        annotations={"summary": "Tokens invalid"}
    )
    temp_repo.add_alert_to_incident(incident.incident_id, alert)

    fetched = temp_repo.get_incident(incident.incident_id)
    assert len(fetched.alerts) == 1
    assert fetched.alerts[0].alertname == "HighTokenErrorRate"
    assert fetched.alerts[0].fingerprint == "fp12345"

def test_chat_history_order_and_limit(temp_repo):
    inc_id = "INC-CHAT-TEST"
    temp_repo.save_incident(Incident(incident_id=inc_id, service_name="test-svc"))

    for i in range(5):
        temp_repo.save_chat_message(ChatMessage(
            incident_id=inc_id,
            sender="user" if i % 2 == 0 else "bot",
            content=f"Message {i}"
        ))

    history = temp_repo.get_chat_history(inc_id, limit=3)
    assert len(history) == 3
    # 최근 대화 추출 검증: 최신 3건의 시간순(Message 2 -> 3 -> 4) 정렬 상태 확인
    assert history[0].content == "Message 2"
    assert history[2].content == "Message 4"

def test_action_results_persistence(temp_repo):
    inc_id = "INC-ACT-TEST"
    temp_repo.save_incident(Incident(incident_id=inc_id, service_name="test-svc"))

    res = ActionResult(
        incident_id=inc_id,
        tool_name="get_recent_logs",
        success=True,
        output="Mock Error Log"
    )
    temp_repo.save_action_result(res)

    results = temp_repo.get_action_results(inc_id)
    assert len(results) == 1
    assert results[0].tool_name == "get_recent_logs"
    assert results[0].success is True
    assert "Mock Error Log" in results[0].output

def test_update_incident_status(temp_repo):
    inc_id = "INC-STATUS-TEST"
    temp_repo.save_incident(Incident(incident_id=inc_id, service_name="test-svc"))

    temp_repo.update_incident_status(inc_id, IncidentStatus.RESOLVED)
    fetched = temp_repo.get_incident(inc_id)
    assert fetched.current_status == IncidentStatus.RESOLVED
