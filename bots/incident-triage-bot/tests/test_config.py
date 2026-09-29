import os
from unittest.mock import patch
from src.config import AppConfig

# 환경변수 미지정 시에도 기본값으로 정상 동작하는지 검증.
def test_config_defaults():
    cfg = AppConfig()
    assert cfg.db_path == "triage.db"
    assert cfg.correlation_window_seconds == 60
    assert cfg.llm.base_url == "http://localhost:11434/v1"
    assert cfg.llm.provider == "ollama"
    assert cfg.observability.grafana_url == "http://localhost:3000"
    assert cfg.observability.prometheus_url == "http://localhost:9090"
    assert cfg.observability.loki_url == "http://localhost:3100"
    assert cfg.observability.pyroscope_url == "http://localhost:4040"
    assert cfg.decision.backend == "rule"
    assert cfg.decision.max_loopback_hops == 1
    assert cfg.decision.loopback_timeout_seconds == 1.5
    assert cfg.decision.confidence_threshold == 0.85

# 배포 환경별 주소 및 보안 토큰 덮어쓰기 설정 검증.
# patch.dict로 테스트 러너의 전역 os.environ 오염 방지.
def test_config_custom_env():
    with patch.dict(os.environ, {
        "GRAFANA_URL": "https://grafana.internal",
        "GRAFANA_TOKEN": "secret-token",
        "PROMETHEUS_URL": "https://prom.internal",
        "LOKI_URL": "https://loki.internal",
        "PYROSCOPE_URL": "https://pyro.internal"
    }):
        cfg = AppConfig()
        assert cfg.observability.grafana_url == "https://grafana.internal"
        assert cfg.observability.grafana_token == "secret-token"
        assert cfg.observability.prometheus_url == "https://prom.internal"
        assert cfg.observability.loki_url == "https://loki.internal"
        assert cfg.observability.pyroscope_url == "https://pyro.internal"

# 프록시 인증(Basic Auth/Bearer) 및 엔터프라이즈 LLM(vLLM) 설정 검증.
def test_config_auth_and_provider_variants():
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "vllm",
        "LLM_BASE_URL": "http://vllm.internal:8000/v1",
        "LLM_API_KEY": "vllm-corp-key",
        "PROMETHEUS_USERNAME": "prom-user",
        "PROMETHEUS_PASSWORD": "prom-password",
        "LOKI_BEARER_TOKEN": "loki-token",
        "DECISION_BACKEND": "laya",
        "DECISION_API_URL": "http://laya.internal:8000"
    }):
        cfg = AppConfig()
        assert cfg.llm.provider == "vllm"
        assert cfg.llm.base_url == "http://vllm.internal:8000/v1"
        assert cfg.observability.prometheus_username == "prom-user"
        assert cfg.observability.prometheus_password == "prom-password"
        assert cfg.observability.loki_bearer_token == "loki-token"
        assert cfg.decision.backend == "laya"
        assert cfg.decision.api_url == "http://laya.internal:8000"


def test_config_decision_advanced_options_override():
    # System 1 고급 옵션(유계 루프백 횟수, 타임아웃, 임계치) 덮어쓰기 검증
    with patch.dict(os.environ, {
        "DECISION_BACKEND": "laya",
        "DECISION_MAX_LOOPBACK_HOPS": "2",
        "DECISION_LOOPBACK_TIMEOUT_SECONDS": "2.5",
        "DECISION_CONFIDENCE_THRESHOLD": "0.90"
    }):
        cfg = AppConfig()
        assert cfg.decision.backend == "laya"
        assert cfg.decision.max_loopback_hops == 2
        assert cfg.decision.loopback_timeout_seconds == 2.5
        assert cfg.decision.confidence_threshold == 0.90
