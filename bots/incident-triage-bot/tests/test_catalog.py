import os
import tempfile
import pytest
from src.catalog import CsvInventoryProvider, ServerNode

SAMPLE_CSV_CONTENT = """ip,hostname,cluster,role,location,owner,health_url,runbook_url,check_command,tags
10.19.20.101,spark-master-01,spark-prod,Spark Master,IDC 2F Rack A-01 10U,데이터팀 홍길동,http://10.19.20.101:8080,https://wiki.internal/spark,systemctl status spark-master,"prod,master,spark"
10.19.20.104,spark-worker-04,spark-prod,Spark Worker,IDC 2F Rack A-04 12U,데이터팀 홍길동,http://10.19.20.104:8081,https://wiki.internal/spark,systemctl status spark-worker,"prod,worker,spark"
10.20.10.11,kafka-broker-01,kafka-prod,Kafka Broker,IDC 3F Rack K-01 04U,메시징팀 이순신,http://10.20.10.11:9092,https://wiki.internal/kafka,systemctl status kafka,"prod,broker,kafka"
"""

@pytest.fixture
def temp_csv_file():
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as f:
        f.write(SAMPLE_CSV_CONTENT)
        f.flush()
        file_path = f.name
    yield file_path
    if os.path.exists(file_path):
        os.remove(file_path)

def test_catalog_load_and_lookup_by_ip(temp_csv_file):
    catalog = CsvInventoryProvider(temp_csv_file)
    node = catalog.get_by_ip("10.19.20.104")
    assert node is not None
    assert node.hostname == "spark-worker-04"
    assert node.role == "Spark Worker"
    assert node.location == "IDC 2F Rack A-04 12U"
    assert "worker" in node.tags

def test_catalog_lookup_with_port(temp_csv_file):
    catalog = CsvInventoryProvider(temp_csv_file)
    # Prometheus instance 라벨 형태(IP:PORT) 대응 검증
    node_ip = catalog.get_by_ip("10.19.20.104:9100")
    assert node_ip is not None
    assert node_ip.hostname == "spark-worker-04"

    node_host = catalog.get_by_hostname("spark-master-01:8080")
    assert node_host is not None
    assert node_host.ip == "10.19.20.101"

def test_catalog_search(temp_csv_file):
    catalog = CsvInventoryProvider(temp_csv_file)
    # 키워드 검색: 역할 기준
    kafka_nodes = catalog.search("kafka")
    assert len(kafka_nodes) == 1
    assert kafka_nodes[0].hostname == "kafka-broker-01"

    # 키워드 검색: 랙 위치 기준
    rack_nodes = catalog.search("Rack A-04")
    assert len(rack_nodes) == 1
    assert rack_nodes[0].hostname == "spark-worker-04"

    # 존재하지 않는 키워드
    empty_nodes = catalog.search("non-existent-keyword")
    assert len(empty_nodes) == 0

def test_catalog_summary_formatting(temp_csv_file):
    catalog = CsvInventoryProvider(temp_csv_file)
    node = catalog.get_by_hostname("spark-worker-04")
    assert node is not None
    summary = node.to_summary()
    assert "spark-worker-04" in summary
    assert "10.19.20.104" in summary
    assert "IDC 2F Rack A-04 12U" in summary
    assert "systemctl status spark-worker" in summary

def test_catalog_missing_file_graceful_fallback():
    catalog = CsvInventoryProvider("/path/to/non_existent_servers.csv")
    # 파일이 없어도 크래시 없이 None 반환 및 빈 리스트 반환
    assert catalog.get_by_ip("10.0.0.1") is None
    assert catalog.get_by_hostname("unknown-host") is None
    assert catalog.search("test") == []
