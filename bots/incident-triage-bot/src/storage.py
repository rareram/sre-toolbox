import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from src.models import Incident, AlertEvent, ChatMessage, ActionResult, IncidentStatus

# 장애 격리(Fault Isolation): 대상 시스템의 DB 장애가 봇으로 번지지 않도록 외부 DB와 독립된 로컬 SQLite 채택
# 의존성 최소화(ponytail): 무거운 ORM 대신 파이썬 내장 sqlite3를 사용하여 가볍고 빠르게 쿼리 실행

class SqliteRepository:
    def __init__(self, db_path: str = "triage.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        # DB 잠금 충돌 방지: WAL 모드로 읽기와 쓰기를 대기 없이 동시 처리하고 busy_timeout을 5초로 설정
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        # 테이블 설계 및 인덱스 추가: 서비스명과 상태 복합 인덱스를 두어 진행 중인 인시던트를 빠르게 조회
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id     TEXT PRIMARY KEY,
                    service_name    TEXT NOT NULL,
                    environment     TEXT NOT NULL,
                    current_status  TEXT NOT NULL,
                    severity        TEXT NOT NULL,
                    first_seen_at   TEXT NOT NULL,
                    last_updated_at TEXT NOT NULL,
                    summary         TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_incidents_service_status 
                ON incidents(service_name, current_status);

                CREATE TABLE IF NOT EXISTS alert_events (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id      TEXT NOT NULL,
                    fingerprint      TEXT NOT NULL,
                    alertname        TEXT NOT NULL,
                    status           TEXT NOT NULL,
                    labels_json      TEXT NOT NULL,
                    annotations_json TEXT NOT NULL,
                    received_at      TEXT NOT NULL,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_alerts_incident 
                ON alert_events(incident_id);

                CREATE TABLE IF NOT EXISTS chat_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    sender      TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS action_results (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    tool_name   TEXT NOT NULL,
                    success     INTEGER NOT NULL,
                    output      TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id) ON DELETE CASCADE
                );
            """)

    def save_incident(self, incident: Incident):
        # 멱등성 보장: UPSERT(ON CONFLICT) 구문 적용으로 키 충돌 방지 및 최신 상태/시각 갱신
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO incidents (
                    incident_id, service_name, environment, current_status,
                    severity, first_seen_at, last_updated_at, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    current_status = excluded.current_status,
                    severity = excluded.severity,
                    last_updated_at = excluded.last_updated_at,
                    summary = COALESCE(excluded.summary, incidents.summary)
            """, (
                incident.incident_id,
                incident.service_name,
                incident.environment,
                incident.current_status.value,
                incident.severity,
                incident.first_seen_at.isoformat(),
                incident.last_updated_at.isoformat(),
                incident.summary
            ))

    def add_alert_to_incident(self, incident_id: str, alert: AlertEvent):
        # 알람 추가 및 시각 갱신: 단일 트랜잭션으로 알람을 저장하고 인시던트의 최종 변경 시각을 함께 업데이트
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO alert_events (
                    incident_id, fingerprint, alertname, status,
                    labels_json, annotations_json, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_id,
                alert.fingerprint,
                alert.alertname,
                alert.status,
                json.dumps(alert.labels, ensure_ascii=False),
                json.dumps(alert.annotations, ensure_ascii=False),
                alert.received_at.isoformat()
            ))
            conn.execute("""
                UPDATE incidents 
                SET last_updated_at = ? 
                WHERE incident_id = ?
            """, (now_str, incident_id))

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        # 쿼리 효율화: 인시던트 정보와 연관된 알람 목록을 한 번에 읽어와 객체로 변환
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
            if not row:
                return None

            alert_rows = conn.execute(
                "SELECT * FROM alert_events WHERE incident_id = ? ORDER BY id ASC", (incident_id,)
            ).fetchall()

            alerts = [
                AlertEvent(
                    fingerprint=a["fingerprint"],
                    alertname=a["alertname"],
                    status=a["status"],
                    labels=json.loads(a["labels_json"]),
                    annotations=json.loads(a["annotations_json"]),
                    received_at=datetime.fromisoformat(a["received_at"])
                )
                for a in alert_rows
            ]

            return Incident(
                incident_id=row["incident_id"],
                service_name=row["service_name"],
                environment=row["environment"],
                current_status=IncidentStatus(row["current_status"]),
                severity=row["severity"],
                first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
                last_updated_at=datetime.fromisoformat(row["last_updated_at"]),
                summary=row["summary"],
                alerts=alerts
            )

    def find_active_incident_by_service(
        self, service_name: str, max_idle_seconds: Optional[int] = None
    ) -> Optional[Incident]:
        # 중복 인시던트 방지 및 좀비 세션 차단: 미해결 인시던트 중 유휴 시간(max_idle_seconds) 이내인 최신 건 조회
        with self._get_connection() as conn:
            if max_idle_seconds is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_idle_seconds)
                row = conn.execute("""
                    SELECT incident_id FROM incidents
                    WHERE service_name = ? AND current_status != 'RESOLVED' AND last_updated_at >= ?
                    ORDER BY last_updated_at DESC LIMIT 1
                """, (service_name, cutoff.isoformat())).fetchone()
            else:
                row = conn.execute("""
                    SELECT incident_id FROM incidents
                    WHERE service_name = ? AND current_status != 'RESOLVED'
                    ORDER BY last_updated_at DESC LIMIT 1
                """, (service_name,)).fetchone()

            if not row:
                return None
            return self.get_incident(row["incident_id"])

    def save_chat_message(self, message: ChatMessage):
        # 대화 맥락 보존: LLM 전달용 이전 질문과 답변 기록 저장
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO chat_history (incident_id, sender, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                message.incident_id,
                message.sender,
                message.content,
                message.created_at.isoformat()
            ))

    def get_chat_history(self, incident_id: str, limit: int = 10) -> List[ChatMessage]:
        # 프롬프트 토큰 초과 방지: 최근 대화 N건만 가져와 시간순으로 다시 정렬
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM (
                    SELECT * FROM chat_history
                    WHERE incident_id = ?
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
            """, (incident_id, limit)).fetchall()

            return [
                ChatMessage(
                    incident_id=r["incident_id"],
                    sender=r["sender"],
                    content=r["content"],
                    created_at=datetime.fromisoformat(r["created_at"])
                )
                for r in rows
            ]

    def save_action_result(self, result: ActionResult):
        # 중복 점검 방지: 도구 실행 결과를 저장하여 LLM이 다음 분석 시 참고할 수 있도록 지원
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO action_results (
                    incident_id, tool_name, success, output, executed_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                result.incident_id,
                result.tool_name,
                1 if result.success else 0,
                result.output,
                result.executed_at.isoformat()
            ))

    def get_action_results(self, incident_id: str) -> List[ActionResult]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM action_results
                WHERE incident_id = ?
                ORDER BY id ASC
            """, (incident_id,)).fetchall()

            return [
                ActionResult(
                    incident_id=r["incident_id"],
                    tool_name=r["tool_name"],
                    success=bool(r["success"]),
                    output=r["output"],
                    executed_at=datetime.fromisoformat(r["executed_at"])
                )
                for r in rows
            ]

    def update_incident_status(self, incident_id: str, status: IncidentStatus):
        # 인시던트 종료 처리: 상태를 해결(RESOLVED)로 변경하여 이후 들어오는 알람은 새 인시던트로 분리
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE incidents
                SET current_status = ?, last_updated_at = ?
                WHERE incident_id = ?
            """, (status.value, now_str, incident_id))
