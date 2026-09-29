import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# 인증 정보 보호: 외부 관측성/LLM/Teams 주소 및 인증정보를 환경변수(.env)로 통합 관리
# 단순화(ponytail): 외부 라이브러리 대신 표준 dataclass(frozen) 기반의 읽기 전용 설정 모델링
# 현실적 인프라 수용: Prometheus/Loki의 무인증(OSS 기본), Basic Auth, Bearer Token 분리 지원

load_dotenv()

@dataclass(frozen=True)
class ObservabilityConfig:
    # Grafana 대시보드 및 알람 규칙 연동 API (Service Account Token 사용)
    grafana_url: str = field(default_factory=lambda: os.getenv("GRAFANA_URL", "http://localhost:3000"))
    grafana_token: Optional[str] = field(default_factory=lambda: os.getenv("GRAFANA_TOKEN"))

    # Prometheus 메트릭(PromQL) 시계열 쿼리 API
    # OSS 기본은 무인증이며, 사내 프록시/게이트웨이에 따라 Basic Auth 또는 Bearer Token 사용
    prometheus_url: str = field(default_factory=lambda: os.getenv("PROMETHEUS_URL", "http://localhost:9090"))
    prometheus_bearer_token: Optional[str] = field(
        default_factory=lambda: os.getenv("PROMETHEUS_BEARER_TOKEN") or os.getenv("PROMETHEUS_TOKEN")
    )
    prometheus_username: Optional[str] = field(default_factory=lambda: os.getenv("PROMETHEUS_USERNAME"))
    prometheus_password: Optional[str] = field(default_factory=lambda: os.getenv("PROMETHEUS_PASSWORD"))

    # 하위 호환성 프로퍼티
    @property
    def prometheus_token(self) -> Optional[str]:
        return self.prometheus_bearer_token

    # Loki 로그(LogQL) 조회 API (멀티테넌트 및 프록시 인증 지원)
    loki_url: str = field(default_factory=lambda: os.getenv("LOKI_URL", "http://localhost:3100"))
    loki_tenant_id: Optional[str] = field(default_factory=lambda: os.getenv("LOKI_TENANT_ID"))
    loki_bearer_token: Optional[str] = field(
        default_factory=lambda: os.getenv("LOKI_BEARER_TOKEN") or os.getenv("LOKI_TOKEN")
    )
    loki_username: Optional[str] = field(default_factory=lambda: os.getenv("LOKI_USERNAME"))
    loki_password: Optional[str] = field(default_factory=lambda: os.getenv("LOKI_PASSWORD"))

    # 하위 호환성 프로퍼티
    @property
    def loki_token(self) -> Optional[str]:
        return self.loki_bearer_token

    # Pyroscope 연속 프로파일링 API
    pyroscope_url: str = field(default_factory=lambda: os.getenv("PYROSCOPE_URL", "http://localhost:4040"))
    pyroscope_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("PYROSCOPE_API_KEY") or os.getenv("PYROSCOPE_TOKEN")
    )

    @property
    def pyroscope_token(self) -> Optional[str]:
        return self.pyroscope_api_key

    # OpenTelemetry Collector OTLP HTTP 트레이스/메트릭 수집 엔드포인트
    otel_endpoint: str = field(default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"))
    otel_headers: Optional[str] = field(default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_HEADERS"))


@dataclass(frozen=True)
class LLMConfig:
    """
    LLM 공급자 설정.
    로컬 OSS(Ollama/llama.cpp), 사내 엔터프라이즈(vLLM/TGI), 공용 클라우드(OpenAI/Azure) 지원.
    """
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama")) # ollama | vllm | openai | azure
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"))
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", "ollama"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gemma4:e4b-mlx"))
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0")))
    # Azure OpenAI 전용 배포 설정
    azure_api_version: Optional[str] = field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION"))


@dataclass(frozen=True)
class DecisionConfig:
    """
    System 1 판단 모델 설정 (Laya / Kev / Jev / Rule)
    일반 옵션과 고급 옵션(루프백 튜닝)을 분리하여 안정적인 운영을 보장합니다.
    """
    # 1. 일반 옵션 (Standard Options)
    backend: str = field(default_factory=lambda: os.getenv("DECISION_BACKEND", "rule")) # rule | laya | kev | jev
    api_url: Optional[str] = field(default_factory=lambda: os.getenv("DECISION_API_URL"))
    api_token: Optional[str] = field(default_factory=lambda: os.getenv("DECISION_API_TOKEN"))

    # 2. 고급 옵션 (Advanced / Expert Options - 기본값 유지 권장)
    # Laya 인과 판단 불확실 시 추가 관측을 위한 최대 유계 루프백 횟수 (기본값: 1, 0~2 권장, 3 이상 시 레이턴시 폭증 위험)
    max_loopback_hops: int = field(
        default_factory=lambda: int(os.getenv("DECISION_MAX_LOOPBACK_HOPS", "1"))
    )
    # 루프백 1회당 최대 허용 비동기 타임아웃 (초)
    loopback_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("DECISION_LOOPBACK_TIMEOUT_SECONDS", "1.5"))
    )
    # 1차 판단 결과로 루프백 없이 즉시 확정하기 위한 최소 신뢰도 임계치
    confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("DECISION_CONFIDENCE_THRESHOLD", "0.85"))
    )


@dataclass(frozen=True)
class TeamsConfig:
    webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("TEAMS_WEBHOOK_URL"))
    app_id: Optional[str] = field(default_factory=lambda: os.getenv("TEAMS_APP_ID"))
    app_password: Optional[str] = field(default_factory=lambda: os.getenv("TEAMS_APP_PASSWORD"))


@dataclass(frozen=True)
class AppConfig:
    db_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "triage.db"))
    correlation_window_seconds: int = field(
        default_factory=lambda: int(os.getenv("CORRELATION_WINDOW_SECONDS", "60"))
    )
    incident_max_idle_seconds: int = field(
        default_factory=lambda: int(os.getenv("INCIDENT_MAX_IDLE_SECONDS", "1800"))
    )
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))

    # 서버 인벤토리 카탈로그 경로
    inventory_file_path: str = field(
        default_factory=lambda: os.getenv("INVENTORY_FILE_PATH", "config/servers.example.csv")
    )

    # 옵셔널 캐시 저장소 (미지정 시 SQLite 단독 모드)
    redis_url: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_URL"))

    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    teams: TeamsConfig = field(default_factory=TeamsConfig)


# 전역 설정 인스턴스: 앱 기동 시 1회 로드하여 설정값 불변 보장
config = AppConfig()
