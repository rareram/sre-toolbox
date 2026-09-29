import pytest
from unittest.mock import patch, MagicMock
import httpx
from src.tools import MockToolRunner, RealToolRunner
from src.catalog import CsvInventoryProvider

def test_mock_tool_execution():
    runner = MockToolRunner()
    inc_id = "INC-TOOL-TEST"

    # Loki 로그 수집: 지정 줄 수 및 서비스 기준 스냅샷 추출 검증
    res_log = runner.execute(inc_id, "get_recent_logs", {"lines": 10, "service": "payment-api"})
    assert res_log.success is True
    assert "Loki Mock Log Snapshot" in res_log.output

    # Prometheus 메트릭 추세: 커넥션 풀 사용률 및 증가율 계산 검증
    res_metric = runner.execute(inc_id, "check_metrics_trend", {"metric_name": "db_connection_usage"})
    assert res_metric.success is True
    assert "Prometheus Mock Trend" in res_metric.output

    # k8s 파드 상태 점검: 재시작 횟수 및 OOMKilled 이벤트 확인 검증
    res_pod = runner.execute(inc_id, "inspect_pod_status", {})
    assert res_pod.success is True
    assert "Kubernetes Pod Status Mock" in res_pod.output

    # 서버 인벤토리 모의 조회 검증
    res_server = runner.execute(inc_id, "lookup_server", {"query": "10.19.20.104"})
    assert res_server.success is True
    assert "spark-worker-04" in res_server.output

    # 허용 목록 검증: 미등록 위험 명령(dangerous_shell_command) 실행 차단 확인
    res_unknown = runner.execute(inc_id, "dangerous_shell_command", {})
    assert res_unknown.success is False
    assert "Unknown tool name" in res_unknown.output

def test_real_tool_runner_server_lookup():
    catalog = CsvInventoryProvider("config/servers.example.csv")
    runner = RealToolRunner(inventory_provider=catalog)
    inc_id = "INC-TOOL-TEST"

    # IP로 실제 카탈로그 조회
    res = runner.execute(inc_id, "lookup_server", {"query": "10.19.20.104"})
    assert res.success is True
    assert "spark-worker-04" in res.output
    assert "IDC 2F Rack A-04 12U" in res.output

    # 존재하지 않는 서버 검색
    res_none = runner.execute(inc_id, "lookup_server", {"query": "192.168.99.99"})
    assert res_none.success is True
    assert "찾지 못했습니다" in res_none.output

def test_real_tool_runner_diagnostic_ping():
    runner = RealToolRunner()
    inc_id = "INC-TOOL-TEST"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.reason_phrase = "OK"

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        res = runner.execute(inc_id, "run_diagnostic_ping", {"target": "http://10.30.1.20:8080/healthz"})
        assert res.success is True
        assert "Healthcheck Ping 결과" in res.output
        assert "200 OK" in res.output
