import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.models import AlertEvent
from src.catalog import InventoryProvider, ServerNode
from src.telemetry import TelemetryClient

logger = logging.getLogger(__name__)

# 선제적 컨텍스트 수집(Auto-Enrichment): 알람 인입 즉시 서버 인벤토리 메타데이터와 텔레메트리를 병렬 수집
# SRE 지표 분석 원칙 반영: 증상 지표(P99 응답 시간, 에러 로그)와 원인 지표(CPU, 풀 지표)를 결합하여 제공

@dataclass
class EnrichedContext:
    server_node: Optional[ServerNode] = None
    metrics_trend: str = ""
    recent_logs: str = ""
    recent_changes: Optional[str] = None

    def to_prompt_context(self) -> str:
        """LLM 프롬프트에 주입하기 위한 통합 마크다운 블록 반환"""
        sections = []

        # 1. 서버 인벤토리 메타데이터 (위치, 역할, 담당자, 런북, 점검 명령어)
        if self.server_node:
            sections.append(f"[대상 서버 인벤토리 정보]\n{self.server_node.to_summary()}")
        else:
            sections.append("[대상 서버 인벤토리 정보]\n- 인벤토리 등록 내역 없음 (외부 또는 미등록 인스턴스)")

        # 2. 증상 및 메트릭 추세
        if self.metrics_trend:
            sections.append(f"[실측 메트릭 추세 분석]\n{self.metrics_trend}")

        # 3. 최근 에러 로그
        if self.recent_logs:
            sections.append(f"[최근 발생 에러 로그 스냅샷]\n{self.recent_logs}")

        # 4. 최근 변경 사항 (배포, 설정)
        if self.recent_changes:
            sections.append(f"[최근 30분 시스템 변경 이력]\n{self.recent_changes}")

        return "\n\n".join(sections)


class ContextEnricher:
    """
    알람 수신 시 비침습적으로 서버 인벤토리와 텔레메트리(Prometheus, Loki)를 병렬 조회하여
    트리아지에 필요한 핵심 문맥을 선제적으로 결합합니다.
    """

    def __init__(self, catalog: InventoryProvider, telemetry: TelemetryClient):
        self.catalog = catalog
        self.telemetry = telemetry

    def extract_target_host_or_ip(self, labels: Dict[str, str]) -> Optional[str]:
        """알람 라벨에서 서버 IP 또는 호스트명을 추출합니다."""
        # 라벨 우선순위: instance -> host -> node -> ip -> server
        raw_target = (
            labels.get("instance")
            or labels.get("host")
            or labels.get("node")
            or labels.get("ip")
            or labels.get("server")
        )
        if not raw_target:
            return None
        # 포트 번호 분리 (예: 10.19.20.104:9100 -> 10.19.20.104)
        return raw_target.split(":")[0].strip()

    async def enrich(
        self,
        alert: AlertEvent,
        service_name: str,
        recent_changes_hint: Optional[str] = None
    ) -> EnrichedContext:
        """
        비동기 병렬 수집(asyncio.gather)을 통해 3초 이내에 인벤토리와 텔레메트리를 묶어 반환합니다.
        """
        labels = alert.labels

        # 1. 인벤토리 카탈로그 매핑 (O(1) 인메모리 조회)
        server_node = None
        target_key = self.extract_target_host_or_ip(labels)
        if target_key:
            server_node = self.catalog.get_by_ip(target_key) or self.catalog.get_by_hostname(target_key)
            if not server_node:
                matched = self.catalog.search(target_key, limit=1)
                if matched:
                    server_node = matched[0]

        # 2. 텔레메트리 쿼리 정의 (증상 중심: P99/지연 및 에러 로그)
        # 서비스명 기반 PromQL 및 LogQL
        metric_query = labels.get("metric_query") or f'rate(http_requests_total{{app="{service_name}",status=~"5.."}}[5m])'
        log_query = labels.get("log_query") or f'{{app="{service_name}"}} |= "ERROR"'

        # 3. 비동기 병렬 수집 (asyncio.gather with return_exceptions=True)
        # 외부 시스템 하나가 타임아웃되어도 다른 작업은 정상 완료 보장
        metrics_task = self.telemetry.query_metrics_trend(metric_query, duration_minutes=5)
        logs_task = self.telemetry.query_recent_logs(log_query, limit=15)

        results = await asyncio.gather(metrics_task, logs_task, return_exceptions=True)

        metrics_res = results[0] if not isinstance(results[0], Exception) else f"[메트릭 수집 예외: {results[0]}]"
        logs_res = results[1] if not isinstance(results[1], Exception) else f"[로그 수집 예외: {results[1]}]"

        return EnrichedContext(
            server_node=server_node,
            metrics_trend=str(metrics_res),
            recent_logs=str(logs_res),
            recent_changes=recent_changes_hint
        )
