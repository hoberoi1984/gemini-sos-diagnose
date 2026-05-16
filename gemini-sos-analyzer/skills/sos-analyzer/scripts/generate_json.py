import tarfile
import re
import json
import os
import sys
import time
from typing import Dict, Any, List

class SOSParser:
    def __init__(self, tar_path: str):
        self.tar_path = tar_path
        self.root_dir = ""
        self.data = {
            "summary": {},
            "resources": {"memory": [], "disk": [], "load_avg": "", "threads": []},
            "cluster": {"nodes": [], "raw_status": ""},
            "logs": []
        }

    def _get_file_content(self, tar, member_name):
        try:
            f = tar.extractfile(member_name)
            if f:
                return f.read().decode('utf-8', errors='ignore')
        except:
            pass
        return ""

    def parse(self) -> Dict[str, Any]:
        if not os.path.exists(self.tar_path):
            return {"error": "File not found"}

        with tarfile.open(self.tar_path, "r:*") as tar:
            members = tar.getmembers()
            if members:
                self.root_dir = members[0].name.split('/')[0]

            for member in members:
                # Summary & Load
                if member.name.endswith("/hostname"):
                    self.data["summary"]["hostname"] = self._get_file_content(tar, member).strip()
                elif member.name.endswith("/etc/redhat-release"):
                    self.data["summary"]["os"] = self._get_file_content(tar, member).strip()
                elif member.name.endswith("sos_commands/host/uptime"):
                    content = self._get_file_content(tar, member)
                    load_match = re.search(r"load average: (.*)", content)
                    if load_match:
                        self.data["resources"]["load_avg"] = load_match.group(1)

                # Threads (from ps -elfL)
                elif member.name.endswith("sos_commands/process/ps_-elfL"):
                    content = self._get_file_content(tar, member)
                    lines = content.splitlines()
                    pids = {}
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) > 14:
                            pid = parts[3]
                            cmd = " ".join(parts[14:])[:50]
                            pids[pid] = pids.get(pid, {"cmd": cmd, "count": 0})
                            pids[pid]["count"] += 1
                    
                    sorted_threads = sorted(pids.items(), key=lambda x: x[1]["count"], reverse=True)
                    self.data["resources"]["threads"] = [{"pid": k, "cmd": v["cmd"], "threads": v["count"]} for k, v in sorted_threads[:10]]

                # Resources
                elif "sos_commands/memory/free_-m" in member.name:
                    content = self._get_file_content(tar, member)
                    for line in content.splitlines():
                        if line.startswith("Mem:"):
                            parts = line.split()
                            self.data["resources"]["memory"].append({
                                "type": "Physical", "total": parts[1], "used": parts[2], "free": parts[3],
                                "shared": parts[4], "buff_cache": parts[5], "available": parts[6]
                            })
                elif "sos_commands/filesys/df_-h" in member.name or "df_-al_-x_autofs" in member.name:
                    content = self._get_file_content(tar, member)
                    lines = content.splitlines()
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 6:
                            self.data["resources"]["disk"].append({
                                "filesystem": parts[0], "size": parts[1], "used": parts[2],
                                "avail": parts[3], "use_pct": parts[4], "mounted_on": parts[5]
                            })

                # Logs
                elif any(member.name.endswith(l) for l in ["var/log/messages", "var.log.messages.tailed", "var/log/dmesg", "var/log/cluster/corosync.log", "var/log/pacemaker/pacemaker.log"]):
                    name = member.name.split("/")[-1]
                    lines = self._get_file_content(tar, member).splitlines()
                    
                    patterns = [
                        r"failed to run tailer",
                        r"permission denied",
                        r"nfs.*not responding",
                        r"Preauthentication failed",
                        r"Failed to initialize credentials",
                        r"alloy.*level=error",
                        r"oom-killer",
                        r"RegisterEC2Agent.*does not exist",
                        r"CCPC.*exec-time=[3-9]\d{4}ms",
                        r"terminated \(reboot\) by ue1pl-ccpc-app",
                        r"rc=193",
                        r"forbidden",
                        r"certificate.*expired",
                        r"certificate verify failed",
                        r"failed to assign",
                        r"Error retrieving metadata",
                        r"Download failed",
                        r"timed out after \d+ms",
                        r"Timer expired",
                        r"Processing failed start of vmfence",
                        r"unpack_rsc_op_failure",
                        r"check_migration_threshold",
                        r"status=Timed Out"
                    ]
                    combined_regex = re.compile("|".join(patterns), re.IGNORECASE)
                    
                    evidence_lines = [l for l in lines if combined_regex.search(l)]
                    evidence_lines = evidence_lines[-200:]

                    self.data["logs"].append({
                        "name": name,
                        "content": "\n".join(evidence_lines) if evidence_lines else "No direct evidence found.",
                        "error_count": len(evidence_lines),
                        "recent_errors": evidence_lines[-20:]
                    })


        return self.data

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_json.py <tar_path> [analysis_json_file]")
        return

    tar_path = sys.argv[1]
    parser = SOSParser(tar_path)
    data = parser.parse()
    data['version'] = time.time()

    # If an analysis file is provided, merge it
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        with open(sys.argv[2], 'r') as f:
            data['analysis'] = json.load(f)

    # Output to the React app's directory
    # We prioritize the 'dashboard' folder within the extension, but fall back to CWD
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.abspath(os.path.join(script_dir, "..", "..", "..", "dashboard", "diagnostic_data.json"))
    
    if os.path.exists(os.path.dirname(dashboard_path)):
        output_path = dashboard_path
    else:
        output_path = "diagnostic_data.json"

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"--- DASHBOARD UPDATED: {output_path} ---")

if __name__ == "__main__":
    main()
