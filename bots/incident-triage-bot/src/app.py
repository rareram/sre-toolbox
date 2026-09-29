import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from src.models import (
    IncidentStatus, ChatMessage, ActionButton, TriageResponse, ActionResult
)
from src.storage import SqliteRepository
from src.correlation import CorrelationEngine
from src.catalog import CsvInventoryProvider
from src.telemetry import RealTelemetryClient, MockTelemetryClient
from src.tools import RealToolRunner, MockToolRunner
from src.enricher import ContextEnricher, EnrichedContext
from src.triage_agent import TriageAgent
from src.config import config

# 리소스 재사용: 모듈 전역 바인딩으로 요청마다 발생하는 객체 생성 오버헤드 방지
# 단순화(ponytail): DI 프레임워크 대신 파이썬 모듈 전역 인스턴스 활용

DB_PATH = config.db_path
WINDOW_SEC = config.correlation_window_seconds
MAX_IDLE_SEC = config.incident_max_idle_seconds

repo = SqliteRepository(DB_PATH)
correlation_engine = CorrelationEngine(repo, window_seconds=WINDOW_SEC, max_idle_seconds=MAX_IDLE_SEC)
inventory_provider = CsvInventoryProvider(config.inventory_file_path)

# 환경변수에 따라 실측 텔레메트리 / 도구 러너 또는 모의 객체 바인딩
use_real_telemetry = os.getenv("USE_REAL_TELEMETRY", "false").lower() == "true"
use_real_tools = os.getenv("USE_REAL_TOOLS", "false").lower() == "true"

if use_real_telemetry:
    telemetry_client = RealTelemetryClient(
        prometheus_url=config.observability.prometheus_url,
        prometheus_token=config.observability.prometheus_bearer_token,
        prometheus_username=config.observability.prometheus_username,
        prometheus_password=config.observability.prometheus_password,
        loki_url=config.observability.loki_url,
        loki_token=config.observability.loki_bearer_token,
        loki_tenant_id=config.observability.loki_tenant_id,
        loki_username=config.observability.loki_username,
        loki_password=config.observability.loki_password,
    )
else:
    telemetry_client = MockTelemetryClient()

context_enricher = ContextEnricher(catalog=inventory_provider, telemetry=telemetry_client)

if use_real_tools:
    tool_runner = RealToolRunner(
        inventory_provider=inventory_provider,
        prometheus_url=config.observability.prometheus_url,
        prometheus_token=config.observability.prometheus_bearer_token,
        prometheus_username=config.observability.prometheus_username,
        prometheus_password=config.observability.prometheus_password,
        loki_url=config.observability.loki_url,
        loki_token=config.observability.loki_bearer_token,
        loki_tenant_id=config.observability.loki_tenant_id,
        loki_username=config.observability.loki_username,
        loki_password=config.observability.loki_password,
    )
else:
    tool_runner = MockToolRunner(inventory_provider=inventory_provider)

