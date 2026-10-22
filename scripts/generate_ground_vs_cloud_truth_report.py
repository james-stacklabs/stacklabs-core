#!/usr/bin/env python3
import os
import sys
import subprocess
import re
import argparse
from datetime import datetime

# Path definitions
SYNC_ANCHOR_FILE = "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/SYNC_ANCHOR_TOKEN.txt"
REPORT_OUTPUT_PATH = "/home/james/sovereign_inbox/reports/ground_vs_cloud_truth_report.md"

TARGETS = [
    {
        "id": "sovereign_os",
        "name": "NotebookLM: SovereignOS",
        "local": "/home/james/sovereign_inbox/notebook_sync/SovereignOS/",
        "remote": "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/SovereignOS/",
        "args": []
    },
    {
        "id": "sovereign_os_internal",
        "name": "NotebookLM: SovereignOS_Internal",
        "local": "/home/james/sovereign_inbox/notebook_sync/SovereignOS_Internal/",
        "remote": "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/SovereignOS_Internal/",
        "args": []
    },
    {
        "id": "stacklabs_internal",
        "name": "NotebookLM: StackLabs_Internal",
        "local": "/home/james/sovereign_inbox/notebook_sync/StackLabs_Internal/",
        "remote": "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Internal/",
        "args": []
    },
    {
        "id": "stacklabs_syndicate",
        "name": "NotebookLM: StackLabs_Syndicate",
        "local": "/home/james/sovereign_inbox/notebook_sync/StackLabs_Syndicate/",
        "remote": "sovereign_os:SovereignOS_Clio_Sync/NotebookLM_Sync/StackLabs_Syndicate/",
        "args": []
    },
    {
        "id": "workspace",
        "name": "Workspace: SovereignOS Repo",
        "local": "/home/james/stacklabs/",
        "remote": "sovereign_os:SovereignOS_Clio_Sync/SovereignOS/",
        "args": ["--exclude-from", "/home/james/stacklabs/.rclone-ignore", "--checkers", "16", "--fast-list"]
    }
]

def get_daemon_status():
    try:
        res = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        for line in res.stdout.splitlines():
            if "gameday_continuous_sync.py" in line and "python" in line:
                parts = line.split()
                pid = parts[1]
                args = " ".join(parts[10:])
                return f"🟢 **Active** (PID: `{pid}`)\nCommand: `{args}`"
    except Exception as e:
        return f"⚠️ Error checking status: {e}"
    return "🔴 **Inactive**"

def get_sync_anchor_token():
    if os.path.exists(SYNC_ANCHOR_FILE):
        try:
            with open(SYNC_ANCHOR_FILE, "r") as f:
                content = f.read()
            anchor_word = "Unknown"
            coordinate = "Unknown"
            last_sync = "Unknown"
            for line in content.splitlines():
                if line.startswith("Anchor Word:"):
                    anchor_word = line.split(":", 1)[1].strip()
                elif line.startswith("Coordinate:"):
                    coordinate = line.split(":", 1)[1].strip()
                elif line.startswith("LAST SYNC TIME:"):
                    last_sync = line.split(":", 1)[1].strip()
            return anchor_word, coordinate, last_sync
        except Exception as e:
            return "Error", str(e), "Error"
    return "None Found", "N/A", "N/A"

def run_rclone_check(target):
    cmd = ["rclone", "check", target["local"], target["remote"], "--one-way", "--combined", "-"] + target["args"]
    print(f"Running rclone check for {target['name']}...")
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    reasons = {}
    err_pattern = re.compile(r"ERROR\s+:\s+(.*?):\s+(.*)")
    for line in stderr.splitlines():
        match = err_pattern.search(line)
        if match:
            reasons[match.group(1).strip()] = match.group(2).strip()
            
    matched = []
    mismatched = []
    local_only = []
    remote_only = []
    errors = []
    
    for line in stdout.splitlines():
        if len(line) < 3:
            continue
        status_char = line[0]
        file_path = line[2:].strip()
        
        # Keep report focused by filtering out temp/venv/node_modules if any slip past rclone
        if any(ignored in file_path for ignored in ["node_modules/", ".git/", ".venv/", "venv/", ".pyc", "__pycache__"]):
            continue
            
        if status_char == '=':
            matched.append(file_path)
        elif status_char == '*':
            mismatched.append(file_path)
        elif status_char == '+':
            local_only.append(file_path)
        elif status_char == '-':
            remote_only.append(file_path)
        elif status_char == '!':
            errors.append(file_path)
            
    return {
        "matched": len(matched),
        "mismatched": mismatched,
        "local_only": local_only,
        "remote_only": remote_only,
        "errors": errors,
        "reasons": reasons
    }

