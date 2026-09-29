import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from src.models import Incident, AlertEvent, IncidentStatus
from src.storage import SqliteRepository

# 알람 폭풍 제어: 동일 서비스 알람을 시간 윈도우 기반으로 묶어 단일 인시던트로 집계 (채널 도배 방지)

class CorrelationEngine:
    def __init__(
        self,
        repo: SqliteRepository,
        window_seconds: int = 60,
        max_idle_seconds: int = 1800
    ):
        self.repo = repo
        self.window_seconds = window_seconds
        self.max_idle_seconds = max_idle_seconds

    @staticmethod
    def extract_service_name(labels: Dict[str, str]) -> str:
        # 서비스 식별자 누락 방어: 라벨 우선순위 폴백 (service -> app -> container -> job -> alertname)
        # 단순화(ponytail): 복잡한 규칙 엔진 대신 딕셔너리 get 체이닝으로 간결하게 처리
        return (
            labels.get("service")
            or labels.get("app")
            or labels.get("container")
            or labels.get("job")
            or labels.get("alertname", "unknown-service")
        )

    @staticmethod
    def generate_fingerprint(labels: Dict[str, str], alertname: str) -> str:
        # 중복 알람 감지: alertname 및 정렬된 라벨 키/값 기반 sha256 고유 해시 생성 (Flapping 감지)
        raw_key = f"{alertname}:" + ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    def process_alert(self, raw_alert: Dict[str, Any]) -> Tuple[Incident, AlertEvent, bool]:
        # 알람 인입 처리: 신규 생성(is_new=True)과 기존 건 누적(is_new=False) 플래그 분기 반환
        labels = raw_alert.get("labels", {})
        annotations = raw_alert.get("annotations", {})
        alertname = labels.get("alertname", raw_alert.get("alertname", "GenericAlert"))
        status = raw_alert.get("status", "firing")
        fingerprint = raw_alert.get("fingerprint") or self.generate_fingerprint(labels, alertname)

        service_name = self.extract_service_name(labels)
        environment = labels.get("environment", labels.get("env", "production"))
        severity = labels.get("severity", "warning")

        now = datetime.now(timezone.utc)
        alert_event = AlertEvent(
            fingerprint=fingerprint,
            alertname=alertname,
            status=status,
            labels=labels,
            annotations=annotations,
            received_at=now
        )

        # 좀비 세션 방지: 유휴 시간(max_idle_seconds) 이내에 갱신된 활성 인시던트만 조회
        active_incident = self.repo.find_active_incident_by_service(
            service_name,
            max_idle_seconds=self.max_idle_seconds
        )

        # 연쇄 알람 통합: 진행 중인 인시던트가 있으면 새 티켓 생성을 막고 기존 타임라인에 병합
        if active_incident and active_incident.current_status != IncidentStatus.RESOLVED:
            self.repo.add_alert_to_incident(active_incident.incident_id, alert_event)
            active_incident.alerts.append(alert_event)
            active_incident.last_updated_at = now
            return active_incident, alert_event, False

        # 신규 인시던트 생성: 진행 중인 장애가 없거나 이미 종료된 경우 고유 접미사(uuid)를 결합하여 생성
        today_str = now.strftime("%Y%m%d")
        time_seq = now.strftime("%H%M%S")
        suffix = uuid.uuid4().hex[:4]
        incident_id = f"INC-{today_str}-{service_name}-{time_seq}-{suffix}"

        new_incident = Incident(
            incident_id=incident_id,
            service_name=service_name,
            environment=environment,
            current_status=IncidentStatus.NEW,
            severity=severity,
            first_seen_at=now,
            last_updated_at=now,
            summary=f"[{service_name}] {alertname} 감지됨",
            alerts=[alert_event]
        )

        self.repo.save_incident(new_incident)
        self.repo.add_alert_to_incident(incident_id, alert_event)
        return new_incident, alert_event, True