triage_agent = TriageAgent(
    base_url=config.llm.base_url,
    api_key=config.llm.api_key,
    model=config.llm.model
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 수명주기 훅: 서버 시작/종료 시 리소스 초기화 및 커넥션 정리
    yield

app = FastAPI(
    title="Incident Triage Bot",
    description="Interactive SRE Incident Triage and Playbook Guidance Engine",
    version="0.1.0",
    lifespan=lifespan
)

class ChatRequest(BaseModel):
    incident_id: str
    message: str

class ActionExecRequest(BaseModel):
    incident_id: str
    tool_name: str
    parameters: Dict[str, Any] = {}

class StatusUpdateRequest(BaseModel):
    status: IncidentStatus

@app.get("/healthz")
async def healthz():
    # k8s 프로브 연동: 봇 동작에 필요한 DB 파일 및 LLM 설정 정상 여부 확인 응답
    return {
        "status": "ok",
        "database": DB_PATH,
        "llm_model": triage_agent.model,
        "correlation_window_seconds": WINDOW_SEC,
        "use_real_telemetry": use_real_telemetry,
        "use_real_tools": use_real_tools
    }

@app.post("/webhook/grafana")
async def webhook_grafana(request: Request):
    # Grafana 웹훅 수신: 알람 수집 후 연관 분석 엔진(Correlation)으로 전달하여 신규/기존 장애 판별
    payload = await request.json()
    alerts = payload.get("alerts", [])
    if not alerts:
        # 단일 알람 페이로드 대응
        alerts = [payload]

    processed_results = []
    for raw_alert in alerts:
        incident, alert_event, is_new = correlation_engine.process_alert(raw_alert)

        processed_results.append({
            "incident_id": incident.incident_id,
            "service_name": incident.service_name,
            "alertname": alert_event.alertname,
            "is_new_incident": is_new,
            "total_alerts_count": len(incident.alerts),
            "status": incident.current_status.value
        })

    return {"status": "processed", "results": processed_results}

@app.post("/api/chat", response_model=TriageResponse)
async def chat_with_triage_bot(chat_req: ChatRequest):
    # 대화형 분석: 누적 알람 및 기수행 점검 데이터를 바탕으로 Fact/Hypothesis 및 추천 버튼 도출
    incident = repo.get_incident(chat_req.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {chat_req.incident_id} not found")

    user_msg = ChatMessage(incident_id=chat_req.incident_id, sender="user", content=chat_req.message)
    repo.save_chat_message(user_msg)

    # 1. 단축 인터셉터: 긴급 서버 정보 조회 (/server <ip|host>, /lookup <query>, /서버 <query>)
    raw_text = chat_req.message.strip()
    lower_text = raw_text.lower()
    is_shortcut = (
        lower_text.startswith("/server ") or
        lower_text.startswith("/lookup ") or
        raw_text.startswith("/서버 ")
    )

    if is_shortcut:
        # LLM을 거치지 않고 O(1) 인메모리 카탈로그에서 즉시 검색하여 0.01초 내 반환
        parts = raw_text.split(maxsplit=1)
        query = parts[1].strip() if len(parts) > 1 else ""

        node = inventory_provider.get_by_ip(query) or inventory_provider.get_by_hostname(query)
        if not node and query:
            searched = inventory_provider.search(query, limit=3)
            if searched:
                node = searched[0]

        if node:
            reply_text = f"[서버 인벤토리 조회 결과]\n{node.to_summary()}"
            fact_summary = f"서버 '{node.hostname}' ({node.ip}) 카탈로그 조회 성공"
            hypothesis = f"소속 서비스: {node.service if hasattr(node, 'service') else node.role}, 역할: {node.role}, 물리 위치: {node.location}"
            actions = [
                ActionButton(label=f"인벤토리 상세 확인 ({node.hostname})", tool_name="lookup_server", parameters={"query": node.ip}),
                ActionButton(label=f"점검 핑 실행 ({node.ip})", tool_name="run_diagnostic_ping", parameters={"target": f"http://{node.ip}:8080/healthz"}),
            ]
        else:
            reply_text = f"'{query}'에 해당하는 서버를 인벤토리 카탈로그에서 찾을 수 없습니다."
            fact_summary = f"서버 '{query}' 인벤토리 검색 결과 없음"
            hypothesis = "미등록 장비이거나 입력 정보 확인이 필요합니다."
            actions = [
                ActionButton(label="최근 에러 로그 확인", tool_name="get_recent_logs", parameters={"lines": 20})
            ]

        response = TriageResponse(
            incident_id=chat_req.incident_id,
            fact_summary=fact_summary,
            hypothesis=hypothesis,
            recommended_actions=actions,
            reply_text=reply_text
        )
        bot_msg = ChatMessage(incident_id=chat_req.incident_id, sender="bot", content=response.reply_text)
        repo.save_chat_message(bot_msg)
        return response

    # 2. 일반 자연어 질의: 선제적 컨텍스트 수집(인벤토리 + 실측 P99/로그) 결합 및 LLM 추론
    history = repo.get_chat_history(chat_req.incident_id, limit=6)
    action_results = repo.get_action_results(chat_req.incident_id)

    enriched = None
    if incident.alerts:
        latest_alert = incident.alerts[-1]
        enriched = await context_enricher.enrich(latest_alert, incident.service_name)

    response = await triage_agent.analyze_and_respond(
        incident=incident,
        user_message=chat_req.message,
        chat_history=history,
        action_results=action_results,
        enriched_context=enriched
    )

    bot_msg = ChatMessage(incident_id=chat_req.incident_id, sender="bot", content=response.reply_text)
    repo.save_chat_message(bot_msg)

    return response

@app.post("/api/action", response_model=ActionResult)
async def execute_action(action_req: ActionExecRequest):
    # 점검 액션 안전 실행: 검증된 읽기 전용 도구 실행 및 결과를 SQLite에 저장 (LLM 후속 참조)
    incident = repo.get_incident(action_req.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {action_req.incident_id} not found")

    result = tool_runner.execute(
        incident_id=action_req.incident_id,
        tool_name=action_req.tool_name,
        parameters=action_req.parameters
    )
    repo.save_action_result(result)
    return result

@app.get("/api/incidents/{incident_id}")
async def get_incident_details(incident_id: str):
    # 장애 컨텍스트 조회: 알람 타임라인, 대화 이력, 점검 도구 결과를 한 번에 묶어서 반환
    incident = repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    history = repo.get_chat_history(incident_id, limit=50)
    action_results = repo.get_action_results(incident_id)

    return {
        "incident": incident,
        "chat_history": history,
        "action_results": action_results
    }

@app.post("/api/incidents/{incident_id}/status")
async def update_incident_status(incident_id: str, req: StatusUpdateRequest):
    # 인시던트 종료 처리: 상태를 RESOLVED로 변경하여 이후 알람이 기존 건과 섞이지 않도록 방지
    incident = repo.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    repo.update_incident_status(incident_id, req.status)
    return {"incident_id": incident_id, "updated_status": req.status.value}

@app.get("/api/catalog/search")
async def search_catalog(q: str, limit: int = 5):
    # 서버 인벤토리 키워드 부분 일치 다건 검색 엔드포인트
    results = inventory_provider.search(q, limit=limit)
    return {
        "query": q,
        "count": len(results),
        "servers": [r.to_dict() for r in results]
    }

@app.get("/api/catalog/servers/{key}")
async def get_catalog_server(key: str):
    # IP 또는 호스트명 단건 조회 엔드포인트
    node = inventory_provider.get_by_ip(key) or inventory_provider.get_by_hostname(key)
    if not node:
        raise HTTPException(status_code=404, detail=f"Server '{key}' not found in inventory")
    return node.to_dict()
