# Gemini SOS Analyzer

An expert diagnostic extension for Gemini CLI designed to analyze Linux `sosreport` archives. It automates log extraction, performs multi-node comparisons, and generates interactive visual dashboards to accelerate Root Cause Analysis (RCA).

## Features

- **Automated Extraction:** Rapidly extracts and parses logs from `sosreport` tarballs (`.tar.xz`, `.tar.gz`).
- **Expert Diagnostics:** Specialized in identifying OS crashes, network failures, PCS cluster issues, and performance bottlenecks.
- **Visual Dashboard:** Generates an interactive React-based dashboard for exploring logs, system metrics, and evidence.
- **Multi-Node Comparison:** Compares multiple reports (e.g., Node A vs. Node B) to pinpoint variances.
- **RCA Generation:** Provides structured Root Cause Analysis, Likely Causes, and Step-by-Step Remediation.

## Project Structure

- `skills/gemini-sos-analyzer/`: Core logic, including `SKILL.md` instructions and diagnostic scripts.
- `dashboard/`: A Vite + React application for interactive visualization of diagnostic data.
- `scripts/`: Python utilities for log extraction and JSON generation for the dashboard.

## Installation

This extension is typically installed via the Gemini CLI extension manager.

```bash
gemini extension install https://github.com/hoberoi1984/gemini-sos-diagnose
```

## Usage

### 1. Analyze a Sosreport
Provide one or more sosreport archives to Gemini:

```text
Analyze these sosreports: ./sosreport-node1.tar.xz ./sosreport-node2.tar.xz
```

Gemini will automatically:
1. Extract the logs using `extract_logs.py`.
2. Perform a deep-dive analysis.
3. Update the visual dashboard data.

### 2. View the Visual Report
Once analysis is complete, Gemini will update the local dashboard. You can view it by running the dashboard (typically on `http://localhost:5173`).

```bash
cd dashboard
npm install
npm run dev
```

## Technical Details

### Analysis Capabilities
- **System Metrics:** Correlates application failures with `free -m`, `slabinfo`, `dmesg`, and `ps`.
- **Network & Clusters:** Analyzes `ip`, `mount`, and `pcs` status.
- **Service Logs:** Inspects SSSD, Apache, Java OOM logs, and more.

### Platform Support
- **Host:** Windows (via Git Bash / MINGW64).
- **Guest:** Linux `sosreports`.
- **Commands:** Utilizes standard POSIX tools (`find`, `grep`, `cat`, `sort`) for analysis.

## Development

To modify the diagnostic logic, update the scripts in `skills/gemini-sos-analyzer/scripts/` or refine the expert instructions in `SKILL.md`.

### Prerequisites
- Python 3.x
- Node.js & npm (for dashboard)

---
*Built with ❤️ for Site Reliability Engineers.*
