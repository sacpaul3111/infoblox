#!/usr/bin/env python3
"""
Generate comprehensive execution report from Robot Framework execution counters.
Creates both console statistics and HTML dashboard.
"""

import json
import os
import sys
from datetime import datetime


def load_counter_data(counter_file):
    """Load execution counter data from JSON file.

    Args:
        counter_file: Path to the execution counter JSON file

    Returns:
        dict: Counter data or empty dict if file doesn't exist
    """
    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load counter file {counter_file}: {e}")
            return {}
    return {}


def generate_statistics_report(report_type, counter_file):
    """Generate detailed statistics report to console.

    Args:
        report_type: Type of report (e.g., 'Pre-Check', 'Post-Check')
        counter_file: Path to the counter JSON file
    """
    data = load_counter_data(counter_file)

    if not data:
        print(f"\n[WARNING] No execution data found for {report_type}")
        return

    print(f"\n{'='*80}")
    print(f"  {report_type.upper().replace('_', ' ')} EXECUTION STATISTICS")
    print(f"{'='*80}")

    total_tests = len(data)
    total_executions = sum(test['count'] for test in data.values())

    print(f"\nTotal Unique Tests: {total_tests}")
    print(f"Total Test Executions: {total_executions}")
    print(f"\n{'-'*80}")
    print(f"{'Test Name':<50} {'Executions':>15} {'Last Run':>15}")
    print(f"{'-'*80}")

    # Sort by execution count (descending)
    sorted_tests = sorted(
        data.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )

    for test_name, test_data in sorted_tests:
        count = test_data['count']
        last_run = test_data.get('last_run', 'N/A')

        # Format last run timestamp
        if last_run != 'N/A':
            try:
                dt = datetime.fromisoformat(last_run)
                last_run_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                last_run_str = 'N/A'
        else:
            last_run_str = 'N/A'

        # Truncate test name if too long
        display_name = test_name[:47] + '...' if len(test_name) > 50 else test_name

        print(f"{display_name:<50} {count:>15} {last_run_str:>15}")

    print(f"{'-'*80}")
    print(f"{'TOTAL':<50} {total_executions:>15}")
    print(f"{'='*80}\n")


def generate_html_report(pre_check_data, post_check_data, output_file):
    """Generate HTML execution report.

    Args:
        pre_check_data: Pre-check counter data
        post_check_data: Post-check counter data
        output_file: Path where HTML report should be saved
    """
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Robot Framework Execution Report</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #6c757d;
            padding-bottom: 5px;
        }}
        .summary {{
            background-color: #e9ecef;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary-item {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .summary-label {{
            font-weight: bold;
            color: #495057;
        }}
        .summary-value {{
            font-size: 24px;
            color: #007bff;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #007bff;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #dee2e6;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 14px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 14px;
        }}
        .no-data {{
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Robot Framework Execution Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <div class="summary-item">
                <div class="summary-label">Pre-Check Tests</div>
                <div class="summary-value">{len(pre_check_data)}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Pre-Check Executions</div>
                <div class="summary-value">{sum(t['count'] for t in pre_check_data.values()) if pre_check_data else 0}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Post-Check Tests</div>
                <div class="summary-value">{len(post_check_data)}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Post-Check Executions</div>
                <div class="summary-value">{sum(t['count'] for t in post_check_data.values()) if post_check_data else 0}</div>
            </div>
        </div>
"""

    # Add Pre-Check table
    if pre_check_data:
        html_content += """
        <h2>Pre-Check Validation Tests</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Execution Count</th>
                    <th>First Run</th>
                    <th>Last Run</th>
                </tr>
            </thead>
            <tbody>
"""
        sorted_pre = sorted(pre_check_data.items(), key=lambda x: x[1]['count'], reverse=True)
        for test_name, data in sorted_pre:
            first_run = data.get('first_run', 'N/A')
            last_run = data.get('last_run', 'N/A')

            try:
                first_run_str = datetime.fromisoformat(first_run).strftime('%Y-%m-%d %H:%M') if first_run != 'N/A' else 'N/A'
                last_run_str = datetime.fromisoformat(last_run).strftime('%Y-%m-%d %H:%M') if last_run != 'N/A' else 'N/A'
            except:
                first_run_str = 'N/A'
                last_run_str = 'N/A'

            html_content += f"""
                <tr>
                    <td>{test_name}</td>
                    <td><strong>{data['count']}</strong></td>
                    <td>{first_run_str}</td>
                    <td>{last_run_str}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    else:
        html_content += """
        <h2>Pre-Check Validation Tests</h2>
        <div class="no-data">No pre-check execution data available yet. Run the pipeline to start tracking.</div>
"""

    # Add Post-Check table
    if post_check_data:
        html_content += """
        <h2>Post-Implementation Verification Tests</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Execution Count</th>
                    <th>First Run</th>
                    <th>Last Run</th>
                </tr>
            </thead>
            <tbody>
"""
        sorted_post = sorted(post_check_data.items(), key=lambda x: x[1]['count'], reverse=True)
        for test_name, data in sorted_post:
            first_run = data.get('first_run', 'N/A')
            last_run = data.get('last_run', 'N/A')

            try:
                first_run_str = datetime.fromisoformat(first_run).strftime('%Y-%m-%d %H:%M') if first_run != 'N/A' else 'N/A'
                last_run_str = datetime.fromisoformat(last_run).strftime('%Y-%m-%d %H:%M') if last_run != 'N/A' else 'N/A'
            except:
                first_run_str = 'N/A'
                last_run_str = 'N/A'

            html_content += f"""
                <tr>
                    <td>{test_name}</td>
                    <td><strong>{data['count']}</strong></td>
                    <td>{first_run_str}</td>
                    <td>{last_run_str}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    else:
        html_content += """
        <h2>Post-Implementation Verification Tests</h2>
        <div class="no-data">No post-check execution data available yet. Run the pipeline to start tracking.</div>
"""

    html_content += """
        <div class="footer">
            <p>This report shows the execution history of all Robot Framework tests.</p>
            <p>Data is tracked using ExecutionCounter.py and merged using merge_reports.py</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n[OK] HTML report generated: {output_file}")


def main():
    """Main execution function."""
    # Get base path from command line or use default
    base_path = sys.argv[1] if len(sys.argv) > 1 else 'infoblox_mvp1'

    print(f"Generating Execution Report")
    print(f"Base Path: {base_path}")
    print("-" * 80)

    # Define counter file paths
    pre_check_file = f'{base_path}/robot_reports/execution_counters/pre_check_counter.json'
    post_check_file = f'{base_path}/robot_reports/execution_counters/post_check_counter.json'

    # Load counter data
    pre_check_data = load_counter_data(pre_check_file)
    post_check_data = load_counter_data(post_check_file)

    # Generate console reports
    generate_statistics_report('Pre-Check', pre_check_file)
    generate_statistics_report('Post-Check', post_check_file)

    # Ensure output directory exists
    output_dir = f'{base_path}/robot_reports'
    os.makedirs(output_dir, exist_ok=True)

    # Generate HTML report
    output_file = f'{output_dir}/execution_summary.html'
    generate_html_report(pre_check_data, post_check_data, output_file)

    print("\n[OK] Execution statistics report generation complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
