#!/usr/bin/env python3
"""
Script to merge multiple Robot Framework test runs into a single report.
This allows tracking test execution history over time.
"""

import os
import sys
import glob
import shutil
from datetime import datetime
from robot import rebot


def merge_robot_reports(report_type='pre_check', max_history=10, base_path='infoblox_mvp1'):
    """
    Merge multiple Robot Framework test runs into a combined report.

    Args:
        report_type: Type of report (pre_check or post_check)
        max_history: Maximum number of historical runs to keep
        base_path: Base path for robot_reports directory (default: infoblox_mvp1)
    """
    base_dir = f"{base_path}/robot_reports/{report_type}"
    history_dir = f"{base_dir}/history"

    # Create history directory if it doesn't exist
    os.makedirs(history_dir, exist_ok=True)

    # Get current output.xml
    current_output = f"{base_dir}/output.xml"

    if not os.path.exists(current_output):
        print(f"No current output file found: {current_output}")
        return False

    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Copy current output to history
    history_output = f"{history_dir}/output_{timestamp}.xml"
    shutil.copy2(current_output, history_output)
    print(f"Saved current run to: {history_output}")

    # Get all historical output files
    output_files = sorted(glob.glob(f"{history_dir}/output_*.xml"))

    # Keep only the most recent runs
    if len(output_files) > max_history:
        for old_file in output_files[:-max_history]:
            os.remove(old_file)
            print(f"Removed old history file: {old_file}")
        output_files = output_files[-max_history:]

    print(f"\nMerging {len(output_files)} test runs...")

    # Merge all outputs into combined report
    try:
        rebot(
            *output_files,
            name=f"{report_type.replace('_', ' ').title()} - Combined History",
            outputdir=base_dir,
            output=f"{base_dir}/combined_output.xml",
            log=f"{base_dir}/combined_log.html",
            report=f"{base_dir}/combined_report.html",
            merge=True
        )

        print(f"\n✓ Successfully merged reports!")
        print(f"  Combined report: {base_dir}/combined_report.html")
        print(f"  Combined log: {base_dir}/combined_log.html")
        print(f"  Total runs merged: {len(output_files)}")

        return True

    except Exception as e:
        print(f"✗ Error merging reports: {str(e)}")
        return False


def generate_statistics_report(report_type='pre_check', base_path='infoblox_mvp1'):
    """
    Generate a statistics report showing test execution trends.

    Args:
        report_type: Type of report (pre_check or post_check)
        base_path: Base path for robot_reports directory (default: infoblox_mvp1)
    """
    history_dir = f"{base_path}/robot_reports/{report_type}/history"

    if not os.path.exists(history_dir):
        print(f"No history directory found: {history_dir}")
        return

    output_files = sorted(glob.glob(f"{history_dir}/output_*.xml"))

    if not output_files:
        print(f"No historical test runs found in: {history_dir}")
        return

    print(f"\n{'='*80}")
    print(f"Test Execution Statistics - {report_type.replace('_', ' ').title()}")
    print(f"{'='*80}")
    print(f"Total test runs: {len(output_files)}")
    print(f"History location: {history_dir}")
    print(f"\nHistorical runs:")

    for idx, output_file in enumerate(output_files, 1):
        filename = os.path.basename(output_file)
        timestamp_str = filename.replace('output_', '').replace('.xml', '')

        try:
            # Parse timestamp
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {idx:2d}. {formatted_date}")
        except:
            print(f"  {idx:2d}. {filename}")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    # Get report type from command line argument
    report_type = sys.argv[1] if len(sys.argv) > 1 else 'pre_check'
    max_history = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    base_path = sys.argv[3] if len(sys.argv) > 3 else 'infoblox_mvp1'

    print(f"Robot Framework Report Merger")
    print(f"Report Type: {report_type}")
    print(f"Max History: {max_history}")
    print(f"Base Path: {base_path}")
    print("-" * 80)

    # Generate statistics before merging
    generate_statistics_report(report_type, base_path)

    # Merge reports
    success = merge_robot_reports(report_type, max_history, base_path)

    if success:
        print("\n✓ Report merging completed successfully!")
        print(f"\n📊 VIEW REPORTS:")
        print(f"   Current Run:  {base_path}/robot_reports/{report_type}/report.html")
        print(f"   📈 HISTORY:   {base_path}/robot_reports/{report_type}/combined_report.html ⭐")
        print(f"   History Dir:  {base_path}/robot_reports/{report_type}/history/")
    else:
        print("\n✗ Report merging failed!")
        sys.exit(1)
