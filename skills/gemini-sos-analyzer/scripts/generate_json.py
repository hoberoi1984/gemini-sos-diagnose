#!/usr/bin/env python3
import os
import sys
import json
import time
from sos_parser import SOSParser

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_json.py <tar_or_dir_path> [analysis_json_file]")
        return

    tar_path = sys.argv[1]

    # Initialize the single, optimized consolidated parser
    parser = SOSParser(tar_path)
    data = parser.parse()
    data['version'] = time.time()

    # If an analysis file is provided, merge it
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        try:
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                data['analysis'] = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load analysis file: {e}")

    # Resolve output path dynamically
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Path 1: Relative location inside development/global workspace
    dev_dashboard_path = os.path.abspath(
        os.path.join(script_dir, "..", "..", "..", "dashboard", "diagnostic_data.json")
    )

    # Path 2: Global Gemini extension installation folder in user home directory
    home_dir = os.path.expanduser("~")
    global_dashboard_path = os.path.abspath(
        os.path.join(
            home_dir,
            ".gemini", "extensions", "gemini-sos-analyzer",
            "dashboard", "diagnostic_data.json"
        )
    )

    # Path Priority Evaluation
    if os.path.exists(os.path.dirname(dev_dashboard_path)):
        output_path = dev_dashboard_path
    elif os.path.exists(os.path.dirname(global_dashboard_path)):
        output_path = global_dashboard_path
    else:
        output_path = "diagnostic_data.json"

    # Safely write the consolidated JSON telemetry data
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"--- DASHBOARD UPDATED: {output_path} ---")
    except Exception as e:
        print(f"Error: Failed to write dashboard file: {e}")

if __name__ == "__main__":
    main()