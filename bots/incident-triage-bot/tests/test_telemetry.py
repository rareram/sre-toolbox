import pytest
from unittest.mock import patch, MagicMock
import httpx
from src.telemetry import RealTelemetryClient, MockTelemetryClient

@pytest.mark.anyio
async def test_mock_telemetry_client():
    client = MockTelemetryClient()
    metrics_res = await client.query_metrics_trend("node_cpu_utilization", duration_minutes=5)
    assert "[Prometheus Mock Trend:" in metrics_res
    assert "node_cpu_utilization" in metrics_res

    logs_res = await client.query_recent_logs('{app="payment"}', limit=10)
    assert "[Loki Mock Log Snapshot:" in logs_res
    assert "Connection pool exhausted" in logs_res

@pytest.mark.anyio
async def test_real_telemetry_prometheus_success():
    client = RealTelemetryClient(prometheus_url="http://mock-prom:9090")

    mock_resp_data = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"instance": "10.19.20.104:9100", "job": "node-exporter"},
                    "values": [
                        [1725900000, "20.0"],
                        [1725900015, "50.0"],
                        [1725900030, "85.0"],
                    ]
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        res = await client.query_metrics_trend('node_load1{instance="10.19.20.104:9100"}', duration_minutes=5)
        assert "[Prometheus 실측 추세:" in res
        assert "시작값: 20.00 -> 현재값: 85.00" in res
        assert "instance=10.19.20.104:9100" in res

@pytest.mark.anyio
async def test_real_telemetry_prometheus_timeout():
    client = RealTelemetryClient(prometheus_url="http://mock-prom:9090", timeout_seconds=1.0)

    with patch.object(httpx.AsyncClient, "get", side_effect=httpx.TimeoutException("Read timed out")):
        res = await client.query_metrics_trend("up", duration_minutes=5)
        assert "타임아웃" in res
        assert "폴백 모드" in res

@pytest.mark.anyio
async def test_real_telemetry_loki_success():
    client = RealTelemetryClient(loki_url="http://mock-loki:3100")

    mock_resp_data = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"app": "order-api"},
                    "values": [
                        ["1725900030000000000", "2026-09-09 23:01:00 [ERROR] Out of memory in order processing"],
                        ["1725900015000000000", "2026-09-09 23:00:45 [WARN] Slow response on db query"]
                    ]
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        res = await client.query_recent_logs('{app="order-api"} |= "ERROR"', limit=10)
        assert "[Loki 실측 최근 로그" in res
        assert "Out of memory in order processing" in res

@pytest.mark.anyio
async def test_real_telemetry_loki_500_error():
    client = RealTelemetryClient(loki_url="http://mock-loki:3100")

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        res = await client.query_recent_logs('{app="order-api"}', limit=10)
        assert "HTTP 500" in res
        assert "폴백 모드" in res
