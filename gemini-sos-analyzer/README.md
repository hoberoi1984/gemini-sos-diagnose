# Gemini CLI SOS Analyzer Extension

A custom skill/extension for the Gemini CLI that acts as an automated, full-stack Site Reliability Engineer (SRE). It allows Gemini to safely parse, extract, and diagnose massive Linux `sosreport` archives without breaking token limits.

## Key Features
* **Automated Log Extraction:** Bundled Python scripts crack open multi-gigabyte `.tar.xz` archives locally, extracting only the most relevant telemetry.
* **Smart Error Isolation:** Scans massive logs for critical keywords (`error`, `fatal`, `timeout`, `panic`, `split-brain`) and correlates them with system metrics.
* **Hardware & Thermal Health:** Detects CPU thermal throttling, core temperature spikes, and hardware failures via `dmesg` and IPMI logs.
* **Cluster Troubleshooting:** Deep analysis of Pacemaker/Corosync stacks, including custom OCF agent metadata failures and fencing history.
* **Interactive Visual Dashboard:** Automatically synchronizes Root Cause Analysis (RCA) findings to a local React-based dashboard for easy visualization.

## Supported Technologies
* **Operating System:** Kernel panics, OOM events, segment faults, and storage timeouts.
* **High Availability (PCS):** Pacemaker quorum loss, resource migration failures, and OCF agent compliance.
* **Networking:** Interface drops, socket exhaustion, and routing inconsistencies.
* **Enterprise Apps:** SSSD/LDAP authentication, Web servers (Nginx/Apache), and Database integrity (Oracle, MySQL).

## How it Works
1. **Targeted Scanning:** The extension identifies specific log files and command outputs (e.g., `ps`, `free`, `df`, `pcs status`) within the archive.
2. **Context Compression:** Instead of feeding raw logs to the LLM, it extracts high-signal "smoking gun" evidence and context.
3. **Dashboard Sync:** RCA findings are written to `diagnostic_data.json`, which feeds a local Vite+React application for interactive log viewing.

## Installation

Install directly via the Gemini CLI using:

```bash
gemini extensions install <your-github-repo-url>
```

## Frontend & Dashboard Setup
The extension includes a Vite + React dashboard for visualizing diagnostic data. To run it locally:

1. **Navigate to the dashboard directory**:
   ```bash
   cd gemini-sos-analyzer/dashboard
   ```
2. **Install dependencies**:
   ```bash
   npm install
   ```
3. **Start the development server**:
   ```bash
   npm run dev
   ```
4. **Access the UI**: Open [http://localhost:5173](http://localhost:5173) in your browser.

## Usage
Once installed, simply provide a path to a sosreport:
> "gemini refer the sosreport and diagnose kernel: CPU15: Core temperature above threshold"

After Gemini completes the analysis, the dashboard will automatically refresh with the latest Root Cause Analysis and log evidence.
