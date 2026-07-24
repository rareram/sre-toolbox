# -*- coding: utf-8 -*-
import json
from unittest.mock import patch, MagicMock
import pytest
from app import (
    app,
    INCIDENT_STORE,
    clean_json_response,
    build_teams_composite_message,
    get_or_create_incident_id
)

@pytest.fixture
def client():
    app.config["TESTING"] = True
    INCIDENT_STORE.clear()
    with app.test_client() as client:
        yield client

# ============================================================================
# 1. 헬퍼 유틸리티 및 파서 단위 테스트 (Unit Tests)
# ============================================================================

def test_get_or_create_incident_id():
    assert get_or_create_incident_id("INC-CUSTOM-99") == "INC-CUSTOM-99"
    assert get_or_create_incident_id("  ").startswith("INC-")

def test_clean_json_response_with_markdown_codeblock():
    raw_llm_output = """```json
{
  "dev_markdown": "## [1. 개발팀 공유용]",
  "leader_markdown": "## [2. 리더 보고용]",
  "customer_markdown": "## [3. 외부 공지용]",
  "remediation_hint": "## [4. 플레이북 힌트]",
  "checklist": ["점검 항목 1"],
  "timeline_entry": "상황 업데이트 완료"
}
```"""
    parsed = clean_json_response(raw_llm_output)
    assert parsed["dev_markdown"] == "## [1. 개발팀 공유용]"
    assert parsed["checklist"] == ["점검 항목 1"]

def test_clean_json_response_fallback_on_invalid_json():
    raw_plain_text = "이것은 JSON이 아닌 일반 텍스트 응답입니다."
    parsed = clean_json_response(raw_plain_text)
    assert "이것은 JSON이 아닌" in parsed["dev_markdown"]
    assert len(parsed["checklist"]) > 0

def test_build_teams_composite_message_filtering():
    sample_report = {
        "incident_id": "INC-20260724-01",
        "first_seen": "12:00:00",
        "update_count": 2,
        "duration_str": "15분 진행 중",
        "dev_markdown": "## [1. 개발팀 전용 텍스트]",
        "leader_markdown": "## [2. 리더 전용 텍스트]",
        "customer_markdown": "## [3. 고객 전용 텍스트]",
        "remediation_hint": "## [4. 조치 힌트]",
        "checklist": ["체크1"],
        "full_timeline": [{"timestamp": "12:00:00", "entry": "초동 조치 완료"}]
    }
    
    dev_msg = build_teams_composite_message(sample_report, "dev")
    assert "개발팀 전용 텍스트" in dev_msg
    assert "리더 전용 텍스트" not in dev_msg
    assert "최초 발생" in dev_msg
    assert "15분 진행 중" in dev_msg
    assert "*Bot*:" in dev_msg

# ============================================================================
# 2. Flask 엔드포인트 API 통합 테스트 (Integration Tests)
# ============================================================================

def test_healthz_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "bot_name" in data
    assert "bot_version" in data
    assert "bot_owner" in data
    assert "hostname" in data

def test_generate_missing_raw_incident(client):
    response = client.post("/generate", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()

    response_space = client.post("/generate", json={"raw_incident": "   "})
    assert response_space.status_code == 400

@patch("app.client.chat.completions.create")
def test_generate_success(mock_llm_create, client):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "dev_markdown": "## [1. 개발팀 내부 공유용 - Technical Report]\n- 로그 분석 완료",
            "leader_markdown": "## [2. 리더/임원 보고용 - Managerial Summary]\n- 조치 중",
            "customer_markdown": "## [3. 고객/외부 공지용 - External Notice]\n- 점검 안내",
            "remediation_hint": "## [4. 플레이북 긴급 조치 가이드 - Remediation Hint]\n- kubectl rollout restart 실행 권장",
            "checklist": ["DB 연결 점검", "캐시 재설정"],
            "timeline_entry": "초동 분석 및 원인 파악 완료"
        })))
    ]
    mock_llm_create.return_value = mock_response

    payload = {
        "raw_incident": "2026-07-24 12:00 DB Timeout 발생",
        "incident_id": "INC-TEST-100"
    }

    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    
    assert data["incident_id"] == "INC-TEST-100"
    assert "first_seen" in data
    assert data["update_count"] == 1
    assert "duration_str" in data
    assert "개발팀" in data["dev_markdown"]
    assert "Remediation Hint" in data["remediation_hint"]
    assert len(data["checklist"]) == 2
    assert len(data["full_timeline"]) == 1

@patch("app.client.chat.completions.create")
def test_generate_llm_exception_graceful_handling(mock_llm_create, client):
    mock_llm_create.side_effect = Exception("LLM Connection Timeout")

    response = client.post("/generate", json={"raw_incident": "장애 테스트"})
    assert response.status_code == 200
    data = response.get_json()
    assert "LLM 분석 오류 발생" in data["dev_markdown"]
    assert len(data["full_timeline"]) == 1

