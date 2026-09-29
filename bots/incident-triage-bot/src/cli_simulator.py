import asyncio
import sys
from datetime import datetime
from src.models import IncidentStatus, ActionButton
from src.storage import SqliteRepository
from src.correlation import CorrelationEngine
from src.tools import MockToolRunner
from src.triage_agent import TriageAgent
from src.config import config

# 외부 인프라 의존성 분리: 외부 네트워크 터널링 없이 로컬 터미널에서 대화 및 점검 루프 검증
# 단순화(ponytail): 로컬 SQLite 환경만으로 전체 시나리오 시뮬레이션 완결

async def run_simulator():
    repo = SqliteRepository("triage_sim.db")
    engine = CorrelationEngine(repo, window_seconds=config.correlation_window_seconds)
    tools = MockToolRunner()
    agent = TriageAgent(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        model=config.llm.model
    )

    print("=" * 70)
    print("SRE Incident Triage Bot - Interactive Terminal Simulator")
    print("=" * 70)
    print("1. [모의 알람 주입] payment-api DB 커넥션 풀 고갈 알람 2건 연속 발생 시뮬레이션")
    
    # 1차 알람 발생: Warning 임계치 초과 모의 알람 주입 (신규 인시던트 생성 확인)
    raw_alert_1 = {
        "status": "firing",
        "labels": {
            "alertname": "DBConnectionPoolWarning",
            "service": "payment-api",
            "severity": "warning",
            "environment": "production"
        },
        "annotations": {
            "summary": "DB connection pool usage over 80% for 2 mins"
        }
    }
    incident, alert1, is_new = engine.process_alert(raw_alert_1)
    print(f"\n[알람 수신 1] 인시던트 발급: {incident.incident_id} (신규: {is_new})")

    # 연속 알람 발생: 윈도우 시간 내 Critical 알람 수신 (동일 인시던트 병합 확인)
    raw_alert_2 = {
        "status": "firing",
        "labels": {
            "alertname": "DBDeadlockDetected",
            "service": "payment-api",
            "severity": "critical",
            "environment": "production"
        },
        "annotations": {
            "summary": "Deadlocks detected on orders table, transactions failing"
        }
    }
    incident, alert2, is_new = engine.process_alert(raw_alert_2)
    print(f"[알람 수신 2] 후속 알람 병합 완료 (누적 알람 수: {len(incident.alerts)}, 신규 인시던트 생성 방지됨)")

    print("\n" + "-" * 70)
    print("봇과의 자연어 대화가 시작됩니다. 질문을 입력하거나 번호를 선택하십시오. (종료: 'q')")
    print("-" * 70)

    # 초기 상황 분석: 인시던트 요약 및 1차 점검 액션 버튼 제시
    initial_resp = await agent.analyze_and_respond(
        incident=incident,
        user_message="현재 상황 요약과 1차 점검 액션을 제안해줘.",
        chat_history=[],
        action_results=[]
    )

    current_actions = initial_resp.recommended_actions

    def display_response(resp):
        print(f"\n[BOT 트리아지 리포트]")
        print(f"- 사실 (Fact): {resp.fact_summary}")
        print(f"- 가설 (Hypothesis): {resp.hypothesis}")
        print(f"\n[BOT 답변]\n{resp.reply_text}\n")
        if resp.recommended_actions:
            print("[추천 점검 액션 (버튼)]:")
            for idx, act in enumerate(resp.recommended_actions, 1):
                print(f"  [{idx}] {act.label} (도구: {act.tool_name})")

    display_response(initial_resp)

    while True:
        try:
            user_input = input("\n[엔지니어] > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input or user_input.lower() == "q":
            print("\n시뮬레이터를 종료합니다.")
            break

        # 버튼 클릭 시뮬레이션: 번호 입력 시 추천 점검 도구 실행 및 결과 저장
        if user_input.isdigit() and 1 <= int(user_input) <= len(current_actions):
            selected_action = current_actions[int(user_input) - 1]
            print(f"\n[액션 실행] {selected_action.label} ...")
            action_res = tools.execute(
                incident_id=incident.incident_id,
                tool_name=selected_action.tool_name,
                parameters=selected_action.parameters
            )
            repo.save_action_result(action_res)
            print(f"[실행 결과]\n{action_res.output}")

            # 점검 결과 기반 후속 질문: 도구 실행 출력을 컨텍스트로 2차 분석 요청
            prompt_msg = f"'{selected_action.label}' 도구를 실행한 결과입니다. 이를 바탕으로 원인을 다시 분석하고 다음 점검 단계를 제안해줘."
            resp = await agent.analyze_and_respond(
                incident=incident,
                user_message=prompt_msg,
                chat_history=repo.get_chat_history(incident.incident_id, limit=6),
                action_results=repo.get_action_results(incident.incident_id)
            )
            current_actions = resp.recommended_actions
            display_response(resp)
        else:
            # 일반 자연어 질문 처리: 이전 대화 맥락을 유지하며 응답 생성
            resp = await agent.analyze_and_respond(
                incident=incident,
                user_message=user_input,
                chat_history=repo.get_chat_history(incident.incident_id, limit=6),
                action_results=repo.get_action_results(incident.incident_id)
            )
            current_actions = resp.recommended_actions
            display_response(resp)

if __name__ == "__main__":
    asyncio.run(run_simulator())
