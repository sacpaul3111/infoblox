#!/usr/bin/env python3
"""
Generate simplified execution summary report.
Shows only suite-level tests (A Record, CNAME Record, Network) with pass/fail status.
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
        dict: Test suite information including status, time, pipeline, etc.
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
        end_time = status_elem.get('endtime', '') if status_elem is not None else ''

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
            record_type = 'A Record'
        elif 'CNAME' in suite_name or 'cname' in suite_name.lower():
            record_type = 'CNAME Record'
        elif 'Network' in suite_name or 'network' in suite_name.lower():
            record_type = 'Network'

        return {
            'record_type': record_type,
            'status': status,
            'execution_time': execution_time,
            'suite_name': suite_name
        }
    except Exception as e:
        print(f"[WARN] Failed to parse {output_file}: {e}")
        return None


def get_json_file_info(base_path, record_type):
    """Get information about the JSON file used for this record type.

    Returns:
        dict: JSON file info (path, record count, etc.)
    """
    # Map record type to JSON filename
    json_map = {
        'A Record': 'a_record.json',
        'CNAME Record': 'cname_record.json',
        'Network': 'network.json'
    }

    json_filename = json_map.get(record_type, f'{record_type.lower().replace(" ", "_")}.json')

    # Look for JSON file in prod_changes (may not exist if cleaned up)
    grid_dirs = glob.glob(f'{base_path}/prod_changes/*')

    for grid_dir in grid_dirs:
        json_path = os.path.join(grid_dir, json_filename)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    record_count = len(data) if isinstance(data, list) else 1
                    grid_host = os.path.basename(grid_dir)
                    return {
                        'path': json_path,
                        'record_count': record_count,
                        'grid_host': grid_host,
                        'exists': True
                    }
            except:
                pass

    return {
        'path': 'N/A',
        'record_count': 0,
        'grid_host': 'N/A',
        'exists': False
    }


def collect_test_executions(base_path):
    """Collect all test executions from history files.

    Returns:
        list: List of test execution records
    """
    executions = []

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
            except:
                file_timestamp = 'N/A'

            # Parse the XML file
            test_info = parse_robot_output(xml_file)

            if test_info:
                # Use file timestamp if execution_time is N/A
                if test_info['execution_time'] == 'N/A':
                    test_info['execution_time'] = file_timestamp

                # Add check type and filename
                test_info['check_type'] = check_type
                test_info['filename'] = filename

                # Try to extract pipeline ID from filename or XML
                pipeline_id = 'N/A'
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    # Look for pipeline ID in metadata or tags
                    for tag in root.findall('.//tag'):
                        if 'Pipeline' in tag.text or 'pipeline' in tag.text.lower():
                            pipeline_id = tag.text.split(':')[-1].strip()
                            break
                except:
                    pass

                test_info['pipeline_id'] = pipeline_id

                executions.append(test_info)

    # Sort by execution time (most recent first)
    executions.sort(key=lambda x: x['execution_time'], reverse=True)

    return executions


def generate_html_report(executions, output_file, grid_host=None, pipeline_id=None):
    """Generate simplified HTML execution report."""

    # Calculate summary statistics
    total_tests = len(executions)
    passed_tests = sum(1 for e in executions if e['status'] == 'PASS')
    failed_tests = sum(1 for e in executions if e['status'] == 'FAIL')

    # Group by record type for unique count
    unique_record_types = set(e['record_type'] for e in executions)

    # Get environment variables
    env_grid_host = os.environ.get('GRID_HOST', grid_host or 'N/A')
    env_pipeline_id = os.environ.get('CI_PIPELINE_ID', pipeline_id or 'N/A')
    env_record_type = os.environ.get('RECORD_TYPE', 'N/A')
    env_operation = os.environ.get('OPERATION_TYPE', 'N/A')

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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        /* Banner */
        .banner {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .banner h1 {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .banner .subtitle {{
            font-size: 16px;
            opacity: 0.9;
            margin-bottom: 30px;
        }}
        .stats-container {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 30px;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 20px 30px;
            min-width: 150px;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 8px;
        }}
        .stat-value {{
            font-size: 42px;
            font-weight: 700;
        }}
        .stat-value.success {{
            color: #10b981;
        }}
        .stat-value.danger {{
            color: #ef4444;
        }}

        /* Pipeline Info */
        .pipeline-info {{
            background: #f8f9fa;
            padding: 20px 40px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .pipeline-info .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .info-item {{
            display: flex;
            flex-direction: column;
        }}
        .info-label {{
            font-size: 12px;
            color: #6b7280;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .info-value {{
            font-size: 16px;
            color: #111827;
            font-weight: 500;
        }}

        /* Content */
        .content {{
            padding: 40px;
        }}

        h2 {{
            font-size: 24px;
            color: #111827;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}

        /* Test Table */
        .test-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 20px;
        }}
        .test-table thead {{
            background: #f9fafb;
        }}
        .test-table th {{
            padding: 16px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .test-table td {{
            padding: 16px;
            border-bottom: 1px solid #f3f4f6;
        }}
        .test-table tbody tr {{
            transition: background-color 0.2s;
        }}
        .test-table tbody tr:hover {{
            background-color: #f9fafb;
        }}

        /* Status Badge */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            gap: 6px;
        }}
        .status-badge.pass {{
            background: #d1fae5;
            color: #065f46;
        }}
        .status-badge.fail {{
            background: #fee2e2;
            color: #991b1b;
        }}
        .status-icon {{
            font-size: 16px;
        }}

        /* Record Type Badge */
        .record-type {{
            font-weight: 600;
            font-size: 15px;
            color: #111827;
        }}

        /* Time */
        .execution-time {{
            color: #6b7280;
            font-size: 14px;
        }}

        /* Pipeline ID */
        .pipeline-id {{
            font-family: 'Courier New', monospace;
            background: #f3f4f6;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 13px;
            color: #4b5563;
        }}

        /* JSON Info */
        .json-info {{
            font-size: 13px;
            color: #6b7280;
        }}
        .json-info .count {{
            font-weight: 600;
            color: #4b5563;
        }}

        /* Footer */
        .footer {{
            background: #f9fafb;
            padding: 20px 40px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
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
            <div class="subtitle">Comprehensive overview of test executions across all pipelines</div>

            <div class="stats-container">
                <div class="stat-box">
                    <div class="stat-label">Total Tests</div>
                    <div class="stat-value">{total_tests}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Passed</div>
                    <div class="stat-value success">{passed_tests}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value danger">{failed_tests}</div>
                </div>
            </div>
        </div>

        <!-- Pipeline Info -->
        <div class="pipeline-info">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Grid Host</div>
                    <div class="info-value">{env_grid_host}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Pipeline ID</div>
                    <div class="info-value">#{env_pipeline_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Record Type</div>
                    <div class="info-value">{env_record_type}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Operation</div>
                    <div class="info-value">{env_operation}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Generated</div>
                    <div class="info-value">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
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
                        <th>Test Suite</th>
                        <th>Status</th>
                        <th>Executed On</th>
                        <th>Pipeline</th>
                        <th>JSON Data</th>
                    </tr>
                </thead>
                <tbody>
"""

        base_path = 'infoblox_mvp1'  # Default base path

        for execution in executions:
            record_type = execution['record_type']
            status = execution['status']
            exec_time = execution['execution_time']
            pipeline = execution.get('pipeline_id', env_pipeline_id)

            # Get JSON file info
            json_info = get_json_file_info(base_path, record_type)
            json_display = f"{json_info['record_count']} records from {json_info['grid_host']}" if json_info['exists'] else "N/A"

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
                                <span class="status-icon">{status_icon}</span>
                                {status}
                            </span>
                        </td>
                        <td>
                            <div class="execution-time">{exec_time}</div>
                        </td>
                        <td>
                            <span class="pipeline-id">#{pipeline}</span>
                        </td>
                        <td>
                            <div class="json-info">
                                <span class="count">{json_display}</span>
                            </div>
                        </td>
                    </tr>
"""

        html_content += """
                </tbody>
            </table>
"""

    html_content += """
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated by Robot Framework Execution Tracker | Data tracked using ExecutionCounter.py and merge_reports.py</p>
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

    # Collect all test executions
    executions = collect_test_executions(base_path)

    print(f"\nFound {len(executions)} test execution(s)")

    # Ensure output directory exists
    output_dir = f'{base_path}/robot_reports'
    os.makedirs(output_dir, exist_ok=True)

    # Generate HTML report
    output_file = f'{output_dir}/execution_summary.html'

    # Get environment variables for context
    grid_host = os.environ.get('GRID_HOST')
    pipeline_id = os.environ.get('CI_PIPELINE_ID')

    generate_html_report(executions, output_file, grid_host, pipeline_id)

    print("\n[OK] Execution summary report generation complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
