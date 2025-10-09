# Enhanced GitLab CI Pipeline Guide

## Overview

The enhanced pipeline (`.gitlab-ci-enhanced.yml`) integrates **ExecutionCounter.py** and **merge_reports.py** to provide comprehensive test execution tracking and historical reporting.

## Key Enhancements

### 1. **Execution Counter Integration**

The pipeline now tracks every test execution using `ExecutionCounter.py`:

- **Counter Files**: `infoblox_mvp1/robot_reports/execution_counters/`
  - `pre_check_counter.json` - Pre-check validation execution counts
  - `post_check_counter.json` - Post-implementation verification counts

- **Tracked Data**:
  - Total execution count per test
  - First run timestamp
  - Last run timestamp
  - Execution history (last 50 runs)

### 2. **Historical Report Merging**

Uses `merge_reports.py` to combine multiple test runs:

- **History Storage**: `infoblox_mvp1/robot_reports/{pre_check|post_check}/history/`
- **Combined Reports**:
  - `combined_report.html` - Merged view of all test runs
  - `combined_log.html` - Detailed logs across runs
  - `combined_output.xml` - XML format for programmatic access

- **Retention**: Keeps last 20 test runs (configurable)

### 3. **Execution Statistics Dashboard**

New stage: `generate_execution_report`

Generates comprehensive HTML dashboard showing:
- Total unique tests executed
- Total execution counts (pre-check and post-check)
- Test-by-test breakdown with timestamps
- Execution trends and history

**Output**: `infoblox_mvp1/robot_reports/execution_summary.html`

## Pipeline Stages

```
build-container → file-processing → pre-implementation → deploy → post-implementation → reporting
```

### Stage Details

#### 1. **build-container**
- Builds Docker container (manual/on Dockerfile change)
- No changes from original pipeline

#### 2. **file-processing**
- Processes CSV input to JSON
- Validates input data
- **Enhancement**: Adds Pipeline ID to output

#### 3. **pre-implementation**
- **server_connection_test**: Network connectivity check
- **pre_check**: Robot Framework validation with execution tracking
  - Initializes execution counter
  - Runs validation tests
  - Merges with historical reports
  - Commits results to repository
- **json_validation**: Validates JSON structure

#### 4. **deploy**
- **run_ansible_playbook**: Executes Ansible deployment
- No changes from original pipeline

#### 5. **post-implementation**
- Runs Robot Framework verification tests
- Tracks execution counts
- Merges with historical reports
- Commits results and execution counters
- Performs file cleanup

#### 6. **reporting** ⭐ NEW
- Generates comprehensive execution statistics
- Creates HTML dashboard
- Displays console summaries
- Commits execution summary report

## How Execution Tracking Works

### In Robot Framework Tests

Add ExecutionCounter library to your test suite:

```robot
*** Settings ***
Library    ExecutionCounter

*** Variables ***
${COUNTER_FILE}    %{COUNTER_FILE}

*** Test Cases ***
My Test Case
    Initialize Execution Counter    ${COUNTER_FILE}
    Record Test Execution    My Test Case
    # ... test logic ...
    Save Execution Counter
```

### Pipeline Variables

The pipeline passes these variables to Robot Framework:

- `GRID_HOST`: Target Infoblox grid
- `RECORD_TYPE`: DNS record type
- `OPERATION_TYPE`: add or delete
- `PIPELINE_ID`: GitLab pipeline ID
- `COUNTER_FILE`: Path to execution counter JSON

### Automatic Integration

The pipeline automatically:
1. Creates counter directories
2. Passes counter file path to tests
3. Collects execution data
4. Merges historical reports
5. Commits results to repository
6. Generates summary dashboard

## Viewing Execution Reports

### 1. **Current Run Reports**

- Pre-check: `infoblox_mvp1/robot_reports/pre_check/report.html`
- Post-check: `infoblox_mvp1/robot_reports/post_check/report.html`

### 2. **Combined Historical Reports**

- Pre-check history: `infoblox_mvp1/robot_reports/pre_check/combined_report.html`
- Post-check history: `infoblox_mvp1/robot_reports/post_check/combined_report.html`

### 3. **Execution Statistics Dashboard**

- Overall statistics: `infoblox_mvp1/robot_reports/execution_summary.html`
- Shows all-time execution counts and trends

### 4. **GitLab CI Artifacts**

Each pipeline job stores artifacts:
- Reports expire in 1 week (configurable)
- Execution summary expires in 1 month
- Access via GitLab UI: `CI/CD → Pipelines → [Pipeline ID] → Browse`

## Git Commit Messages

The pipeline creates detailed commit messages:

### Pre-Check Example:
```
Pre-check PASSED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]
```

### Post-Implementation Example:
```
Post-implementation PASSED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 52]
```

### Execution Report Example:
```
Update execution statistics report [Pipeline: 12345]
```

## Configuration Options

### Adjusting History Retention

In `.gitlab-ci-enhanced.yml`, modify the merge_reports.py call:

```bash
# Keep last 20 runs (default)
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 20

# Keep last 50 runs
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 50
```

### Artifact Retention

Modify `expire_in` values:

```yaml
artifacts:
  when: always
  paths:
    - infoblox_mvp1/robot_reports/pre_check/
  expire_in: 1 week  # Change to: 2 weeks, 1 month, etc.
```

## Execution Counter Data Format

### JSON Structure

