import datetime
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx

from src.models import ActionResult
from src.catalog import InventoryProvider

logger = logging.getLogger(__name__)

# 위험 변경(파드 삭제, 임의 쉘 실행, DB 조작) 전면 차단: 화이트리스트 기반 읽기 전용(Read-Only) 점검 도구만 허용
# 안전한 운영 연속성: 서버 인벤토리 역색인 및 비침습 헬스체크/텔레메트리 조회 지원

class ToolRunner(ABC):
    @abstractmethod
    def execute(self, incident_id: str, tool_name: str, parameters: Dict[str, Any]) -> ActionResult:
        pass


class MockToolRunner(ToolRunner):
    """
    외부 클러스터(Loki/Prometheus/k8s) 의존성을 배제한 오프라인 시뮬레이션 및 단위 테스트용 모의 러너.
    인벤토리 프로바이더가 제공되면 실제 카탈로그 조회를 수행하고, 없으면 모의 데이터를 반환합니다.
    """

    def __init__(self, inventory_provider: Optional[InventoryProvider] = None):
        self.inventory_provider = inventory_provider

    def execute(self, incident_id: str, tool_name: str, parameters: Dict[str, Any]) -> ActionResult:
        if tool_name == "get_recent_logs":
            lines = parameters.get("lines", 20)
            service = parameters.get("service", "unknown-service")
            output = (
                f"[Loki Mock Log Snapshot: {service} (Last {lines} lines)]\n"
                f"2026-09-09 23:00:12 [ERROR] Connection pool exhausted: active=50, idle=0, max=50\n"
                f"2026-09-09 23:00:15 [WARN] Request timeout on /api/v1/checkout after 5000ms\n"
                f"2026-09-09 23:00:18 [ERROR] HikariPool-1 - Connection is not available, request timed out\n"
                f"2026-09-09 23:00:20 [FATAL] Critical failure: DB deadlocks suspected on orders table"
            )
            return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)

        elif tool_name == "check_metrics_trend":
            metric = parameters.get("metric_name", "db_connection_usage")
            output = (
                f"[Prometheus Mock Trend: {metric}]\n"
                f"- 10m ago: 42% (Normal)\n"
                f"- 5m ago: 78% (Increasing rapid)\n"
                f"- 1m ago: 100% (Saturated, active thread queueing: 34 requests)\n"
                f"- Slope: +14.2% per minute"
            )
            return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)

        elif tool_name == "inspect_pod_status":
            output = (
                f"[Kubernetes Pod Status Mock]\n"
                f"- pod/payment-api-7b8f98d9-2q9lw: Running (Restarts: 0, Ready: 1/1, CPU: 85%, Mem: 72%)\n"
                f"- pod/payment-api-7b8f98d9-x8p4k: Running (Restarts: 1 [Last: OOMKilled 4m ago], Mem: 91%)\n"
                f"- Warning Event: Unhealthy Readiness probe failed 3 times"
            )
            return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)

        elif tool_name == "run_diagnostic_ping":
            target = parameters.get("target", "localhost:8080/healthz")
            output = f"[Healthcheck Ping Mock]\n- Target: {target}\n- Status Code: 503 Service Unavailable\n- Latency: 3200ms (High)"
            return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)

        elif tool_name == "lookup_server":
            query = parameters.get("query") or parameters.get("ip") or parameters.get("hostname") or ""
            if self.inventory_provider:
                node = self.inventory_provider.get_by_ip(query) or self.inventory_provider.get_by_hostname(query)
                if not node:
                    nodes = self.inventory_provider.search(query, limit=3)
                    if nodes:
                        node = nodes[0]
                if node:
                    output = f"[서버 인벤토리 조회 결과]\n{node.to_summary()}"
                    return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)
                return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=f"'{query}'에 해당하는 서버를 인벤토리에서 찾지 못했습니다.")

            output = (
                f"[서버 인벤토리 모의 조회 결과: {query}]\n"
                f"- 호스트명: spark-worker-04 (IP: 10.19.20.104)\n"
                f"- 역할/클러스터: Spark Worker / spark-prod\n"
                f"- 물리 위치: IDC 2F Rack A-04 12U\n"
                f"- 담당자: 데이터팀 홍길동\n"
                f"- 권장 점검 명령: `systemctl status spark-worker`"
            )
            return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)

        return ActionResult(
            incident_id=incident_id,
            tool_name=tool_name,
            success=False,
            output=f"Unknown tool name: {tool_name}"
        )


