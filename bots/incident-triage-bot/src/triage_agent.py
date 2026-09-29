import json
import os
import re
from typing import List, Optional, Any
import httpx
from dotenv import load_dotenv
from src.models import Incident, ActionResult, ChatMessage, TriageResponse, ActionButton

load_dotenv()

# 진단 오판 방지: LLM 환각을 차단하기 위해 관측 지표(Fact)와 원인 가설(Hypothesis)을 엄격히 분리
# SRE 지표 분석 원칙 반영: 증상(P99/에러율)과 원인(CPU/풀) 분리, 지표 교차 해석, 복구 우선(30분 내 변경 확인)

SYSTEM_PROMPT = """너는 숙련된 Senior SRE Incident Triage Specialist이자 Co-pilot이야.
장애 상황에서 엔지니어와 자연어로 대화하며 신속하고 객관적인 1차 원인 파악 및 점검을 지원한다.

[행동 및 응답 원칙]
1. 객관적 사실과 가설의 엄격한 분리:
   - Fact: 수신된 알람 메트릭, 실제 수집된 로그 내용, 도구 점검 결과로 확인된 객관적 수치만 기술한다.
   - Hypothesis: 가설을 명확히 명시하고 근거를 제시한다. 절대 섣불리 확정 짓지 않는다.
2. 이모지 및 군더더기 금지:
   - 이모지나 이모티콘을 일체 사용하지 않는다.
   - 불필요한 인사말, 사과, 기계적인 아부를 배제하고 담백한 기술적 엔지니어링 문체로 답변한다.
3. SRE 데이터 및 지표 해석 원칙:
   - 증상(Symptom)과 원인(Cause)의 분리:
     * 사용자가 체감하는 지연 시간(P99 꼬리 지연)과 에러율이 증상이며, CPU/메모리/풀은 원인 쪽이다.
     * CPU 사용률만 보고 판단하지 마라. CPU가 20%로 한가한데 P99가 폭증한다면 스레드가 I/O나 DB 커넥션 풀 대기, 락 경합에 묶인 상태다.
   - 에러율과 응답 속도의 교차 검증:
     * 에러율이 높은데 응답이 매우 빠르다면 커넥션 거부(Connection Refused)나 널 참조 등 즉시 실패(Fast Fail) 패턴이다.
     * 에러율과 P99가 함께 치솟는다면 타임아웃으로 느리게 죽어가는 상태다.
   - 병목 범위 판단:
     * 모든 API가 동시에 느리면 공유 자원(DB, Redis 캐시, 공용 풀) 병목이다.
     * 특정 API만 느리면 해당 엔드포인트의 쿼리나 외부 연동 코드 문제다.
   - 복구 우선 원칙:
     * 최근 30분 내 배포나 설정 변경이 있었다면, 원인 규명보다 롤백 검토를 최우선 권장하라.
4. 실행 가능한 점검 도구 추천:
   - 다음 사용 가능한 도구 목록 중 현 상황에 가장 적절한 점검 도구 1~3개를 recommended_actions에 포함한다.
   - 지원 도구:
     * `get_recent_logs`: 파라미터 `{"lines": 20, "service": "..."}`
     * `check_metrics_trend`: 파라미터 `{"metric_name": "db_connection_usage"}`
     * `lookup_server`: 파라미터 `{"query": "IP 또는 호스트명"}`
     * `run_diagnostic_ping`: 파라미터 `{"target": "http://..."}`
     * `inspect_pod_status`: 파라미터 `{}`

반드시 아래 JSON 포맷으로만 응답하라:
{
  "fact_summary": "현재 수집된 로그와 알람으로 확인된 객관적 사실",
  "hypothesis": "추정되는 근본 원인 가설 및 추가 검증이 필요한 지점",
  "recommended_actions": [
    {
      "label": "버튼에 표시될 간결한 텍스트 (예: DB 커넥션 풀 추세 확인)",
      "tool_name": "도구명",
      "parameters": {"param": "value"}
    }
  ],
  "reply_text": "엔지니어 질문에 대한 구체적이고 전문적인 답변 및 안내"
}
"""

