# Gemini CLI SOS Analyzer Extension

A custom skill/extension for the Gemini CLI that acts as an automated, full-stack Site Reliability Engineer (SRE). It allows Gemini to safely parse, extract, and diagnose massive Linux `sosreport` archives without breaking token limits.

## Supported Technologies
This extension specifically targets and extracts data for:
* **Operating System:** Kernel panics, OOM events, general faults (`dmesg`, `syslog`, `messages`)
* **High Availability (PCS):** Pacemaker & Corosync split-brains, quorum loss, and `crm_mon` states
* **Networking:** Interface states and socket statistics (`ip link`, `ss`)
* **Mail Routing:** Postfix and Exim relay/timeout issues (`maillog`)
* **Enterprise Apps:** Web servers (Nginx/Apache), Databases (MySQL/PostgreSQL), and Containers (Docker)

## How it Works
Feeding a multi-gigabyte `.tar.xz` file directly into an LLM will break the context window. Instead, this extension uses a bundled Python script to crack open the archive locally and perform **Smart Grepping**:
1. **Targeted Scanning:** It only extracts specific log files and command outputs based on the technologies listed above.
2. **Error Isolation:** It scans massive logs specifically for critical keywords (`error`, `fatal`, `timeout`, `panic`, `split-brain`) and pulls only the exact moments of failure.
3. **State Capture:** It captures the actual system state commands saved by the `sosreport` (like `free -m` and `df -h`) so Gemini can correlate application crashes with infrastructure constraints.

## Installation

Install directly via the Gemini CLI using:

```bash
gemini extensions install https://github.com/osttra/gemini-sos-analyzer
