# Robot Framework - Test Execution Tracking & Historical Reports

## Overview

The Robot Framework integration now includes **automatic execution tracking** and **historical report merging**. Every time your tests run in the GitLab pipeline, the system:

1. ✅ Tracks how many times each test has been executed
2. ✅ Records timestamps for first and last runs
3. ✅ Saves the current test results to history
4. ✅ Merges up to 20 historical runs into a combined report
5. ✅ Displays execution statistics in the test logs

## Features

### 1. Execution Counter

**Location:**
- `robot_reports/pre_check/execution_counter.json`
- `robot_reports/post_check/execution_counter.json`

**Tracks:**
```json
{
  "Pre-Check Validation Suite": {
    "count": 15,
    "first_run": "2025-10-01T14:30:22.123456",
    "last_run": "2025-10-04T19:45:33.987654",
    "history": [
      {
        "timestamp": "2025-10-04T19:45:33.987654",
        "run_number": 15
      }
    ]
  },
  "Authentication Test": {
    "count": 15,
    "first_run": "2025-10-01T14:30:25.234567",
    "last_run": "2025-10-04T19:45:35.876543",
    "history": [...]
  }
}
```

### 2. Historical Report Merging

**How it works:**

1. After each test run, the `output.xml` file is saved to the `history/` folder with a timestamp
2. The merge script combines up to 20 most recent runs
3. A combined report is generated showing trends across all runs

**Report Types:**

| Report Type | Description | Use Case |
|-------------|-------------|----------|
| `report.html` | Current run only | View latest execution results |
| `combined_report.html` | Merged history (up to 20 runs) | View trends and historical analysis |
| `log.html` | Current run detailed log | Debug current run |
| `combined_log.html` | Merged historical logs | Debug across multiple runs |

### 3. Historical Data Storage

```
robot_reports/
├── pre_check/
│   ├── report.html                    # ← Latest run
│   ├── combined_report.html           # ← Historical trends (20 runs)
│   ├── execution_counter.json         # ← Execution counts
│   ├── log.html
│   ├── combined_log.html
│   ├── output.xml
│   ├── combined_output.xml
│   └── history/
│       ├── output_20251001_143022.xml # Run 1
│       ├── output_20251001_150135.xml # Run 2
│       ├── output_20251002_091545.xml # Run 3
│       └── ...                        # Up to 20 most recent
└── post_check/
    └── [same structure]
```

## What You'll See

### In the Test Logs

At the **start** of each test suite:

```
================================================================================
TEST EXECUTION STATISTICS
================================================================================
Total unique tests: 4
Total test executions: 127

Test execution counts:
  • Pre-Check Validation Suite: 32 runs
    Last run: 2025-10-04 19:45:23
  • Authentication Test: 32 runs
    Last run: 2025-10-04 19:45:25
  • A Record Validation: 31 runs
    Last run: 2025-10-04 19:45:28
  • CNAME Record Validation: 32 runs
    Last run: 2025-10-04 19:45:31
================================================================================
```

At the **end** of each test suite:

```
📊 Test 'Pre-Check Validation Suite' - Execution #33
✅ Total test suite executions: 128
```

### In the GitLab Pipeline Logs

```
[OK] Pre-check validation passed

Merging with historical test runs...
================================================================================
Test Execution Statistics - Pre Check
================================================================================
Total test runs: 20
History location: robot_reports/pre_check/history

Historical runs:
   1. 2025-10-01 14:30:22
   2. 2025-10-01 15:01:35
   3. 2025-10-02 09:15:45
   ...
  20. 2025-10-04 19:45:33
================================================================================

Merging 20 test runs...

✓ Successfully merged reports!
  Combined report: robot_reports/pre_check/combined_report.html
  Combined log: robot_reports/pre_check/combined_log.html
  Total runs merged: 20

[OK] Test history merged successfully
  - Current run: infoblox_mvp1/robot_reports/pre_check/report.html
  - Combined history: infoblox_mvp1/robot_reports/pre_check/combined_report.html
```

### In the Combined Report (HTML)

The `combined_report.html` shows:

1. **Overall Statistics**
   - Total: Number of tests across all runs
   - Passed: Total passed across all runs
   - Failed: Total failed across all runs

2. **Individual Run Details**
   - Each run is shown as a separate suite
   - Timestamp for each run
   - Pass/fail status for each run

3. **Trends**
   - Visual representation of test stability
   - Identify flaky tests (inconsistent pass/fail)
   - Track performance changes over time

## Configuration

### Maximum Historical Runs

By default, the system keeps **20** historical runs. To change this:

**In `.gitlab-ci.yml`:**
```yaml
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 30  # Keep 30 runs
python3 infoblox_mvp1/utils/robot/merge_reports.py post_check 50 # Keep 50 runs
```

### Maximum History Entries per Test

Execution counter keeps the last **50** runs for each test. To change this, edit `utils/robot/ExecutionCounter.py`:

```python
# Keep only last 100 runs in history
if len(self.counter_data[test_name]['history']) > 100:
    self.counter_data[test_name]['history'] = self.counter_data[test_name]['history'][-100:]
```

## Benefits

### 1. Test Stability Tracking

See which tests pass consistently vs. which ones are flaky:

- **Stable test**: Passed 20/20 runs
- **Flaky test**: Passed 15/20 runs (investigate!)
- **Consistently failing**: Failed 20/20 runs (fix required)

### 2. Performance Trends

Track execution time over multiple runs:

- Identify tests that are getting slower
- Spot performance regressions
- Optimize slow tests

### 3. Audit Trail

Complete history of all test executions:

- When tests were run
- How many times
- Success/failure patterns
- Compliance and auditing

### 4. Trend Analysis

Understand test behavior over time:

- Are tests becoming more reliable?
- Are new changes introducing failures?
- Which tests run most frequently?

## Viewing Reports in GitLab

### Current Run Only

1. Navigate to your pipeline
2. Click on `pre_check` or `post_implementation` job
3. Click "Browse" under Job Artifacts
4. Open `infoblox_mvp1/robot_reports/[stage]/report.html`

### Historical Trends

1. Navigate to your pipeline
2. Click on `pre_check` or `post_implementation` job
3. Click "Browse" under Job Artifacts
4. Open `infoblox_mvp1/robot_reports/[stage]/combined_report.html` ← **Historical trends**

## Manual Report Merging

You can manually merge reports using the script:

```bash
# Merge pre_check reports (keep last 20)
python utils/robot/merge_reports.py pre_check 20

# Merge post_check reports (keep last 30)
python utils/robot/merge_reports.py post_check 30
```

## Execution Counter API

The `ExecutionCounter` library provides these keywords:

### Initialize Execution Counter
```robot
Initialize Execution Counter    ${COUNTER_FILE}
```

### Record a Test Execution
```robot
${count}=    Record Test Execution    My Test Name
Log    This test has run ${count} times
```

### Get Execution Count
```robot
${count}=    Get Test Execution Count    My Test Name
```

### Get Total Executions
```robot
${total}=    Get Total Test Executions
```

### Log Statistics
```robot
Log Execution Statistics
```

### Save Counter
```robot
Save Execution Counter
```

## Example Output

### Execution Counter JSON

```json
{
  "Pre-Check Validation Suite": {
    "count": 32,
    "first_run": "2025-10-01T14:30:22.123456",
    "last_run": "2025-10-04T19:45:33.987654",
    "history": [
      {
        "timestamp": "2025-10-01T14:30:22.123456",
        "run_number": 1
      },
      {
        "timestamp": "2025-10-01T15:01:35.234567",
        "run_number": 2
      },
      ...
      {
        "timestamp": "2025-10-04T19:45:33.987654",
        "run_number": 32
      }
    ]
  }
}
```

### Combined Report Statistics

When you open `combined_report.html`, you'll see:

```
Test Execution Statistics
─────────────────────────────────────────
Total Test Runs:     20
Date Range:          2025-10-01 to 2025-10-04
Total Tests:         4
Total Executions:    80 (4 tests × 20 runs)

Test Pass Rates:
  • Authentication Test:        20/20 (100%)  ✅
  • A Record Validation:         19/20 (95%)  ⚠️
  • CNAME Record Validation:     20/20 (100%) ✅
  • Network Validation:          20/20 (100%) ✅
```

## Troubleshooting

### Reports Not Merging

**Issue:** "No historical test runs found"

**Solution:** This is normal for the first run. History will build up over time.

### Old History Files Not Deleted

**Issue:** Too many history files in the `history/` folder

**Solution:** The script automatically keeps only the most recent N runs (default: 20). Older files are deleted automatically.

### Execution Counter Reset

**Issue:** Execution count went back to 1

**Solution:** The `execution_counter.json` file may have been deleted. The counter will rebuild from scratch.

## Data Persistence

### GitLab Artifacts

By default, GitLab artifacts (including reports) expire after **1 week**. The execution counter and history are stored in these artifacts.

**To keep data longer:**

Edit `.gitlab-ci.yml`:
```yaml
artifacts:
  expire_in: 30 days  # Or 90 days, 1 year, etc.
```

**Note:** If artifacts expire, the counter and history will be lost. New executions will start from count 1.

## Summary

✅ **Automatic tracking** - No manual work required
✅ **Historical trends** - See test behavior over 20 runs
✅ **Execution counts** - Know how many times tests have run
✅ **Audit trail** - Complete history of test executions
✅ **Flaky test detection** - Identify unstable tests
✅ **Performance tracking** - Monitor execution time trends
✅ **GitLab integration** - All reports available as artifacts

---

**Key Files:**
- `robot_reports/[stage]/report.html` - Latest run
- `robot_reports/[stage]/combined_report.html` - Historical trends
- `robot_reports/[stage]/execution_counter.json` - Execution counts
- `robot_reports/[stage]/history/` - Historical XML files