class TriageAgent:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "ollama")
        self.model = model or os.getenv("LLM_MODEL", "gemma4:e4b-mlx")

    @staticmethod
    def _clean_json_output(raw_text: str) -> dict:
        # 마크다운 코드블록 제거: 응답 앞뒤 백틱(```json)을 정규식으로 제거하고 JSON으로 파싱
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 부분 JSON 매칭 시도: 중괄호 블록 추출
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # 최후의 안전 폴백: 파싱 실패 시 원본을 reply_text로 감싼 기본 구조 반환
            return {
                "fact_summary": "LLM 응답 JSON 파싱 실패로 기본 텍스트로 폴백합니다.",
                "hypothesis": "추가 도구 점검이 필요합니다.",
                "recommended_actions": [
                    {
                        "label": "최근 에러 로그 재확인",
                        "tool_name": "get_recent_logs",
                        "parameters": {"lines": 20}
                    }
                ],
                "reply_text": cleaned
            }

    async def analyze_and_respond(
        self,
        incident: Incident,
        user_message: str,
        chat_history: List[ChatMessage],
        action_results: List[ActionResult],
        enriched_context: Optional[Any] = None
    ) -> TriageResponse:
        # 장애 컨텍스트 조립: 인벤토리, 텔레메트리, 알람 이력, 점검 결과, 대화 내역을 취합하여 프롬프트 구성

        enrich_prompt = ""
        if enriched_context and hasattr(enriched_context, "to_prompt_context"):
            enrich_prompt = f"\n[선제 수집된 컨텍스트 (인벤토리 & 실측 텔레메트리)]:\n{enriched_context.to_prompt_context()}\n"

        alerts_context = "\n".join([
            f"- [{a.received_at.strftime('%H:%M:%S')}] {a.alertname} (상태: {a.status}) 라벨: {json.dumps(a.labels, ensure_ascii=False)}"
            for a in incident.alerts
        ]) or "수신된 알람 없음"

        tool_context = "\n".join([
            f"[도구 실행: {r.tool_name}] 결과:\n{r.output}"
            for r in action_results
        ]) or "아직 실행된 점검 도구 없음"

        history_context = "\n".join([
            f"{m.sender.upper()}: {m.content}"
            for m in chat_history
        ]) or "이전 대화 없음"

        user_prompt = f"""[인시던트 ID]: {incident.incident_id}
[대상 서비스]: {incident.service_name} (환경: {incident.environment}, 심각도: {incident.severity})
{enrich_prompt}
[1. 누적 수신 알람 이력]:
{alerts_context}

[2. 이전 점검 도구 실행 결과]:
{tool_context}

[3. 최근 대화 내역]:
{history_context}

[엔지니어의 현재 질문 / 요청]:
{user_message}
"""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.2,
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                raw_output = data["choices"][0]["message"]["content"]
            except Exception as e:
                err_detail = f"{type(e).__name__}: {str(e)}"
                return TriageResponse(
                    incident_id=incident.incident_id,
                    fact_summary=f"LLM 통신 오류 발생: {err_detail}",
                    hypothesis="LLM 엔드포인트 응답성 점검 필요",
                    recommended_actions=[
                        ActionButton(label="서비스 파드 상태 점검", tool_name="inspect_pod_status", parameters={})
                    ],
                    reply_text=f"현재 LLM 서비스에 연결할 수 없습니다. 수동 점검 도구를 활용하십시오. (에러: {err_detail})"
                )

        parsed = self._clean_json_output(raw_output)
        action_buttons = [
            ActionButton(
                label=act.get("label", "점검 실행"),
                tool_name=act.get("tool_name", "inspect_pod_status"),
                parameters=act.get("parameters", {})
            )
            for act in parsed.get("recommended_actions", [])
        ]

        return TriageResponse(
            incident_id=incident.incident_id,
            fact_summary=parsed.get("fact_summary", "확인된 사실 요약 없음"),
            hypothesis=parsed.get("hypothesis", "추정 가설 없음"),
            recommended_actions=action_buttons,
            reply_text=parsed.get("reply_text", raw_output)
        )
