#!/usr/bin/env python3
"""
Generate simplified execution summary report.
Combines pre and post checks into single test entry with merged status.
"""

import json
import os
import sys
import glob
from datetime import datetime
from xml.etree import ElementTree as ET


def parse_robot_output(output_file):
    """Parse Robot Framework output.xml to extract suite-level test info.

    Returns:
        dict: Test suite information including status, time, etc.
    """
    try:
        tree = ET.parse(output_file)
        root = tree.getroot()

        # Get suite info
        suite = root.find('.//suite[@name]')
        if suite is None:
            return None

        suite_name = suite.get('name', 'Unknown')

        # Get status
        status_elem = suite.find('status')
        status = status_elem.get('status', 'UNKNOWN') if status_elem is not None else 'UNKNOWN'

        # Get timestamps
        start_time = status_elem.get('starttime', '') if status_elem is not None else ''

        # Parse timestamp (format: 20250120 16:45:30.123)
        execution_time = 'N/A'
        if start_time:
            try:
                dt = datetime.strptime(start_time.split('.')[0], '%Y%m%d %H:%M:%S')
                execution_time = dt.strftime('%Y-%m-%d %H:%M')
            except:
                execution_time = start_time

        # Determine record type from suite name
        record_type = 'Unknown'
        if 'A Record' in suite_name or 'a_record' in suite_name.lower():
            record_type = 'a_record'
        elif 'CNAME' in suite_name or 'cname' in suite_name.lower():
            record_type = 'cname_record'
        elif 'Network' in suite_name or 'network' in suite_name.lower():
            record_type = 'network'

        return {
            'record_type': record_type,
            'status': status,
            'execution_time': execution_time,
            'suite_name': suite_name
        }
    except Exception as e:
        print(f"[WARN] Failed to parse {output_file}: {e}")
        return None


def get_pipeline_id_from_filename(filename):
    """Try to extract pipeline ID from filename or return N/A."""
    # Filename format might be: output_20250120_164530.xml
    # Pipeline ID might be embedded, otherwise return N/A
    return os.environ.get('CI_PIPELINE_ID', 'N/A')


def collect_and_merge_test_executions(base_path):
    """Collect test executions from history files and merge pre/post checks.

    Returns:
        list: List of merged test execution records
    """
    # Dictionary to group tests by timestamp/pipeline
    test_groups = {}

    # Check both pre_check and post_check history
    for check_type in ['pre_check', 'post_check']:
        history_dir = f'{base_path}/robot_reports/{check_type}/history'

        if not os.path.exists(history_dir):
            continue

        # Get all output XML files
        xml_files = sorted(glob.glob(f'{history_dir}/output_*.xml'))

        for xml_file in xml_files:
            # Extract timestamp from filename: output_20250120_164530.xml
            filename = os.path.basename(xml_file)
            try:
                timestamp_str = filename.replace('output_', '').replace('.xml', '')
                # timestamp_str format: 20250120_164530
                dt = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                file_timestamp = dt.strftime('%Y-%m-%d %H:%M')
                group_key = timestamp_str  # Use timestamp as grouping key
            except:
                file_timestamp = 'N/A'
                group_key = filename

            # Parse the XML file
            test_info = parse_robot_output(xml_file)

            if test_info:
                # Use file timestamp if execution_time is N/A
                if test_info['execution_time'] == 'N/A':
                    test_info['execution_time'] = file_timestamp

                record_type = test_info['record_type']
                status = test_info['status']

                # Create a unique key for this test group (timestamp + record_type)
                unique_key = f"{group_key}_{record_type}"

                if unique_key not in test_groups:
                    test_groups[unique_key] = {
                        'record_type': record_type,
                        'execution_time': test_info['execution_time'],
                        'pre_status': None,
                        'post_status': None,
                        'group_key': group_key
                    }

                # Store pre or post status
                if check_type == 'pre_check':
                    test_groups[unique_key]['pre_status'] = status
                else:
                    test_groups[unique_key]['post_status'] = status

    # Convert grouped tests to final list with merged status
    merged_executions = []

    for unique_key, test_group in test_groups.items():
        pre_status = test_group['pre_status']
        post_status = test_group['post_status']

        # Determine final status: FAIL if either pre or post failed
        if pre_status == 'FAIL' or post_status == 'FAIL':
            final_status = 'FAIL'
        elif pre_status == 'PASS' and post_status == 'PASS':
            final_status = 'PASS'
        elif pre_status == 'PASS' or post_status == 'PASS':
            # At least one passed, other might be None
            final_status = 'PASS'
        else:
            final_status = 'UNKNOWN'

        merged_executions.append({
            'record_type': test_group['record_type'],
            'status': final_status,
            'execution_time': test_group['execution_time'],
            'pipeline_id': get_pipeline_id_from_filename(test_group['group_key']),
            'grid_host': os.environ.get('GRID_HOST', 'N/A'),
            'operation': os.environ.get('OPERATION_TYPE', 'N/A')
        })

    # Sort by execution time (most recent first)
    merged_executions.sort(key=lambda x: x['execution_time'], reverse=True)

    return merged_executions


