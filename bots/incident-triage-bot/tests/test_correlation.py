import pytest
from src.models import IncidentStatus
from src.storage import SqliteRepository
from src.correlation import CorrelationEngine

@pytest.fixture
def correlation_setup(tmp_path):
    db_file = tmp_path / "test_corr.db"
    repo = SqliteRepository(str(db_file))
    engine = CorrelationEngine(repo, window_seconds=60)
    return repo, engine

def test_extract_service_name_priorities():
    assert CorrelationEngine.extract_service_name({"service": "order-api"}) == "order-api"
    assert CorrelationEngine.extract_service_name({"app": "billing-app"}) == "billing-app"
    assert CorrelationEngine.extract_service_name({"container": "nginx-ingress"}) == "nginx-ingress"
    assert CorrelationEngine.extract_service_name({"job": "prometheus-k8s"}) == "prometheus-k8s"
    assert CorrelationEngine.extract_service_name({"alertname": "HostHighMemory"}) == "HostHighMemory"
    assert CorrelationEngine.extract_service_name({}) == "unknown-service"

def test_alert_correlation_into_single_incident(correlation_setup):
    repo, engine = correlation_setup

    alert_1 = {
        "status": "firing",
        "labels": {"service": "payment-api", "alertname": "ConnectionPoolExhausted"},
        "annotations": {"summary": "DB Connection High"}
    }
    incident_1, _, is_new_1 = engine.process_alert(alert_1)
    assert is_new_1 is True
    assert incident_1.service_name == "payment-api"
    assert len(incident_1.alerts) == 1

    # 윈도우 시간 내 후속 알람: 동일 서비스(payment-api) 다운스트림 알람 수신
    alert_2 = {
        "status": "firing",
        "labels": {"service": "payment-api", "alertname": "TransactionTimeout"},
        "annotations": {"summary": "Timeout over 5s"}
    }
    incident_2, _, is_new_2 = engine.process_alert(alert_2)
    # 알람 병합 검증: 신규 인시던트 생성 차단(is_new=False) 및 기존 ID 일치 확인
    assert is_new_2 is False
    assert incident_2.incident_id == incident_1.incident_id
    assert len(incident_2.alerts) == 2

def test_new_incident_after_resolved(correlation_setup):
    repo, engine = correlation_setup

    alert = {"labels": {"service": "search-api", "alertname": "SearchLatencyHigh"}}
    inc_1, _, is_new_1 = engine.process_alert(alert)
    assert is_new_1 is True

    # 인시던트 종료 처리: 상태 RESOLVED 변경
    repo.update_incident_status(inc_1.incident_id, IncidentStatus.RESOLVED)

    # 종료 후 신규 알람 분리 검증: 종료된 인시던트와 섞이지 않고 신규 티켓 분리(is_new=True) 확인
    inc_2, _, is_new_2 = engine.process_alert(alert)
    assert is_new_2 is True
    assert inc_2.incident_id != inc_1.incident_id