def main():
    parser = argparse.ArgumentParser(description="Generate Ground vs Cloud Truth Sync Report")
    parser.add_argument("--quick", action="store_true", help="Skip the large workspace repo check")
    args = parser.parse_args()
    
    anchor_word, coordinate, last_sync = get_sync_anchor_token()
    daemon_status = get_daemon_status()
    audit_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    results = {}
    targets_to_check = TARGETS[:-1] if args.quick else TARGETS
    
    for target in targets_to_check:
        results[target["id"]] = run_rclone_check(target)
        
    # Build Markdown Report
    report = []
    report.append("# ⚖️ Sovereign OS: Ground vs Cloud Truth Sync Audit\n")
    report.append(f"**Audit Execution Time:** `{audit_time}`\n")
    
    # Check if there are any differences at all
    total_differences = sum(
        len(r["mismatched"]) + len(r["local_only"]) + len(r["remote_only"]) + len(r["errors"])
        for r in results.values()
    )
    
    if total_differences == 0:
        report.append("> [!NOTE]\n> **ALL SYSTEMS ALIGNED:** Ground Truth (Clio) and Cloud Truth (Google Drive) are in perfect parity. Zero differences found.\n")
    else:
        report.append(f"> [!WARNING]\n> **SYNC DRIFT DETECTED:** Found **{total_differences}** total difference(s) between local workspace/staging files and Google Drive. See details below.\n")
        
    report.append("## 🛰️ Sync Configuration & Diagnostics\n")
    report.append(f"- **Current Sync Anchor:** `{anchor_word}`")
    report.append(f"- **Anchor Coordinate:** `{coordinate}`")
    report.append(f"- **Last Codebase Push:** `{last_sync}`")
    report.append(f"- **Continuous Sync Daemon Status:**\n{daemon_status}\n")
    
    report.append("## 📊 Synchronization Parity Summary\n")
    report.append("| Target Directory | Matching Files | Mismatched Files | Local Only | Remote Only | Errors | Status |")
    report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    for target in TARGETS:
        tid = target["id"]
        if tid not in results:
            report.append(f"| {target['name']} | *Skipped* | - | - | - | - | ⚪ Skipped |")
            continue
            
        r = results[tid]
        diff_count = len(r["mismatched"]) + len(r["local_only"]) + len(r["remote_only"]) + len(r["errors"])
        status_label = "🟢 Aligned" if diff_count == 0 else "🟡 Drifted"
        
        report.append(
            f"| {target['name']} | {r['matched']} | {len(r['mismatched'])} | {len(r['local_only'])} | {len(r['remote_only'])} | {len(r['errors'])} | {status_label} |"
        )
        
    report.append("\n## 🔍 Audit Details\n")
    
    any_details = False
    for target in TARGETS:
        tid = target["id"]
        if tid not in results:
            continue
        r = results[tid]
        
        diff_count = len(r["mismatched"]) + len(r["local_only"]) + len(r["remote_only"]) + len(r["errors"])
        if diff_count == 0:
            continue
            
        any_details = True
        report.append(f"### 📁 {target['name']}\n")
        report.append("| File Path | Status | Detail / Reason |")
        report.append("| :--- | :--- | :--- |")
        
        # Mismatched files
        for f in r["mismatched"][:50]:  # Limit to 50 to avoid massive tables
            reason = r["reasons"].get(f, "md5 differ")
            report.append(f"| `{f}` | 🟡 Mismatched | {reason} |")
            
        # Local-only files
        for f in r["local_only"][:50]:
            report.append(f"| `{f}` | 🟢 Local Only (Staged) | File not found in remote |")
            
        # Remote-only files
        for f in r["remote_only"][:50]:
            report.append(f"| `{f}` | 🔵 Remote Only | File not found in local |")
            
        # Error files
        for f in r["errors"][:50]:
            report.append(f"| `{f}` | 🔴 Check Error | File check failed |")
            
        if diff_count > 50:
            report.append(f"\n*...and {diff_count - 50} more differences hidden for brevity.*")
        report.append("")
        
    if not any_details:
        report.append("*No differences to display. All staging directories and tracked files are in lockstep.*")
        
    report_content = "\n".join(report)
    
    # Save Report
    os.makedirs(os.path.dirname(REPORT_OUTPUT_PATH), exist_ok=True)
    with open(REPORT_OUTPUT_PATH, "w") as f:
        f.write(report_content)
        
    print(f"Report successfully compiled and written to: {REPORT_OUTPUT_PATH}")
    
    # Mirror/Stage the report to all 4 Notebook sync target directories
    for target in TARGETS[:-1]:
        stage_dir = target["local"]
        if os.path.exists(stage_dir):
            stage_path = os.path.join(stage_dir, "ground_vs_cloud_truth_report.md.txt")
            
            # Write with Last Sync Time prepended for NotebookLM compatibility
            with open(stage_path, "w") as f:
                f.write(f"**LAST SYNC TIME:** {audit_time}\n\n")
                f.write(report_content)
            print(f"Staged report to {stage_path}")
            
            # Immediately mirror the updated report file to Google Drive target
            try:
                remote_file_path = os.path.join(target["remote"], "ground_vs_cloud_truth_report.md.txt")
                cmd = ["rclone", "copyto", stage_path, remote_file_path, "--quiet"]
                subprocess.run(cmd, check=True)
                print(f"Uploaded report directly to remote: {remote_file_path}")
            except Exception as e:
                print(f"Warning: Failed to upload report directly to remote for {target['name']}: {e}")

if __name__ == "__main__":
    main()
