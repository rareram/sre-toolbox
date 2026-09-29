import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import httpx
import pytest

from src.models import Incident, AlertEvent, IncidentStatus
from src.storage import SqliteRepository
from src.correlation import CorrelationEngine
from src.catalog import CsvInventoryProvider
from src.telemetry import RealTelemetryClient
from src.tools import RealToolRunner

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

# 1. 인시던트 유휴 만료 및 좀비 세션 방지 검증
def test_incident_session_idle_timeout_prevents_zombie_merging(temp_db):
    repo = SqliteRepository(temp_db)
    # 유휴 시간을 2초로 짧게 설정한 엔진
    engine = CorrelationEngine(repo, window_seconds=60, max_idle_seconds=2)

    raw_alert_1 = {
        "labels": {"alertname": "HighCPU", "service": "payment-api", "environment": "production"},
        "status": "firing"
    }

    # 1차 알람: 신규 인시던트 생성
    inc_1, _, is_new_1 = engine.process_alert(raw_alert_1)
    assert is_new_1 is True

    # 2차 알람: 유휴 시간(2초) 이내이므로 기존 인시던트에 병합
    raw_alert_2 = {
        "labels": {"alertname": "HighMemory", "service": "payment-api", "environment": "production"},
        "status": "firing"
    }
    inc_2, _, is_new_2 = engine.process_alert(raw_alert_2)
    assert is_new_2 is False
    assert inc_2.incident_id == inc_1.incident_id
    assert len(inc_2.alerts) == 2

    # 세션 유휴 시간 경과 시뮬레이션: DB 상의 last_updated_at을 과거(10초 전)로 직접 업데이트
    past_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    with repo._get_connection() as conn:
        conn.execute("UPDATE incidents SET last_updated_at = ? WHERE incident_id = ?", (past_time, inc_1.incident_id))

    # 3차 알람: 이전 인시던트가 RESOLVED가 아니지만 유휴 시간(2초)이 지났으므로 새 인시던트 분기
    raw_alert_3 = {
        "labels": {"alertname": "DiskFull", "service": "payment-api", "environment": "production"},
        "status": "firing"
    }
    inc_3, _, is_new_3 = engine.process_alert(raw_alert_3)
    assert is_new_3 is True
    assert inc_3.incident_id != inc_1.incident_id
    assert inc_3.summary == "[payment-api] DiskFull 감지됨"

# 2. 관측성 토큰 만료(HTTP 401/403) 시 우아한 기능 저하(Graceful Degrade) 검증
@pytest.mark.anyio
async def test_telemetry_token_expiration_handling():
    client = RealTelemetryClient(
        prometheus_url="http://mock-prom:9090",
        prometheus_token="expired-prom-token",
        loki_url="http://mock-loki:3100",
        loki_token="expired-loki-token"
    )

    mock_401_resp = MagicMock()
    mock_401_resp.status_code = 401

    mock_403_resp = MagicMock()
    mock_403_resp.status_code = 403

    # Prometheus 401 시 크래시 없이 명확한 인증 오류 및 폴백 반환
    with patch.object(httpx.AsyncClient, "get", return_value=mock_401_resp):
        res_prom = await client.query_metrics_trend("up", duration_minutes=5)
        assert "HTTP 401" in res_prom
        assert "토큰 만료/권한 부족" in res_prom
        assert "로컬 폴백 모드" in res_prom

    # Loki 403 시 크래시 없이 명확한 인증 오류 및 폴백 반환
    with patch.object(httpx.AsyncClient, "get", return_value=mock_403_resp):
        res_loki = await client.query_recent_logs('{app="payment"}', limit=10)
        assert "HTTP 403" in res_loki
        assert "토큰 만료/권한 부족" in res_loki
        assert "로컬 폴백 모드" in res_loki

def test_real_tool_runner_token_expiration_handling():
    runner = RealToolRunner(
        prometheus_url="http://mock-prom:9090",
        prometheus_token="expired-prom-token",
        loki_url="http://mock-loki:3100",
        loki_token="expired-loki-token"
    )
    mock_401_resp = MagicMock()
    mock_401_resp.status_code = 401

    with patch.object(httpx.Client, "get", return_value=mock_401_resp):
        res = runner.execute("INC-TEST", "check_metrics_trend", {"metric_name": "up"})
        assert res.success is False
        assert "HTTP 401" in res.output
        assert "토큰 만료/권한 부족" in res.output

# 3. 인프라 카탈로그 파일 mtime 기반 무재기동 핫 리로드 검증
def test_inventory_mtime_hot_reload():
    initial_csv = """ip,hostname,cluster,role,location,owner,health_url,runbook_url,check_command,tags
10.0.1.10,app-server-01,app-cluster,App Server,IDC 1F Rack A-01,인프라팀,http://10.0.1.10:8080,,,"prod,app"
"""
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as f:
        f.write(initial_csv)
        f.flush()
        file_path = f.name

    try:
        catalog = CsvInventoryProvider(file_path)
        # 초기 장비 조회
        node_1 = catalog.get_by_ip("10.0.1.10")
        assert node_1 is not None
        assert node_1.hostname == "app-server-01"

        # 신규 장비는 아직 없음
        assert catalog.get_by_ip("10.0.1.20") is None

        # 파일 변경 시뮬레이션: 파일에 신규 서버 내용 추가 및 mtime 갱신
        time.sleep(0.05) # mtime 차이 보장
        updated_csv = initial_csv + "10.0.1.20,app-server-02,app-cluster,App Server,IDC 1F Rack A-02,인프라팀,http://10.0.1.20:8080,,,\"prod,app\"\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_csv)
            f.flush()

        # 봇 재기동 없이 get_by_ip 호출 시 자동 핫 리로드 확인
        node_2 = catalog.get_by_ip("10.0.1.20")
        assert node_2 is not None
        assert node_2.hostname == "app-server-02"
        assert node_2.location == "IDC 1F Rack A-02"

        # 검색 기능에서도 핫 리로드 반영 확인
        nodes = catalog.search("app-server-02")
        assert len(nodes) == 1
        assert nodes[0].ip == "10.0.1.20"
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
