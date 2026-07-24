#!/usr/bin/env python3
import tarfile, sys, os, re, io
from collections import deque
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("path", help="Path to sosreport")
parser.add_argument("--focus", default="all", choices=["all", "memory", "cluster", "network", "disk"])
args = parser.parse_args()
path = args.path

if not os.path.exists(path):
    print("Error: Valid path to sosreport required.")
    sys.exit(1)
err_pat = re.compile(
    r"(?i)(error|fail|fatal|panic|oom-killer|segfault|timeout|"
    r"split-brain|stonith|fencing)"
)

LOG_GROUPS = {
    "cluster": ["var/log/pacemaker/pacemaker.log", "var/log/cluster/corosync.log", "var/log/messages"],
    "memory": ["var/log/messages", "var/log/dmesg"],
    "network": ["var/log/messages", "var/log/syslog"],
    "disk": ["var/log/messages", "var/log/syslog"],
    "all": ["var/log/messages", "var/log/syslog", "var/log/dmesg", "var/log/maillog", "var/log/mail.log", "var/log/pacemaker/pacemaker.log", "var/log/cluster/corosync.log"]
}
CMD_GROUPS = {
    "cluster": ["crm_mon", "pcs_status", "hostname"],
    "memory": ["free_-m", "ps_auxwww", "hostname"],
    "network": ["hostname"],
    "disk": ["df_-h", "df_-al", "hostname"],
    "all": ["crm_mon", "pcs_status", "free_-m", "df_-h", "df_-al", "ps_auxwww", "hostname"]
}
TARGET_LOGS = LOG_GROUPS.get(args.focus, LOG_GROUPS["all"])
TARGET_CMDS = CMD_GROUPS.get(args.focus, CMD_GROUPS["all"])

def normalize_line(l):
    import re
    l = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\b", "[DATE]", l)
    l = re.sub(r"\b\d{4}-\d{2}-\d{2}(?:T|\b)", "[DATE]", l)
    l = re.sub(r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b", "[TIME]", l)
    l = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]", l)
    l = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "[UUID]", l, flags=re.IGNORECASE)
    l = re.sub(r"\[\d+\]|0x[0-9a-f]+", "[ID/HEX]", l, flags=re.IGNORECASE)
    return l

def process_cmd(name, text_f):
    out = f"\n=== FILE: {name} ===\n[COMMAND OUTPUT]\n"
    if "ps_auxwww" in name:
        lines = list(text_f)
        if not lines: return out + "Empty\n"
        header = lines[0].strip()
        procs = []
        for l in lines[1:]:
            parts = l.split(None, 10)
            if len(parts) >= 11:
                try:
                    cpu = float(parts[2])
                    mem = float(parts[3])
                    procs.append((cpu, mem, l.strip()))
                except ValueError:
                    pass
        top_cpu = sorted(procs, key=lambda x: x[0], reverse=True)[:5]
        top_mem = sorted(procs, key=lambda x: x[1], reverse=True)[:5]
        out += header + "\n--- TOP 5 CPU HOGS ---\n" + "\n".join(p[2] for p in top_cpu) + "\n"
        out += "--- TOP 5 MEMORY HOGS ---\n" + "\n".join(p[2] for p in top_mem) + "\n"
        return out
    elif "df_" in name:
        out += "--- DISKS > 80% OR IMPORTANT MOUNTS ---\n"
        header = next(text_f, "").strip()
        out += header + "\n"
        pending_fs = None
        for l in text_f:
            parts = l.split()
            if not parts: continue
            if len(parts) == 1: pending_fs = parts[0]; continue
            if pending_fs: parts = [pending_fs] + parts; pending_fs = None
            if len(parts) >= 6:
                fs = parts[0]; use_pct = parts[4].replace("%", ""); mnt = parts[5]
                if any(x in fs for x in ["squashfs", "tmpfs", "loop", "overlay", "shm"]): continue
                try:
                    if int(use_pct) >= 80 or mnt in ["/", "/var", "/tmp", "/boot"]: out += l.strip() + "\n"
                except ValueError: out += l.strip() + "\n"
        return out
    else:
        lines = [next(text_f, "").rstrip() for _ in range(50)]
        out += "\n".join(filter(None, lines)) + "\n"
        return out

def process_stream(name, f):
    import io
    from collections import deque
    try: text_f = io.TextIOWrapper(f, encoding="utf-8", errors="ignore")
    except Exception: return ""
    if any(c in name for c in TARGET_CMDS): return process_cmd(name, text_f)
    out = f"\n=== FILE: {name} ===\n"
    errs, tail, counts = deque(maxlen=30), deque(maxlen=50), {}
    for line in text_f:
        l = line.rstrip()
        tail.append(l)
        if err_pat.search(l):
            errs.append(l)
            norm = normalize_line(l)
            counts[norm] = counts.get(norm, 0) + 1
    if errs:
        out += f"[CRITICAL ERRORS FOUND ({sum(counts.values())} total)]\n"
        for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:2]:
            if v > 5: out += f"  - Repeated {v}x: {k[:80]}...\n"
        out += f"[LAST {len(errs)} RECENT ERRORS]\n" + "\n".join(errs) + "\n\n"
        out += f"[LAST {len(tail)} LINES OF LOG]\n" + "\n".join(tail)
        out += "[NO CRITICAL ERRORS DETECTED]\n"
    return out

summary = ""
if os.path.isdir(path):
    for r, _, files in os.walk(path):
        for fl in files:
            p = os.path.join(r, fl)
            rel = os.path.relpath(p, path).replace('\\', '/')
            is_log = any(rel.endswith(lg) for lg in TARGET_LOGS)
            is_cmd = any(c in rel for c in TARGET_CMDS)
            if (is_log or is_cmd) and os.path.isfile(p):
                if not os.path.islink(p):
                    with open(p, 'rb') as f:
                        summary += process_stream(rel, f)
elif tarfile.is_tarfile(path):
    with tarfile.open(path, "r:*") as tar:
        for m in tar.getmembers():
            if m.isfile() and not m.issym():
                is_log = any(m.name.endswith(lg) for lg in TARGET_LOGS)
                is_cmd = any(c in m.name for c in TARGET_CMDS)
                if is_log or is_cmd:
                    f = tar.extractfile(m)
                    if f:
                        summary += process_stream(m.name, f)

if summary:
    print(f"--- CRITICAL LOGS & CLUSTER STATES EXTRACTED (Focus: {args.focus.upper()}) ---\n" + summary)
else:
    print(f"--- NO RELEVANT LOGS FOUND (Focus: {args.focus.upper()}) ---")
