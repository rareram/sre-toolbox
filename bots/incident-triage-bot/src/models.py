from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# 인시던트 생명주기 관리: 진행 중인 장애와 종료된 장애의 알람이 섞이지 않도록 상태 변경 기준 정의
class IncidentStatus(str, Enum):
    NEW = "NEW"
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"

# 원본 알람 보존: 단일 장애 건에 여러 알람이 들어올 때 라벨 손실을 방지하고 LLM 분석 근거 확보
class AlertEvent(BaseModel):
    fingerprint: str
    alertname: str
    status: str = "firing"
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 임의 쉘 실행 방지: 미리 검증된 허용 도구와 파라미터만 실행 가능하도록 제한 (Teams 버튼 연동)
class ActionButton(BaseModel):
    label: str
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

# 섣부른 오판 방지: 확인된 사실(Fact)과 원인 추정(Hypothesis)을 모델 수준에서 명확히 분리하고 추천 액션 제공
class TriageResponse(BaseModel):
    incident_id: str
    fact_summary: str
    hypothesis: str
    recommended_actions: List[ActionButton] = Field(default_factory=list)
    reply_text: str

# 알람 피로도 완화: 같은 서비스의 알람을 시간 윈도우로 묶어 발생부터 종료까지 하나의 타임라인으로 관리
class Incident(BaseModel):
    incident_id: str
    service_name: str
    environment: str = "production"
    current_status: IncidentStatus = IncidentStatus.NEW
    severity: str = "warning"
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: Optional[str] = None
    alerts: List[AlertEvent] = Field(default_factory=list)

# 연속 대화 맥락 유지: 이전 질문과 답변 기록을 보존하여 LLM 분석 프롬프트에 반영
class ChatMessage(BaseModel):
    incident_id: str
    sender: str  # "user" 또는 "bot"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 점검 실행 이력 추적: 도구 실행 결과와 로그 원문을 저장하여 후속 대화 분석에 활용
class ActionResult(BaseModel):
    incident_id: str
    tool_name: str
    success: bool
    output: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