```json
{
  "Test Name": {
    "count": 15,
    "first_run": "2025-10-01T10:30:00",
    "last_run": "2025-10-08T14:45:00",
    "history": [
      {
        "timestamp": "2025-10-08T14:45:00",
        "run_number": 15
      }
    ]
  }
}
```

### Fields

- **count**: Total number of times test has executed
- **first_run**: ISO timestamp of first execution
- **last_run**: ISO timestamp of most recent execution
- **history**: Array of last 50 executions with timestamps

## Troubleshooting

### Execution Counter Not Updating

**Check**:
1. Counter file path is correct in Robot test
2. `Save Execution Counter` keyword is called
3. Git commits are successful
4. Artifacts include `execution_counters/` directory

**Fix**:
```bash
# Verify counter file exists
ls -la infoblox_mvp1/robot_reports/execution_counters/

# Check JSON validity
python3 -c "import json; print(json.load(open('infoblox_mvp1/robot_reports/execution_counters/pre_check_counter.json')))"
```

### Historical Reports Not Merging

**Check**:
1. `merge_reports.py` exits successfully
2. History directory exists
3. Output.xml files are present

**Fix**:
```bash
# Manually run merge
cd infoblox_mvp1
python3 utils/robot/merge_reports.py pre_check 20

# Check history directory
ls -la robot_reports/pre_check/history/
```

### Git Push Failures

**Symptoms**: Reports not appearing in repository

**Fix**:
- Pipeline retries 3 times automatically
- Check GitLab token permissions
- Verify network connectivity
- Review Git configuration

## Comparison: Original vs Enhanced Pipeline

| Feature | Original Pipeline | Enhanced Pipeline |
|---------|------------------|-------------------|
| Test execution | ✅ Yes | ✅ Yes |
| Current run reports | ✅ Yes | ✅ Yes |
| Execution counting | ❌ No | ✅ Yes |
| Historical reports | ❌ No | ✅ Yes (20 runs) |
| Execution statistics | ❌ No | ✅ Yes (HTML dashboard) |
| Commit messages | Basic | Detailed with counts |
| Pipeline ID tracking | ❌ No | ✅ Yes |
| Reporting stage | ❌ No | ✅ Yes |

## Migration from Original Pipeline

### Step 1: Rename Files

```bash
# Backup original pipeline
cp .gitlab-ci.yml .gitlab-ci.yml.backup

# Use enhanced pipeline
cp .gitlab-ci-enhanced.yml .gitlab-ci.yml
```

### Step 2: Update Robot Tests (Optional)

Add ExecutionCounter to your test suites:

```robot
*** Settings ***
Library    ExecutionCounter

*** Variables ***
${COUNTER_FILE}    %{COUNTER_FILE}    # Passed from pipeline

*** Test Cases ***
Test With Execution Tracking
    Initialize Execution Counter    ${COUNTER_FILE}
    Record Test Execution    Test With Execution Tracking
    # ... your test logic ...
    Log Execution Statistics
    Save Execution Counter
```

### Step 3: Commit and Push

```bash
git add .gitlab-ci.yml
git commit -m "Upgrade to enhanced pipeline with execution tracking"
git push origin main
```

### Step 4: Run Pipeline

1. Go to GitLab UI: `CI/CD → Pipelines → Run Pipeline`
2. Select environment, record type, operation
3. Paste CSV data
4. Run pipeline
5. View execution summary after completion

## Best Practices

### 1. **Regular Monitoring**

- Review execution summary weekly
- Check for test failures in historical reports
- Monitor execution counts for anomalies

### 2. **Counter File Maintenance**

- Counters persist across pipeline runs
- Stored in repository for continuity
- Backed up with repository backups

### 3. **Report Retention**

- Artifacts expire automatically
- Historical reports stored in repository
- Clone repository for permanent archival

### 4. **Test Suite Organization**

- Group related tests in same suite
- Use descriptive test names
- Include execution counter in all suites

## Advanced Usage

### Custom Execution Reports

Create custom Python scripts to analyze counter data:

```python
import json

with open('infoblox_mvp1/robot_reports/execution_counters/pre_check_counter.json') as f:
    data = json.load(f)

# Find most executed test
most_executed = max(data.items(), key=lambda x: x[1]['count'])
print(f"Most executed: {most_executed[0]} ({most_executed[1]['count']} runs)")

# Calculate average executions
avg_executions = sum(t['count'] for t in data.values()) / len(data)
print(f"Average executions per test: {avg_executions:.2f}")
```

### Integrating with External Systems

Export execution data:

```bash
# Export as CSV
python3 << EOF
import json
import csv

with open('infoblox_mvp1/robot_reports/execution_counters/pre_check_counter.json') as f:
    data = json.load(f)

with open('executions.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Test Name', 'Execution Count', 'Last Run'])
    for name, info in data.items():
        writer.writerow([name, info['count'], info['last_run']])
EOF
```

## Support and Feedback

For issues or questions:

1. Check this guide first
2. Review pipeline logs in GitLab
3. Examine execution counter JSON files
4. Contact the automation team

## Summary

The enhanced pipeline provides:

- ✅ **Full execution tracking** with ExecutionCounter.py
- ✅ **Historical report merging** with merge_reports.py
- ✅ **Comprehensive statistics dashboard** (HTML)
- ✅ **20 runs of historical data** (configurable)
- ✅ **Detailed commit messages** with execution counts
- ✅ **Automatic repository updates** with test results
- ✅ **New reporting stage** for statistics generation

This gives complete visibility into test execution history and trends!
