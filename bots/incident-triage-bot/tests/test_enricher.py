import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.models import AlertEvent, Incident, ChatMessage, ActionButton, TriageResponse
from src.catalog import CsvInventoryProvider, ServerNode
from src.telemetry import MockTelemetryClient, TelemetryClient
from src.enricher import ContextEnricher, EnrichedContext
from src.storage import SqliteRepository
from src.correlation import CorrelationEngine
from src.app import app
import src.app as app_module

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_isolated_test_env(tmp_path):
    # 테스트 전용 격리 DB 및 인벤토리 CSV 구성
    db_file = tmp_path / "enricher_test.db"
    csv_file = tmp_path / "test_servers.csv"
    csv_file.write_text(
        "ip,hostname,cluster,role,location,owner,health_url,runbook_url,check_command,tags\n"
        "10.19.20.104,spark-worker-04,spark-prod,Spark Worker,IDC 2F Rack A-04 12U,홍길동,http://10.19.20.104:8080/healthz,https://wiki.corp/spark,systemctl status spark-worker,spark;worker;prod\n"
        "10.19.20.201,payment-db-master,pay-cluster,MySQL Master,IDC 3F Rack C-01 10U,데이터팀 이몽룡,,https://wiki.corp/db-master,show processlist,mysql;db;prod\n"
    )

    new_repo = SqliteRepository(str(db_file))
    new_engine = CorrelationEngine(new_repo, window_seconds=60)
    new_catalog = CsvInventoryProvider(str(csv_file))
    mock_telemetry = MockTelemetryClient()

    app_module.repo = new_repo
    app_module.correlation_engine = new_engine
    app_module.inventory_provider = new_catalog
    app_module.telemetry_client = mock_telemetry
    app_module.context_enricher = ContextEnricher(catalog=new_catalog, telemetry=mock_telemetry)

    yield


def test_extract_target_host_or_ip():
    # 라벨에서 IP/호스트명 및 포트 분리 로직 검증
    catalog = app_module.inventory_provider
    enricher = ContextEnricher(catalog=catalog, telemetry=MockTelemetryClient())

    assert enricher.extract_target_host_or_ip({"instance": "10.19.20.104:9100"}) == "10.19.20.104"
    assert enricher.extract_target_host_or_ip({"host": "spark-worker-04:8080"}) == "spark-worker-04"
    assert enricher.extract_target_host_or_ip({"node": "k8s-node-01"}) == "k8s-node-01"
    assert enricher.extract_target_host_or_ip({"server": "10.19.20.201"}) == "10.19.20.201"
    assert enricher.extract_target_host_or_ip({}) is None


@pytest.mark.anyio
async def test_enrich_with_catalog_and_telemetry():
    # 카탈로그 매핑 및 텔레메트리 병렬 수집 검증
    catalog = app_module.inventory_provider
    enricher = ContextEnricher(catalog=catalog, telemetry=MockTelemetryClient())

    alert = AlertEvent(
        fingerprint="fp-spark-01",
        alertname="SparkWorkerDead",
        labels={"instance": "10.19.20.104:9100", "service": "spark"}
    )

    enriched = await enricher.enrich(
        alert=alert,
        service_name="spark",
        recent_changes_hint="30분 전 spark-worker 버전 v2.4.1 패치 배포"
    )

    assert enriched.server_node is not None
    assert enriched.server_node.hostname == "spark-worker-04"
    assert enriched.server_node.location == "IDC 2F Rack A-04 12U"
    assert "Prometheus Mock Trend" in enriched.metrics_trend
    assert "Loki Mock Log Snapshot" in enriched.recent_logs
    assert enriched.recent_changes == "30분 전 spark-worker 버전 v2.4.1 패치 배포"

    summary = enriched.to_prompt_context()
    assert "[대상 서버 인벤토리 정보]" in summary
    assert "spark-worker-04 (IP: 10.19.20.104)" in summary
    assert "[최근 30분 시스템 변경 이력]" in summary


@pytest.mark.anyio
async def test_enrich_telemetry_exception_graceful_handling():
    # 외부 텔레메트리 예외 발생 시 격리 및 폴백 확인
    class FailingTelemetry(TelemetryClient):
        async def query_metrics_trend(self, query: str, duration_minutes: int = 5) -> str:
            raise RuntimeError("Prometheus Connection Refused")

        async def query_recent_logs(self, query: str, limit: int = 20) -> str:
            raise TimeoutError("Loki query timed out after 3.0s")

    catalog = app_module.inventory_provider
    enricher = ContextEnricher(catalog=catalog, telemetry=FailingTelemetry())

    alert = AlertEvent(
        fingerprint="fp-fail-01",
        alertname="ServiceError",
        labels={"instance": "10.19.20.104"}
    )

    enriched = await enricher.enrich(alert=alert, service_name="payment")
    assert enriched.server_node is not None
    assert "[메트릭 수집 예외" in enriched.metrics_trend
    assert "[로그 수집 예외" in enriched.recent_logs


def test_chat_shortcut_server_command_hit():
    # 대화창에서 /server <ip> 입력 시 LLM 없이 즉시 카탈로그 정보 반환 검증
    # 1. 인시던트 준비
    hook_res = client.post("/webhook/grafana", json={
        "alerts": [{"labels": {"service": "spark-service", "instance": "10.19.20.104"}}]
    })
    inc_id = hook_res.json()["results"][0]["incident_id"]

    # 2. /server 명령어 전송
    chat_res = client.post("/api/chat", json={
        "incident_id": inc_id,
        "message": "/server 10.19.20.104"
    })
    assert chat_res.status_code == 200
    data = chat_res.json()

    assert "spark-worker-04" in data["fact_summary"]
    assert "IDC 2F Rack A-04 12U" in data["hypothesis"]
    assert "spark-worker-04 (IP: 10.19.20.104)" in data["reply_text"]
    assert len(data["recommended_actions"]) >= 1


def test_chat_shortcut_server_command_miss():
    # 대화창에서 미등록 IP 입력 시 친절한 안내 메시지 반환 검증
    hook_res = client.post("/webhook/grafana", json={
        "alerts": [{"labels": {"service": "unknown-service"}}]
    })
    inc_id = hook_res.json()["results"][0]["incident_id"]

    chat_res = client.post("/api/chat", json={
        "incident_id": inc_id,
        "message": "/server 192.168.99.99"
    })
    assert chat_res.status_code == 200
    data = chat_res.json()

    assert "결과 없음" in data["fact_summary"]
    assert "찾을 수 없습니다" in data["reply_text"]


def test_catalog_rest_endpoints():
    # REST API를 통한 카탈로그 키워드 검색 및 단건 조회 검증
    # 1. 키워드 검색
    search_res = client.get("/api/catalog/search?q=MySQL")
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["count"] == 1
    assert data["servers"][0]["hostname"] == "payment-db-master"

    # 2. IP 단건 조회
    single_res = client.get("/api/catalog/servers/10.19.20.201")
    assert single_res.status_code == 200
    server_data = single_res.json()
    assert server_data["role"] == "MySQL Master"
    assert server_data["owner"] == "데이터팀 이몽룡"

    # 3. 404 미등록 서버
    not_found = client.get("/api/catalog/servers/99.99.99.99")
    assert not_found.status_code == 404
