#!/usr/bin/env python3
import tarfile
import sys
import os
import re

if len(sys.argv) < 2:
    print("Error: Please provide the path to the sosreport tarball.")
    sys.exit(1)

file_location = sys.argv[1]

if not os.path.exists(file_location):
    print(f"Error: File {file_location} not found.")
    sys.exit(1)

# Compile a regex to catch critical errors across all logs
error_pattern = re.compile(r"(?i)(error|fail|fatal|panic|oom-killer|segfault|timeout|reject|connection refused|split-brain)")

# Define the highly specific files we care about based on your domains
TARGET_LOGS = [
    # General OS
    "var/log/messages", "var/log/syslog", "var/log/dmesg",          
    # Mail & Cluster (Your specific domains)
    "var/log/maillog", "var/log/mail.log", "var/log/exim",          
    "var/log/pacemaker/pacemaker.log", "var/log/cluster/corosync.log",
    
    # --- ADDED BROAD APP SUPPORT ---
    # Web Servers
    "var/log/nginx/error.log", "var/log/httpd/error_log", "var/log/apache2/error.log",
    # Databases
    "var/log/mysql/error.log", "var/log/postgresql/postgresql",
    # Containers
    "var/log/containers/", "var/log/docker/"
]

# Define sosreport command outputs we want to capture fully
TARGET_COMMANDS = [
    "sos_commands/pacemaker/crm_mon", "sos_commands/pacemaker/pcs_status", 
    "sos_commands/networking/ip_-s_-d_link", "sos_commands/networking/ss_-tlnp", 
    "sos_commands/memory/free_-m", "sos_commands/filesys/df_-h", "sos_commands/host/hostname", 
    "sos_commands/filesys/df_-al", "sos_commands/process/ps_auxwww"            
]

def process_file(member_name, file_obj):
    """Reads a file, extracts errors, and grabs the tail context."""
    try:
        content = file_obj.read().decode('utf-8', errors='ignore').splitlines()
    except Exception:
        return ""

    output = f"\n=== FILE: {member_name} ===\n"
    
    # For small command outputs, return the whole thing (up to 100 lines)
    if any(cmd in member_name for cmd in TARGET_COMMANDS):
        output += "[COMMAND OUTPUT]\n"
        output += "\n".join(content[-100:])
        return output

    # For large logs, use Smart Grepping + Tail Context
    errors_found = [line for line in content if error_pattern.search(line)]
    
    if errors_found:
        output += f"[CRITICAL ERRORS FOUND ({len(errors_found)} lines)]\n"
        # Only keep the last 30 errors to prevent flooding the context window
        output += "\n".join(errors_found[-30:]) + "\n\n"
    else:
        output += "[NO CRITICAL ERRORS FOUND]\n\n"

    output += "[LAST 50 LINES OF LOG]\n"
    output += "\n".join(content[-50:])
    
    return output

# Main extraction routine
log_summary = ""
try:
    with tarfile.open(file_location, "r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
                
            # Check if the file is one of our targets
            is_target_log = any(member.name.endswith(log) for log in TARGET_LOGS)
            is_target_cmd = any(cmd in member.name for cmd in TARGET_COMMANDS)
            
            if is_target_log or is_target_cmd:
                f = tar.extractfile(member)
                if f:
                    log_summary += process_file(member.name, f)
    
    print("--- CRITICAL LOGS & CLUSTER STATES EXTRACTED ---")
    print(log_summary)

except Exception as e:
    print(f"Extraction failed: {str(e)}")
