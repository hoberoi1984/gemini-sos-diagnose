import tarfile
import re
import json
import os
import sys
import io
from typing import Dict, Any, List
from collections import deque

class SOSParser:
    def __init__(self, path: str):
        self.path = path
        self.is_dir = os.path.isdir(path)
        self.root_dir = ""
        self.data = {
            "summary": {"hostname": "Unknown", "os": "Unknown"},
            "resources": {"memory": [], "disk": [], "load_avg": "Unknown", "threads": []},
            "cluster": {"nodes": [], "raw_status": ""},
            "logs": []
        }

    def _get_file_stream(self, tar, member_or_path):
        """Returns a line generator for a file inside either a tarball or a directory."""
        try:
            if self.is_dir:
                if (os.path.exists(member_or_path) and 
                    os.path.isfile(member_or_path) and 
                    not os.path.islink(member_or_path)):
                    f = open(member_or_path, 'rb')
                    return io.TextIOWrapper(f, encoding='utf-8', errors='ignore')
            else:
                f = tar.extractfile(member_or_path)
                if f:
                    return io.TextIOWrapper(f, encoding='utf-8', errors='ignore')
        except Exception:
            pass
        return None

    def parse(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {"error": f"Path {self.path} not found"}

        if self.is_dir:
            # Walk local directory structure
            for root, _, files in os.walk(self.path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.path).replace('\\', '/')
                    self._parse_file(None, full_path, rel_path)
        else:
            with tarfile.open(self.path, "r:*") as tar:
                members = tar.getmembers()
                if members:
                    self.root_dir = members[0].name.split('/')[0]

                for member in members:
                    # Ignore non-files and symlinks to avoid Windows host path crashes
                    if not member.isfile() or member.issym():
                        continue
                    self._parse_file(tar, member, member.name)

        return self.data

    def _parse_file(self, tar, file_ref, rel_path):
        """Processes a single file from the tarball or directory."""
        # Summary: Hostname
        if (rel_path.endswith("/hostname") or 
            rel_path == "hostname" or 
            rel_path.endswith("sos_commands/host/hostname")):
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                content = stream.read().strip()
                if content:
                    self.data["summary"]["hostname"] = content
                stream.close()

        # Summary: Redhat Release
        elif rel_path.endswith("/etc/redhat-release") or rel_path.endswith("etc/redhat-release"):
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                content = stream.read().strip()
                if content:
                    self.data["summary"]["os"] = content
                stream.close()

        # Resources: Uptime/Load Average
        elif rel_path.endswith("sos_commands/host/uptime") or rel_path.endswith("uptime"):
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                content = stream.read()
                load_match = re.search(r"load average:\s*(.*)", content)
                if load_match:
                    self.data["resources"]["load_avg"] = load_match.group(1).strip()
                stream.close()

        # Threads: ps -elfL
        elif rel_path.endswith("sos_commands/process/ps_-elfL"):
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                pids = {}
                next(stream, None)  # Skip header line
                for line in stream:
                    parts = line.split()
                    if len(parts) > 14:
                        pid = parts[3]
                        cmd = " ".join(parts[14:])[:50]
                        pids[pid] = pids.get(pid, {"cmd": cmd, "count": 0})
                        pids[pid]["count"] += 1

                sorted_threads = sorted(pids.items(), key=lambda x: x[1]["count"], reverse=True)
                self.data["resources"]["threads"] = [
                    {"pid": k, "cmd": v["cmd"], "threads": v["count"]} 
                    for k, v in sorted_threads[:10]
                ]
                stream.close()

        # Resources: Memory (free -m)
        elif "sos_commands/memory/free_-m" in rel_path:
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                for line in stream:
                    if line.startswith("Mem:"):
                        parts = line.split()
                        self.data["resources"]["memory"].append({
                            "type": "Physical", "total": parts[1], "used": parts[2], "free": parts[3],
                            "shared": parts[4], "buff_cache": parts[5], "available": parts[6]
                        })
                    elif line.startswith("Swap:"):
                        parts = line.split()
                        self.data["resources"]["memory"].append({
                            "type": "Swap", "total": parts[1], "used": parts[2], "free": parts[3]
                        })
                stream.close()

        # Resources: Disk space (df -h / df -al)
        elif ("sos_commands/filesys/df_-h" in rel_path or 
              "df_-al_-x_autofs" in rel_path or 
              "sos_commands/filesys/df_-al" in rel_path):
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                next(stream, None)  # Skip header
                pending_fs = None
                for line in stream:
                    parts = line.split()
                    if not parts:
                        continue
                    # Handle df line wrapping for long mount/filesystem names
                    if len(parts) == 1:
                        pending_fs = parts[0]
                        continue
                    if pending_fs:
                        parts = [pending_fs] + parts
                        pending_fs = None

                    if len(parts) >= 6:
                        # Prevent duplicate mounts from overwriting
                        if not any(d["mounted_on"] == parts[5] for d in self.data["resources"]["disk"]):
                            self.data["resources"]["disk"].append({
                                "filesystem": parts[0], "size": parts[1], "used": parts[2],
                                "avail": parts[3], "use_pct": parts[4], "mounted_on": parts[5]
                            })
                stream.close()

        # Logs: Diagnostic streaming
        elif "var/log/" in rel_path and not rel_path.endswith(".gz") and not rel_path.endswith(".xz") and not rel_path.endswith(".1"):
            stream = self._get_file_stream(tar, file_ref)
            if stream:
                name = rel_path.split("/")[-1]

                # Broad critical patterns consolidated from both versions
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
                    r"status=Timed Out",
                    r"kernel: \[.*\] [A-Z].*hung"
                ]
                combined_regex = re.compile("|".join(patterns), re.IGNORECASE)

                # Keep only last 200 matches using deque (O(1) memory footprint!)
                evidence_lines = deque(maxlen=200)
                error_count = 0
                for line in stream:
                    clean_line = line.rstrip()
                    if combined_regex.search(clean_line):
                        evidence_lines.append(clean_line)
                        error_count += 1

                # Save evidence
                evidence_list = list(evidence_lines)
                self.data["logs"].append({
                    "name": name,
                    "content": "\n".join(evidence_list) if evidence_list else "No direct evidence found.",
                    "error_count": error_count,
                    "recent_errors": evidence_list[-20:] if evidence_list else []
                })
                stream.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sos_parser.py <sosreport_tar_or_dir>")
        sys.exit(1)
    parser = SOSParser(sys.argv[1])
    print(json.dumps(parser.parse(), indent=2))