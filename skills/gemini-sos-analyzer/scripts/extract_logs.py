#!/usr/bin/env python3
import tarfile, sys, os, re, io
from collections import deque

if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
    print("Error: Valid path to sosreport required.")
    sys.exit(1)

path = sys.argv[1]
err_pat = re.compile(
    r"(?i)(error|fail|fatal|panic|oom-killer|segfault|timeout|"
    r"split-brain|stonith|fencing)"
)

TARGET_LOGS = [
    "var/log/messages", "var/log/syslog", "var/log/dmesg",
    "var/log/maillog", "var/log/mail.log",
    "var/log/pacemaker/pacemaker.log",
    "var/log/cluster/corosync.log"
]

TARGET_CMDS = [
    "crm_mon", "pcs_status", "free_-m", "df_-h", "hostname",
    "df_-al", "ps_auxwww"
]

def process_stream(name, f):
    try:
        text_f = io.TextIOWrapper(f, encoding='utf-8', errors='ignore')
    except Exception:
        return ""
    
    out = f"\n=== FILE: {name} ===\n"
    if any(c in name for c in TARGET_CMDS):
        hdr = next(text_f, "").rstrip()
        tail = deque(text_f, 100)
        lines = [l.rstrip() for l in tail]
        out += "[COMMAND OUTPUT]\n"
        if hdr:
            out += hdr + "\n"
        out += "\n".join(lines)
        return out

    errs, tail, counts = deque(maxlen=30), deque(maxlen=50), {}
    for line in text_f:
        l = line.rstrip()
        tail.append(l)
        if err_pat.search(l):
            errs.append(l)
            norm = re.sub(
                r'\b\d{2}:\d{2}:\d{2}\b|\[\d+\]|0x[0-9a-f]+',
                '[SUB]', l
            )
            counts[norm] = counts.get(norm, 0) + 1

    if errs:
        total_matches = sum(counts.values())
        out += f"[CRITICAL ERRORS FOUND ({total_matches} total)]\n"
        spammers = sorted(
            counts.items(), key=lambda x: x[1], reverse=True
        )[:2]
        for k, v in spammers:
            if v > 5:
                out += f"  - Repeated {v}x: {k[:80]}...\n"
        out += f"[LAST {len(errs)} RECENT ERRORS]\n" + "\n".join(errs) + "\n\n"
    return out + f"[LAST {len(tail)} LINES OF LOG]\n" + "\n".join(tail)

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
else:
    with tarfile.open(path, "r:*") as tar:
        for m in tar.getmembers():
            if m.isfile() and not m.issym():
                is_log = any(m.name.endswith(lg) for lg in TARGET_LOGS)
                is_cmd = any(c in m.name for c in TARGET_CMDS)
                if is_log or is_cmd:
                    f = tar.extractfile(m)
                    if f:
                        summary += process_stream(m.name, f)

print("--- CRITICAL LOGS & CLUSTER STATES EXTRACTED ---\n" + summary)