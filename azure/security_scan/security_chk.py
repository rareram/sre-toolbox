import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.sql import SqlManagementClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    subscription_id = "YOUR_SUBSCRIPTION_ID"
    credential = DefaultAzureCredential()

    # Initialize clients
    compute_client = ComputeManagementClient(credential, subscription_id)
    storage_client = StorageManagementClient(credential, subscription_id)
    network_client = NetworkManagementClient(credential, subscription_id)
    sql_client = SqlManagementClient(credential, subscription_id)

    results = {
        "vm_encryption": check_vm_encryption(compute_client),
        "storage_encryption": check_storage_encryption(storage_client),
        "network_security_groups": check_network_security_groups(network_client),
        "sql_tde": check_sql_tde(sql_client)
    }

    return func.HttpResponse(
        str(results),
        status_code=200
    )

def check_vm_encryption(compute_client):
    encrypted_vms = 0
    total_vms = 0
    for vm in compute_client.virtual_machines.list_all():
        total_vms += 1
        if vm.encryption_at_host or (vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.encryption):
            encrypted_vms += 1
    return f"{encrypted_vms}/{total_vms} VMs are encrypted"

def check_storage_encryption(storage_client):
    encrypted_accounts = 0
    total_accounts = 0
    for account in storage_client.storage_accounts.list():
        total_accounts += 1
        if account.encryption and account.encryption.services.blob.enabled:
            encrypted_accounts += 1
    return f"{encrypted_accounts}/{total_accounts} storage accounts have encryption enabled"

def check_network_security_groups(network_client):
    secure_nsgs = 0
    total_nsgs = 0
    for nsg in network_client.network_security_groups.list_all():
        total_nsgs += 1
        if any(rule.access == 'Deny' for rule in nsg.security_rules):
            secure_nsgs += 1
    return f"{secure_nsgs}/{total_nsgs} NSGs have deny rules"

def check_sql_tde(sql_client):
    tde_enabled_dbs = 0
    total_dbs = 0
    for server in sql_client.servers.list():
        for db in sql_client.databases.list_by_server(server.id.split('/')[4], server.name):
            total_dbs += 1
            if db.transparent_data_encryption and db.transparent_data_encryption.status == 'Enabled':
                tde_enabled_dbs += 1
    return f"{tde_enabled_dbs}/{total_dbs} SQL databases have TDE enabled"
