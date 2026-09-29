import csv
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 불필요한 복잡도 배제(ponytail): 외부 CMDB 의존성 없이 표준 라이브러리(csv) 기반 인메모리 역색인 제공
# 안전한 운영 연속성: 야간/휴일 온콜 시 IP와 호스트명만으로 장비 위치, 역할, 담당자, 점검 명령어를 즉시 조회

@dataclass
class ServerNode:
    ip: str
    hostname: str
    cluster: str = ""
    role: str = ""
    location: str = ""                         # 물리/논리 위치 (예: IDC 2F Rack A-04 12U)
    owner: str = ""                            # 담당팀 및 엔지니어
    health_url: Optional[str] = None           # HTTP 헬스체크 주소
    runbook_url: Optional[str] = None          # 관련 위키 및 런북 가이드
    check_command: Optional[str] = None        # 엔지니어 터미널 복사용 표준 점검 명령어
    tags: List[str] = field(default_factory=list)

    def to_summary(self) -> str:
        """메신저 및 LLM 프롬프트 주입용 요약 문자열 반환"""
        lines = [
            f"- 호스트명: {self.hostname} (IP: {self.ip})",
            f"- 역할/클러스터: {self.role} / {self.cluster}" if self.cluster else f"- 역할: {self.role}",
            f"- 물리 위치: {self.location}" if self.location else "- 물리 위치: 미지정",
            f"- 담당자: {self.owner}" if self.owner else "- 담당자: 미지정",
        ]
        if self.runbook_url:
            lines.append(f"- 런북: {self.runbook_url}")
        if self.check_command:
            lines.append(f"- 권장 점검 명령: `{self.check_command}`")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """REST API 및 직렬화용 딕셔너리 반환"""
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "cluster": self.cluster,
            "role": self.role,
            "location": self.location,
            "owner": self.owner,
            "health_url": self.health_url,
            "runbook_url": self.runbook_url,
            "check_command": self.check_command,
            "tags": self.tags,
        }


class InventoryProvider(ABC):
    @abstractmethod
    def get_by_ip(self, ip: str) -> Optional[ServerNode]:
        """IP 주소로 서버 정보 단건 조회"""
        pass

    @abstractmethod
    def get_by_hostname(self, hostname: str) -> Optional[ServerNode]:
        """호스트명으로 서버 정보 단건 조회"""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[ServerNode]:
        """키워드(IP, 호스트, 역할, 위치, 태그) 부분 일치 다건 검색"""
        pass

    @abstractmethod
    def reload(self) -> None:
        """인벤토리 파일 리로드"""
        pass


class CsvInventoryProvider(InventoryProvider):
    """
    CSV 파일 기반 경량 서버 카탈로그 구현체.
    표준 csv 모듈을 사용하여 외부 의존성을 배제하고 인메모리 해시 맵으로 O(1) 조회를 보장합니다.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ip_map: Dict[str, ServerNode] = {}
        self._hostname_map: Dict[str, ServerNode] = {}
        self._nodes: List[ServerNode] = []
        self._last_mtime: float = 0.0
        self.reload()

    def _check_and_reload(self) -> None:
        """파일 수정 시간(mtime)이 변경되었으면 무재기동 핫 리로드를 수행합니다."""
        if not os.path.exists(self.file_path):
            return
        try:
            current_mtime = os.path.getmtime(self.file_path)
            if current_mtime > self._last_mtime:
                self.reload()
        except OSError:
            pass

    def reload(self) -> None:
        """인벤토리 CSV 파일을 파싱하여 내부 인덱스를 갱신합니다."""
        if not os.path.exists(self.file_path):
            logger.warning(f"서버 인벤토리 파일을 찾을 수 없습니다: {self.file_path}")
            self._ip_map.clear()
            self._hostname_map.clear()
            self._nodes.clear()
            self._last_mtime = 0.0
            return

        new_ip_map: Dict[str, ServerNode] = {}
        new_hostname_map: Dict[str, ServerNode] = {}
        new_nodes: List[ServerNode] = []

        try:
            current_mtime = os.path.getmtime(self.file_path)
            with open(self.file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = (row.get("ip") or "").strip()
                    hostname = (row.get("hostname") or "").strip()
                    if not ip and not hostname:
                        continue

                    raw_tags = (row.get("tags") or "").strip()
                    tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []

                    node = ServerNode(
                        ip=ip,
                        hostname=hostname,
                        cluster=(row.get("cluster") or "").strip(),
                        role=(row.get("role") or "").strip(),
                        location=(row.get("location") or "").strip(),
                        owner=(row.get("owner") or "").strip(),
                        health_url=(row.get("health_url") or "").strip() or None,
                        runbook_url=(row.get("runbook_url") or "").strip() or None,
                        check_command=(row.get("check_command") or "").strip() or None,
                        tags=tags,
                    )

                    new_nodes.append(node)
                    if ip:
                        new_ip_map[ip] = node
                    if hostname:
                        new_hostname_map[hostname.lower()] = node

            self._ip_map = new_ip_map
            self._hostname_map = new_hostname_map
            self._nodes = new_nodes
            self._last_mtime = current_mtime
            logger.info(f"서버 인벤토리 로드 완료: 총 {len(self._nodes)}대 서버 등록됨 ({self.file_path})")

        except Exception as e:
            logger.error(f"서버 인벤토리 파일 파싱 중 오류 발생: {e}", exc_info=True)
            # 장애 격리: 파싱 오류 발생 시 기존 캐시 유지 또는 안전 빈 상태 보장

    def get_by_ip(self, ip: str) -> Optional[ServerNode]:
        self._check_and_reload()
        clean_ip = ip.strip()
        # 포트 번호가 포함된 경우(예: 10.19.20.104:9100) IP 부분만 분리
        if ":" in clean_ip:
            clean_ip = clean_ip.split(":")[0]
        return self._ip_map.get(clean_ip)

    def get_by_hostname(self, hostname: str) -> Optional[ServerNode]:
        self._check_and_reload()
        clean_host = hostname.strip().lower()
        if ":" in clean_host:
            clean_host = clean_host.split(":")[0]
        return self._hostname_map.get(clean_host)

    def search(self, query: str, limit: int = 5) -> List[ServerNode]:
        self._check_and_reload()
        clean_query = query.strip().lower()
        if not clean_query:
            return self._nodes[:limit]

        results: List[ServerNode] = []
        for node in self._nodes:
            # 1. IP 또는 호스트명 직접 일치 우선
            if clean_query in node.ip.lower() or clean_query in node.hostname.lower():
                results.append(node)
                if len(results) >= limit:
                    return results
                continue

            # 2. 역할, 위치, 클러스터, 담당자, 태그 부분 일치
            searchable_text = f"{node.cluster} {node.role} {node.location} {node.owner} {' '.join(node.tags)}".lower()
            if clean_query in searchable_text:
                results.append(node)
                if len(results) >= limit:
                    return results

        return results