def generate_html_report(executions, output_file):
    """Generate simplified HTML execution report."""

    # Calculate summary statistics
    total_tests = len(executions)
    passed_tests = sum(1 for e in executions if e['status'] == 'PASS')
    failed_tests = sum(1 for e in executions if e['status'] == 'FAIL')

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Summary</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        /* Banner */
        .banner {{
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
            color: white;
            padding: 30px 40px;
            text-align: center;
        }}
        .banner h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .stats-container {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            border-radius: 8px;
            padding: 15px 25px;
            min-width: 120px;
        }}
        .stat-label {{
            font-size: 13px;
            opacity: 0.9;
            margin-bottom: 6px;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: 600;
        }}

        /* Content */
        .content {{
            padding: 40px;
        }}

        h2 {{
            font-size: 20px;
            color: #111827;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        /* Test Table */
        .test-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
        }}
        .test-table thead {{
            background: #f3f4f6;
        }}
        .test-table th {{
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .test-table td {{
            padding: 14px 16px;
            border-bottom: 1px solid #f3f4f6;
            font-size: 14px;
        }}
        .test-table tbody tr {{
            transition: background-color 0.15s;
        }}
        .test-table tbody tr:hover {{
            background-color: #f9fafb;
        }}
        .test-table tbody tr:last-child td {{
            border-bottom: none;
        }}

        /* Status Badge */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            padding: 5px 14px;
            border-radius: 16px;
            font-weight: 600;
            font-size: 13px;
            gap: 5px;
        }}
        .status-badge.pass {{
            background: #d1fae5;
            color: #065f46;
        }}
        .status-badge.fail {{
            background: #fee2e2;
            color: #991b1b;
        }}

        /* Record Type */
        .record-type {{
            font-weight: 600;
            font-size: 14px;
            color: #111827;
        }}

        /* Cell styling */
        .cell-value {{
            color: #4b5563;
            font-size: 14px;
        }}

        /* Pipeline ID */
        .pipeline-id {{
            font-family: 'Courier New', monospace;
            background: #f3f4f6;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 13px;
            color: #4b5563;
            display: inline-block;
        }}

        /* Footer */
        .footer {{
            background: #f9fafb;
            padding: 20px 40px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 13px;
        }}

        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #6b7280;
        }}
        .empty-state-icon {{
            font-size: 64px;
            margin-bottom: 20px;
            opacity: 0.5;
        }}
        .empty-state-text {{
            font-size: 18px;
            margin-bottom: 10px;
        }}
        .empty-state-subtext {{
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Banner -->
        <div class="banner">
            <h1>🎯 Test Execution Summary</h1>

            <div class="stats-container">
                <div class="stat-box">
                    <div class="stat-label">Total Tests</div>
                    <div class="stat-value">{total_tests}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value">{passed_tests}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value">{failed_tests}</div>
                </div>
            </div>
        </div>

        <!-- Content -->
        <div class="content">
            <h2>Test Execution History</h2>
"""

    if not executions:
        html_content += """
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-text">No test executions found</div>
                <div class="empty-state-subtext">Test history will appear here after running the pipeline</div>
            </div>
"""
    else:
        html_content += """
            <table class="test-table">
                <thead>
                    <tr>
                        <th>Record Type</th>
                        <th>Status</th>
                        <th>Executed On</th>
                        <th>Grid Host</th>
                        <th>Pipeline</th>
                        <th>Operation</th>
                    </tr>
                </thead>
                <tbody>
"""

        for execution in executions:
            record_type = execution['record_type']
            status = execution['status']
            exec_time = execution['execution_time']
            pipeline = execution.get('pipeline_id', 'N/A')
            grid_host = execution.get('grid_host', 'N/A')
            operation = execution.get('operation', 'N/A')

            # Status badge
            status_class = 'pass' if status == 'PASS' else 'fail'
            status_icon = '✅' if status == 'PASS' else '❌'

            html_content += f"""
                    <tr>
                        <td>
                            <div class="record-type">{record_type}</div>
                        </td>
                        <td>
                            <span class="status-badge {status_class}">
                                <span>{status_icon}</span>
                                {status}
                            </span>
                        </td>
                        <td>
                            <div class="cell-value">{exec_time}</div>
                        </td>
                        <td>
                            <div class="cell-value">{grid_host}</div>
                        </td>
                        <td>
                            <span class="pipeline-id">#{pipeline}</span>
                        </td>
                        <td>
                            <div class="cell-value">{operation}</div>
                        </td>
                    </tr>
"""

        html_content += """
                </tbody>
            </table>
"""

    html_content += f"""
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated by Robot Framework Execution Tracker | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n[OK] HTML report generated: {output_file}")
    print(f"     Total tests: {total_tests}")
    print(f"     Passed: {passed_tests}")
    print(f"     Failed: {failed_tests}")


def main():
    """Main execution function."""
    base_path = sys.argv[1] if len(sys.argv) > 1 else 'infoblox_mvp1'

    print(f"Generating Execution Summary Report")
    print(f"Base Path: {base_path}")
    print("-" * 80)

    # Collect and merge test executions
    executions = collect_and_merge_test_executions(base_path)

    print(f"\nFound {len(executions)} merged test execution(s)")

    # Ensure output directory exists
    output_dir = f'{base_path}/robot_reports'
    os.makedirs(output_dir, exist_ok=True)

    # Generate HTML report
    output_file = f'{output_dir}/execution_summary.html'

    generate_html_report(executions, output_file)

    print("\n[OK] Execution summary report generation complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