class RealToolRunner(ToolRunner):
    """
    실제 환경 연동을 위한 도구 러너.
    비침습적 원칙에 따라 읽기 전용 HTTP 엔드포인트 및 서버 인벤토리 카탈로그만 호출합니다.
    """

    def __init__(
        self,
        inventory_provider: Optional[InventoryProvider] = None,
        prometheus_url: str = "http://localhost:9090",
        prometheus_token: Optional[str] = None,
        prometheus_username: Optional[str] = None,
        prometheus_password: Optional[str] = None,
        loki_url: str = "http://localhost:3100",
        loki_token: Optional[str] = None,
        loki_tenant_id: Optional[str] = None,
        loki_username: Optional[str] = None,
        loki_password: Optional[str] = None,
        timeout_seconds: float = 3.0,
    ):
        self.inventory_provider = inventory_provider
        self.prometheus_url = prometheus_url.rstrip("/")
        self.prometheus_token = prometheus_token
        self.prometheus_username = prometheus_username
        self.prometheus_password = prometheus_password
        self.loki_url = loki_url.rstrip("/")
        self.loki_token = loki_token
        self.loki_tenant_id = loki_tenant_id
        self.loki_username = loki_username
        self.loki_password = loki_password
        self.timeout = timeout_seconds

    def execute(self, incident_id: str, tool_name: str, parameters: Dict[str, Any]) -> ActionResult:
        if tool_name == "lookup_server":
            query = parameters.get("query") or parameters.get("ip") or parameters.get("hostname") or ""
            if not self.inventory_provider:
                return ActionResult(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    success=False,
                    output="서버 인벤토리 카탈로그가 설정되지 않았습니다."
                )

            node = self.inventory_provider.get_by_ip(query) or self.inventory_provider.get_by_hostname(query)
            if not node:
                nodes = self.inventory_provider.search(query, limit=3)
                if nodes:
                    summaries = "\n---\n".join(n.to_summary() for n in nodes)
                    return ActionResult(
                        incident_id=incident_id,
                        tool_name=tool_name,
                        success=True,
                        output=f"[서버 인벤토리 검색 결과 ({len(nodes)}건)]\n{summaries}"
                    )
                return ActionResult(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    success=True,
                    output=f"'{query}'에 해당하는 서버를 인벤토리에서 찾지 못했습니다."
                )

            return ActionResult(
                incident_id=incident_id,
                tool_name=tool_name,
                success=True,
                output=f"[서버 인벤토리 조회 결과]\n{node.to_summary()}"
            )

        elif tool_name == "run_diagnostic_ping":
            target = parameters.get("target") or parameters.get("url") or "http://localhost:8080/healthz"
            if not target.startswith("http://") and not target.startswith("https://"):
                target = f"http://{target}"

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    start_time = datetime.datetime.now()
                    resp = client.get(target)
                    elapsed_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)

                    output = (
                        f"[Healthcheck Ping 결과]\n"
                        f"- 대상: {target}\n"
                        f"- 응답 코드: {resp.status_code} {resp.reason_phrase}\n"
                        f"- 응답 지연: {elapsed_ms}ms"
                    )
                    success = resp.status_code < 400
                    return ActionResult(incident_id=incident_id, tool_name=tool_name, success=success, output=output)
            except httpx.TimeoutException:
                return ActionResult(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    success=False,
                    output=f"[Healthcheck Ping 타임아웃 ({self.timeout}s 초과)]: {target}"
                )
            except Exception as e:
                return ActionResult(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    success=False,
                    output=f"[Healthcheck Ping 연결 실패 ({type(e).__name__})]: {target}"
                )

        elif tool_name == "get_recent_logs":
            query = parameters.get("query") or f'{{app="{parameters.get("service", "unknown")}"}}'
            lines = min(int(parameters.get("lines", 20)), 30)

            headers = {}
            if self.loki_token:
                headers["Authorization"] = f"Bearer {self.loki_token}"
            elif self.loki_username and self.loki_password:
                import base64
                auth_str = f"{self.loki_username}:{self.loki_password}"
                encoded = base64.b64encode(auth_str.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
            if self.loki_tenant_id:
                headers["X-Scope-OrgID"] = self.loki_tenant_id

            now = datetime.datetime.now(datetime.timezone.utc)
            start = now - datetime.timedelta(minutes=15)
            params = {
                "query": query,
                "limit": lines,
                "start": str(int(start.timestamp() * 1e9)),
                "end": str(int(now.timestamp() * 1e9)),
                "direction": "backward",
            }

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(f"{self.loki_url}/loki/api/v1/query_range", params=params, headers=headers)
                    if resp.status_code in (401, 403):
                        logger.error(f"Loki 인증 만료 또는 권한 오류 (HTTP {resp.status_code}): {self.loki_url}")
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=False,
                            output=f"[Loki 인증 오류: HTTP {resp.status_code} (토큰 만료/권한 부족) / 로컬 폴백 모드]"
                        )
                    if resp.status_code != 200:
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=False,
                            output=f"[Loki 응답 오류: HTTP {resp.status_code} - 폴백 모드]"
                        )

                    data = resp.json().get("data", {})
                    results = data.get("result", [])
                    log_lines = []
                    for stream in results:
                        for entry in stream.get("values", []):
                            log_lines.append(entry[1].strip())
                            if len(log_lines) >= lines:
                                break
                        if len(log_lines) >= lines:
                            break

                    if not log_lines:
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=True,
                            output=f"[Loki 최근 로그: 매칭 내역 없음 (`{query}`)]"
                        )

                    output = f"[Loki 실측 최근 로그 ({len(log_lines)}건 / 쿼리: `{query}`)]\n" + "\n".join(f"- {l}" for l in log_lines)
                    return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)
            except Exception as e:
                return ActionResult(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    success=False,
                    output=f"[Loki 로그 수집 실패 ({type(e).__name__}) / 폴백 모드]"
                )

        elif tool_name == "check_metrics_trend":
            query = parameters.get("query") or parameters.get("metric_name") or "up"
            duration = int(parameters.get("duration_minutes", 5))

            headers = {}
            if self.prometheus_token:
                headers["Authorization"] = f"Bearer {self.prometheus_token}"
            elif self.prometheus_username and self.prometheus_password:
                import base64
                auth_str = f"{self.prometheus_username}:{self.prometheus_password}"
                encoded = base64.b64encode(auth_str.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

            now = datetime.datetime.now(datetime.timezone.utc)
            start = now - datetime.timedelta(minutes=duration)
            params = {
                "query": query,
                "start": str(start.timestamp()),
                "end": str(now.timestamp()),
                "step": "15s",
            }

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(f"{self.prometheus_url}/api/v1/query_range", params=params, headers=headers)
                    if resp.status_code in (401, 403):
                        logger.error(f"Prometheus 인증 만료 또는 권한 오류 (HTTP {resp.status_code}): {self.prometheus_url}")
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=False,
                            output=f"[Prometheus 인증 오류: HTTP {resp.status_code} (토큰 만료/권한 부족) / 로컬 폴백 모드]"
                        )
                    if resp.status_code != 200:
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=False,
                            output=f"[Prometheus 응답 오류: HTTP {resp.status_code} - 폴백 모드]"
                        )

                    data = resp.json().get("data", {})
                    results = data.get("result", [])
                    if not results:
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=True,
                            output=f"[Prometheus 추세: 최근 {duration}분간 지표 없음 (`{query}`)]"
                        )

                    first_series = results[0]
                    values = first_series.get("values", [])
                    if not values:
                        return ActionResult(
                            incident_id=incident_id,
                            tool_name=tool_name,
                            success=True,
                            output=f"[Prometheus 추세: 최근 {duration}분간 수집 데이터 없음]"
                        )

                    start_val = float(values[0][1])
                    end_val = float(values[-1][1])
                    diff = end_val - start_val
                    change_rate = ((diff / start_val) * 100) if start_val != 0 else 0.0

                    output = (
                        f"[Prometheus 실측 추세: `{query}` ({duration}분간)]\n"
                        f"- 시작값: {start_val:.2f} -> 현재값: {end_val:.2f} (변동폭: {diff:+.2f}, {change_rate:+.1f}%)"
                    )
                    return ActionResult(incident_id=incident_id, tool_name=tool_name, success=True, output=output)
            except Exception as e:
                return ActionResult(
                    incident_id=incident_id,
                    tool_name=tool_name,
                    success=False,
                    output=f"[Prometheus 메트릭 수집 실패 ({type(e).__name__}) / 폴백 모드]"
                )

        elif tool_name == "inspect_pod_status":
            # k8s 파드 상태 읽기 전용 가이드
            return ActionResult(
                incident_id=incident_id,
                tool_name=tool_name,
                success=True,
                output="[안내] k8s 클러스터 접근은 읽기 전용 진단 모드로만 지원됩니다. 터미널에서 `kubectl get pods -l app=<service>`로 상세 이벤트를 확인하십시오."
            )

        return ActionResult(
            incident_id=incident_id,
            tool_name=tool_name,
            success=False,
            output=f"Unknown tool name: {tool_name}"
        )
