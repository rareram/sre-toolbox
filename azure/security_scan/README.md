# Azure 자원 보안 설정 점검 유틸리티 (`security_scan`)

Azure SDK 및 Azure Functions(HTTP Trigger) 기반으로 대상 구독(Subscription) 내 주요 클라우드 자원의 암호화 및 보안 설정 누락 여부를 진단하는 스캔 유틸리티입니다.

---

## 주요 점검 항목

1. **Virtual Machine 디스크 암호화 상태 (`vm_encryption`)**:
   - VM 호스트 암호화(`encryption_at_host`) 및 OS 디스크 암호화 적용 상태 점검
2. **Storage Account 암호화 상태 (`storage_encryption`)**:
   - 스토리지 계정의 Blob 서비스 암호화 활성화 상태 점검
3. **네트워크 보안 그룹 규칙 (`network_security_groups`)**:
   - NSG(Network Security Group) 내 차단 규칙(Deny Rule) 구성 상태 점검
4. **Azure SQL Database TDE 상태 (`sql_tde`)**:
   - Azure SQL 데이터베이스의 투명적 데이터 암호화(TDE, Transparent Data Encryption) 활성화 상태 점검

---

## 환경 설정 및 사전 준비

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 구독 ID 및 인증 설정
`security_chk.py` 내 `subscription_id` 변수에 점검 대상 Azure Subscription ID를 지정합니다.
- 인증은 `DefaultAzureCredential` 기반으로 수행되므로 아래 중 하나의 환경을 준비합니다:
  - Azure Managed Identity (Azure Functions 배포 시)
  - Azure CLI 로그인 (`az login`)
  - 환경 변수 지정 (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`)

---

## 실행 및 API 응답 구조

### HTTP Trigger 호출 (`GET /api/security_chk`)

Azure Function 실행 후 HTTP 요청을 전송하여 보안 점검 결과를 수신합니다.

**응답 예시 (HTTP 200)**:
```json
{
  "vm_encryption": "3/5 VMs are encrypted",
  "storage_encryption": "4/4 storage accounts have encryption enabled",
  "network_security_groups": "2/2 NSGs have deny rules",
  "sql_tde": "1/1 SQL databases have TDE enabled"
}
```

---

## 라이선스
MIT License
