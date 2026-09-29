import datetime
import logging
from abc import ABC, abstractmethod
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# 비침습 관측성 규격(ADR-02): 외부 시스템에 부하를 주지 않도록 모든 텔레메트리 호출은 timeout 3초 및 로그 30줄 제한 강제
# 장애 격리: Prometheus나 Loki가 다운되거나 응답이 없어도 봇이 크래시되지 않고 안전한 폴백 텍스트 반환

class TelemetryClient(ABC):
    @abstractmethod
    async def query_metrics_trend(self, query: str, duration_minutes: int = 5) -> str:
        """Prometheus 호환 시계열 지표 추세 조회"""
        pass

    @abstractmethod
    async def query_recent_logs(self, query: str, limit: int = 20) -> str:
        """Loki 호환 최근 에러 로그 조회"""
        pass


class RealTelemetryClient(TelemetryClient):
    def __init__(
        self,
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

    def _prom_headers(self) -> dict:
        headers = {}
        if self.prometheus_token:
            headers["Authorization"] = f"Bearer {self.prometheus_token}"
        elif self.prometheus_username and self.prometheus_password:
            import base64
            auth_str = f"{self.prometheus_username}:{self.prometheus_password}"
            encoded = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        return headers

    def _loki_headers(self) -> dict:
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
        return headers

    async def query_metrics_trend(self, query: str, duration_minutes: int = 5) -> str:
        """Prometheus /api/v1/query_range를 호출하여 최근 지표 추세를 요약합니다."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now - datetime.timedelta(minutes=duration_minutes)

        params = {
            "query": query,
            "start": str(start.timestamp()),
            "end": str(now.timestamp()),
            "step": "15s",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.prometheus_url}/api/v1/query_range",
                    params=params,
                    headers=self._prom_headers(),
                )
                if resp.status_code in (401, 403):
                    logger.error(f"Prometheus 인증 만료 또는 권한 오류 (HTTP {resp.status_code}): {self.prometheus_url}")
                    return f"[Prometheus 인증 오류: HTTP {resp.status_code} (토큰 만료/권한 부족) / 로컬 폴백 모드]"
                if resp.status_code != 200:
                    return f"[Prometheus 응답 오류: HTTP {resp.status_code} - 기본 폴백 모드]"

                data = resp.json().get("data", {})
                results = data.get("result", [])
                if not results:
                    return f"[Prometheus 추세: 최근 {duration_minutes}분간 해당 쿼리 지표 없음 (`{query}`)]"

                first_series = results[0]
                values = first_series.get("values", [])
                if not values:
                    return f"[Prometheus 추세: 최근 {duration_minutes}분간 수집 데이터 없음]"

                start_val = float(values[0][1])
                end_val = float(values[-1][1])
                diff = end_val - start_val
                change_rate = ((diff / start_val) * 100) if start_val != 0 else 0.0

                metric_labels = first_series.get("metric", {})
                label_desc = ", ".join(f"{k}={v}" for k, v in list(metric_labels.items())[:3])

                return (
                    f"[Prometheus 실측 추세: `{query}` ({duration_minutes}분간)]\n"
                    f"- 대상: {label_desc or '기본 타깃'}\n"
                    f"- 시작값: {start_val:.2f} -> 현재값: {end_val:.2f} (변동폭: {diff:+.2f}, {change_rate:+.1f}%)\n"
                    f"- 총 데이터 포인트: {len(values)}개 (15초 간격)"
                )

        except httpx.TimeoutException:
            logger.warning(f"Prometheus 지표 수집 타임아웃 ({self.timeout}s 초과): {query}")
            return f"[Prometheus 지표 수집 타임아웃({self.timeout}s 초과) / 기본 폴백 모드 전환]"
        except Exception as e:
            logger.warning(f"Prometheus 지표 수집 실패 ({e}): {query}")
            return f"[Prometheus 지표 수집 실패({type(e).__name__}) / 기본 폴백 모드 전환]"

    async def query_recent_logs(self, query: str, limit: int = 20) -> str:
        """Loki /loki/api/v1/query_range를 호출하여 최근 로그를 수집합니다. (최대 30줄 강제)"""
        safe_limit = min(max(1, limit), 30)
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now - datetime.timedelta(minutes=15)

        params = {
            "query": query,
            "limit": safe_limit,
            "start": str(int(start.timestamp() * 1e9)),
            "end": str(int(now.timestamp() * 1e9)),
            "direction": "backward",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.loki_url}/loki/api/v1/query_range",
                    params=params,
                    headers=self._loki_headers(),
                )
                if resp.status_code in (401, 403):
                    logger.error(f"Loki 인증 만료 또는 권한 오류 (HTTP {resp.status_code}): {self.loki_url}")
                    return f"[Loki 인증 오류: HTTP {resp.status_code} (토큰 만료/권한 부족) / 로컬 폴백 모드]"
                if resp.status_code != 200:
                    return f"[Loki 응답 오류: HTTP {resp.status_code} - 기본 폴백 모드]"

                data = resp.json().get("data", {})
                results = data.get("result", [])
                if not results:
                    return f"[Loki 로그: 최근 15분간 매칭 로그 없음 (`{query}`)]"

                log_lines = []
                for stream in results:
                    for entry in stream.get("values", []):
                        # entry format: [timestamp_ns, line_string]
                        line = entry[1].strip()
                        log_lines.append(line)
                        if len(log_lines) >= safe_limit:
                            break
                    if len(log_lines) >= safe_limit:
                        break

                formatted_logs = "\n".join(f"- {line}" for line in log_lines)
                return (
                    f"[Loki 실측 최근 로그 (최근 {len(log_lines)}건 / 쿼리: `{query}`)]\n"
                    f"{formatted_logs}"
                )

        except httpx.TimeoutException:
            logger.warning(f"Loki 로그 수집 타임아웃 ({self.timeout}s 초과): {query}")
            return f"[Loki 로그 수집 타임아웃({self.timeout}s 초과) / 기본 폴백 모드 전환]"
        except Exception as e:
            logger.warning(f"Loki 로그 수집 실패 ({e}): {query}")
            return f"[Loki 로그 수집 실패({type(e).__name__}) / 기본 폴백 모드 전환]"


class MockTelemetryClient(TelemetryClient):
    """오프라인 시뮬레이션 및 테스트용 모의 텔레메트리 클라이언트"""

    async def query_metrics_trend(self, query: str, duration_minutes: int = 5) -> str:
        return (
            f"[Prometheus Mock Trend: `{query}` ({duration_minutes}분간)]\n"
            f"- 5m ago: 42% (Normal)\n"
            f"- 1m ago: 98% (Saturated, active thread queueing: 34 requests)\n"
            f"- Slope: +11.2% per minute"
        )

    async def query_recent_logs(self, query: str, limit: int = 20) -> str:
        return (
            f"[Loki Mock Log Snapshot: `{query}` (Last {min(limit, 30)} lines)]\n"
            f"2026-09-09 23:00:12 [ERROR] Connection pool exhausted: active=50, idle=0, max=50\n"
            f"2026-09-09 23:00:15 [WARN] Request timeout on /api/v1/checkout after 5000ms\n"
            f"2026-09-09 23:00:18 [ERROR] HikariPool-1 - Connection is not available, request timed out\n"
            f"2026-09-09 23:00:20 [FATAL] Critical failure: DB deadlocks suspected on orders table"
        )