@patch("app.client.chat.completions.create")
def test_timeline_accumulation(mock_llm_create, client):
    mock_response1 = MagicMock()
    mock_response1.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "dev_markdown": "1차 분석",
            "leader_markdown": "1차 보고",
            "customer_markdown": "1차 공지",
            "remediation_hint": "1차 힌트",
            "checklist": ["체크1"],
            "timeline_entry": "장애 원인 파악 중"
        })))
    ]
    mock_response2 = MagicMock()
    mock_response2.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "dev_markdown": "2차 조치",
            "leader_markdown": "2차 보고",
            "customer_markdown": "2차 공지",
            "remediation_hint": "2차 힌트",
            "checklist": ["체크2"],
            "timeline_entry": "DB 재부팅 완료 및 복구 진행 중"
        })))
    ]
    
    mock_llm_create.side_effect = [mock_response1, mock_response2]
    inc_id = "INC-ACCUMULATE-01"

    res1 = client.post("/generate", json={"raw_incident": "1차 상황", "incident_id": inc_id})
    assert res1.status_code == 200
    assert len(res1.get_json()["full_timeline"]) == 1

    res2 = client.post("/generate", json={"raw_incident": "2차 상황", "incident_id": inc_id})
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert len(data2["full_timeline"]) == 2
    assert data2["full_timeline"][1]["entry"] == "DB 재부팅 완료 및 복구 진행 중"
    assert data2["update_count"] == 2

@patch("app.client.chat.completions.create")
def test_grafana_webhook(mock_llm_create, client):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "dev_markdown": "Grafana Alert 분석",
            "leader_markdown": "Grafana Alert 보고",
            "customer_markdown": "Grafana Alert 공지",
            "remediation_hint": "Grafana 힌트",
            "checklist": ["Pod 개수 점검"],
            "timeline_entry": "Grafana High CPU Alert 감지"
        })))
    ]
    mock_llm_create.return_value = mock_response

    grafana_payload = {
        "title": "High CPU Usage Alert",
        "commonLabels": {"service": "payment-api"},
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "HighCPU", "service": "payment-api"},
                "annotations": {"summary": "CPU usage exceeded 90% for 5 mins"}
            }
        ]
    }

    response = client.post("/webhook/grafana", json=grafana_payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["incident_id"] == "payment-api"

def test_teams_webhook_missing_env(client):
    with patch("app.TEAMS_WEBHOOK", None):
        response = client.post("/generate", json={
            "raw_incident": "Teams 테스트",
            "post_to_teams": True
        })
        assert response.status_code == 500
        assert "TEAMS_WEBHOOK" in response.get_json()["error"]

@patch("app.requests.post")
@patch("app.client.chat.completions.create")
def test_teams_webhook_posting_failure(mock_llm_create, mock_requests_post, client):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "dev_markdown": "개발팀 리포트",
            "leader_markdown": "리더 리포트",
            "customer_markdown": "고객 리포트",
            "remediation_hint": "조치 힌트",
            "checklist": ["체크1"],
            "timeline_entry": "상황 전송 완료"
        })))
    ]
    mock_llm_create.return_value = mock_response
    
    mock_requests_post.side_effect = Exception("HTTP 404 Not Found")

    with patch("app.TEAMS_WEBHOOK", "https://outlook.office.com/webhook/invalid-url"):
        response = client.post("/generate", json={
            "raw_incident": "Teams 전송 에러 테스트",
            "post_to_teams": True
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["posted_to_teams"] is False
        assert "HTTP 404 Not Found" in data["teams_post_error"]

@patch("app.client.chat.completions.create")
def test_generate_non_technical_symptom_input(mock_llm_create, client):
    # 비기술자/고객사 담당자의 구두 현상 입력 ("결제창이 흰 화면으로 멈춰요") 테스트
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "dev_markdown": "## [1. 개발팀 공유용]\n- **추정 원인**: Frontend PG SDK 로딩 타임아웃 또는 API Gateway SSL 체인 문제 추정",
            "leader_markdown": "## [2. 리더 보고용]\n- 결제 서비스 일부 고객 화면 멈춤 현상",
            "customer_markdown": "## [3. 고객 공지용]\n- 결제 서비스 일시 지연 현상 확인 중",
            "remediation_hint": "## [4. 조치 힌트]\n- curl -v https://pg-gateway.company.com/health 로 응답 확인",
            "checklist": ["PG Gateway SSL 상태 확인", "Frontend CDN 상태 점검"],
            "timeline_entry": "고객사 결제창 멈춤 제보 수신"
        })))
    ]
    mock_llm_create.return_value = mock_response

    response = client.post("/generate", json={
        "raw_incident": "고객사에서 결제 버튼 누르면 흰색 화면만 떠서 아무것도 안 된다고 제보 들어옴"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert "PG SDK" in data["dev_markdown"]
    assert "고객사 결제창 멈춤 제보 수신" == data["full_timeline"][0]["entry"]


