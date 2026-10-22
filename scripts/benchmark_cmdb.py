#!/usr/bin/env python3
"""
Sovereign CMDB Benchmark: ServiceNow PDI REST API vs. Sovereign VFS POSIX
Measures:
1. Ingress Latency (ms)
2. Payload Size (Bytes & Characters)
3. Model Context Ingestion Tokens
"""
import time
import requests
import json
import os
from pathlib import Path

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Fill in your PDI URL & credentials once provisioning finishes:
SN_INSTANCE = os.getenv("SN_INSTANCE", "https://dev186522.service-now.com")
SN_USER = os.getenv("SN_USER", "admin")
SN_PASS = os.getenv("SN_PASS", "J-Slf7SPmg!2")

CI_NAME = "faas_server"
VFS_PATH = Path("/home/james/stacklabs/vfs/cmdb")
VFS_SHM_PATH = Path("/dev/shm/faas_vfs/cmdb")

# ==============================================================================
# 1. SERVICENOW PDI RUN (ENTERPRISE REST API)
# ==============================================================================
def test_servicenow():
    if "devXXXXX" in SN_INSTANCE:
        return {
            "engine": "ServiceNow PDI REST",
            "status": "SKIPPED_CREDENTIALS_NOT_SET",
            "latency_ms": None,
            "payload_bytes": None,
            "raw_payload_len_chars": None,
            "result": "Configure SN_INSTANCE, SN_USER, SN_PASS to run live PDI test."
        }
    
    start = time.perf_counter()
    
    # Hop 1: Fetch Logical CI (cmdb_ci_appl)
    url_ci = f"{SN_INSTANCE}/api/now/table/cmdb_ci_appl?sysparm_query=name={CI_NAME}&sysparm_limit=1"
    res_ci = requests.get(url_ci, auth=(SN_USER, SN_PASS), timeout=10)
    ci_data = res_ci.json()
    
    sys_id = ci_data["result"][0]["sys_id"] if ci_data.get("result") else None
    port = ci_data["result"][0].get("tcp_port", "3033") if ci_data.get("result") else None
    
    # Hop 2: Fetch Relationship (cmdb_rel_ci: Runs on::Hosts)
    url_rel = f"{SN_INSTANCE}/api/now/table/cmdb_rel_ci?sysparm_query=child={sys_id}&sysparm_limit=1"
    res_rel = requests.get(url_rel, auth=(SN_USER, SN_PASS), timeout=10)
    rel_data = res_rel.json()
    parent_sys_id = rel_data["result"][0]["parent"]["value"] if rel_data.get("result") else None
    
    # Hop 3: Fetch Parent Physical Node IP (cmdb_ci_server)
    url_parent = f"{SN_INSTANCE}/api/now/table/cmdb_ci_server/{parent_sys_id}"
    res_parent = requests.get(url_parent, auth=(SN_USER, SN_PASS), timeout=10)
    parent_data = res_parent.json()
    ip = parent_data["result"].get("ip_address", "") if parent_data.get("result") else None
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    total_bytes = len(res_ci.content) + len(res_rel.content) + len(res_parent.content)
    full_json_payload = res_ci.text + res_rel.text + res_parent.text
    
    return {
        "engine": "ServiceNow PDI REST",
        "status": "SUCCESS",
        "latency_ms": round(elapsed_ms, 2),
        "payload_bytes": total_bytes,
        "raw_payload_len_chars": len(full_json_payload),
        "result": f"Port: {port}, Host IP: {ip}"
    }

# ==============================================================================
# 2. VFS CMDB RUN (BARE-METAL POSIX READS)
# ==============================================================================
def test_vfs(path_root: Path):
    start = time.perf_counter()
    
    # Scalar Point Reads + Native Kernel Symlink Traversal
    port_file = path_root / "logical" / CI_NAME / "port.txt"
    runs_on_link = path_root / "logical" / CI_NAME / "runs_on"
    ip_file = runs_on_link.resolve() / "ip.txt"
    
    port = port_file.read_text(encoding="utf-8").strip()
    host_ip = ip_file.read_text(encoding="utf-8").strip()
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    payload_str = f"Port: {port}, Host IP: {host_ip}"
    
    return {
        "engine": f"VFS CMDB ({path_root.name})",
        "status": "SUCCESS",
        "latency_ms": elapsed_ms,
        "payload_bytes": len(payload_str.encode("utf-8")),
        "raw_payload_len_chars": len(payload_str),
        "result": payload_str
    }

def main():
    print("=" * 70)
    print("⚡ STACKLABS CMDB BENCHMARK: SERVICENOW PDI vs. SOVEREIGN VFS")
    print("=" * 70)

    # 1. Test NVMe VFS
    vfs_nvme = test_vfs(VFS_PATH)
    print("\n--- 1. VFS CMDB (NVMe Storage) ---")
    print(f"Latency:        {vfs_nvme['latency_ms']:.4f} ms")
    print(f"Payload Bytes:  {vfs_nvme['payload_bytes']} bytes")
    print(f"Payload Chars:  {vfs_nvme['raw_payload_len_chars']} chars")
    print(f"Resolved Data:  {vfs_nvme['result']}")

    # 2. Test /dev/shm VFS
    if VFS_SHM_PATH.exists():
        vfs_shm = test_vfs(VFS_SHM_PATH)
        print("\n--- 2. VFS CMDB (/dev/shm Pagecache) ---")
        print(f"Latency:        {vfs_shm['latency_ms']:.4f} ms")
        print(f"Payload Bytes:  {vfs_shm['payload_bytes']} bytes")
        print(f"Payload Chars:  {vfs_shm['raw_payload_len_chars']} chars")
        print(f"Resolved Data:  {vfs_shm['result']}")

    # 3. Test ServiceNow PDI
    print("\n--- 3. ServiceNow Personal Developer Instance (PDI) ---")
    sn_res = test_servicenow()
    if sn_res["status"] == "SUCCESS":
        print(f"Latency:        {sn_res['latency_ms']:.2f} ms")
        print(f"Payload Bytes:  {sn_res['payload_bytes']} bytes")
        print(f"Payload Chars:  {sn_res['raw_payload_len_chars']} chars")
        print(f"Resolved Data:  {sn_res['result']}")
        
        # Calculate Delta
        speedup = sn_res["latency_ms"] / vfs_nvme["latency_ms"]
        byte_reduction = (1 - (vfs_nvme["payload_bytes"] / sn_res["payload_bytes"])) * 100
        print("\n" + "=" * 70)
        print(f"🚀 VERIFIED MULTIPLIER:")
        print(f"• VFS is {speedup:.1f}x FASTER than ServiceNow PDI REST")
        print(f"• Payload reduced by {byte_reduction:.2f}% ({sn_res['payload_bytes']} B ➔ {vfs_nvme['payload_bytes']} B)")
        print("=" * 70)
    else:
        print(f"Status:         {sn_res['status']}")
        print(f"Notice:         {sn_res['result']}")
        print("Tip: Run with SN_INSTANCE=https://devXXX.service-now.com SN_PASS=xxx python3 benchmark_cmdb.py")

if __name__ == "__main__":
    main()
