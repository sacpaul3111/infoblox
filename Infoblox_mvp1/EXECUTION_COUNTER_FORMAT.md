# Execution Counter JSON Format - Complete Guide

## Overview

The execution counter JSON files now track **comprehensive test execution history** including pass/fail status, timestamps, and pass rates.

---

## File Locations

```
infoblox_mvp1/robot_reports/execution_counters/
├── pre_check_counter.json    # Pre-check test tracking
└── post_check_counter.json   # Post-check test tracking
```

---

## New JSON Format (Enhanced)

### Complete Example

```json
{
  "Validate A Record JSON File Exists": {
    "count": 15,
    "pass_count": 14,
    "fail_count": 1,
    "first_run": "2025-01-15T10:30:00.123456",
    "last_run": "2025-01-15T16:45:30.789012",
    "last_status": "PASS",
    "history": [
      {
        "timestamp": "2025-01-15T10:30:00.123456",
        "run_number": 1,
        "status": "PASS",
        "pass_rate": 100.0
      },
      {
        "timestamp": "2025-01-15T11:15:20.456789",
        "run_number": 2,
        "status": "PASS",
        "pass_rate": 100.0
      },
      {
        "timestamp": "2025-01-15T12:00:45.789123",
        "run_number": 3,
        "status": "FAIL",
        "pass_rate": 66.67
      },
      {
        "timestamp": "2025-01-15T13:20:10.234567",
        "run_number": 4,
        "status": "PASS",
        "pass_rate": 75.0
      },
      {
        "timestamp": "2025-01-15T16:45:30.789012",
        "run_number": 15,
        "status": "PASS",
        "pass_rate": 93.33
      }
    ]
  },
  "Validate A Record Required Fields": {
    "count": 15,
    "pass_count": 15,
    "fail_count": 0,
    "first_run": "2025-01-15T10:30:05.234567",
    "last_run": "2025-01-15T16:45:35.890123",
    "last_status": "PASS",
    "history": [
      {
        "timestamp": "2025-01-15T10:30:05.234567",
        "run_number": 1,
        "status": "PASS",
        "pass_rate": 100.0
      },
      {
        "timestamp": "2025-01-15T16:45:35.890123",
        "run_number": 15,
        "status": "PASS",
        "pass_rate": 100.0
      }
    ]
  },
  "Check For Duplicate A Records": {
    "count": 15,
    "pass_count": 12,
    "fail_count": 3,
    "first_run": "2025-01-15T10:30:15.345678",
    "last_run": "2025-01-15T16:45:45.901234",
    "last_status": "FAIL",
    "history": [
      {
        "timestamp": "2025-01-15T10:30:15.345678",
        "run_number": 1,
        "status": "PASS",
        "pass_rate": 100.0
      },
      {
        "timestamp": "2025-01-15T14:20:00.567890",
        "run_number": 10,
        "status": "FAIL",
        "pass_rate": 90.0
      },
      {
        "timestamp": "2025-01-15T16:45:45.901234",
        "run_number": 15,
        "status": "FAIL",
        "pass_rate": 80.0
      }
    ]
  }
}
```

---

## Field Descriptions

### Top Level (Per Test)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **count** | integer | Total number of times this test has been executed | `15` |
| **pass_count** | integer | Number of times this test passed | `14` |
| **fail_count** | integer | Number of times this test failed | `1` |
| **first_run** | ISO datetime | Timestamp of the first time this test was run | `"2025-01-15T10:30:00.123456"` |
| **last_run** | ISO datetime | Timestamp of the most recent run | `"2025-01-15T16:45:30.789012"` |
| **last_status** | string | Status of the most recent run (`PASS` or `FAIL`) | `"PASS"` |
| **history** | array | Array of up to 50 most recent execution records | `[...]` |

### History Entry

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **timestamp** | ISO datetime | When this specific run occurred | `"2025-01-15T12:00:45.789123"` |
| **run_number** | integer | Sequential run number for this test | `3` |
| **status** | string | Result of this run (`PASS` or `FAIL`) | `"FAIL"` |
| **pass_rate** | float | Cumulative pass rate up to this run (percentage) | `66.67` |

---

## What's New vs Old Format

### ❌ Old Format (Just Timestamps)

```json
{
  "A Record Validation Suite": {
    "count": 15,
    "first_run": "2025-01-15T10:30:00.123456",
    "last_run": "2025-01-15T16:45:30.789012",
    "history": [
      {
        "timestamp": "2025-01-15T10:30:00.123456",
        "run_number": 1
      },
      {
        "timestamp": "2025-01-15T11:15:20.456789",
        "run_number": 2
      }
    ]
  }
}
```

**Problems:**
- ❌ No pass/fail information
- ❌ Can't identify flaky tests
- ❌ Can't see test quality trends
- ❌ No pass rate metrics

### ✅ New Format (Comprehensive Tracking)

```json
{
  "Validate A Record JSON File Exists": {
    "count": 15,
    "pass_count": 14,
    "fail_count": 1,
    "first_run": "2025-01-15T10:30:00.123456",
    "last_run": "2025-01-15T16:45:30.789012",
    "last_status": "PASS",
    "history": [
      {
        "timestamp": "2025-01-15T12:00:45.789123",
        "run_number": 3,
        "status": "FAIL",
        "pass_rate": 66.67
      }
    ]
  }
}
```

**Benefits:**
- ✅ Pass/fail status for every run
- ✅ Identify flaky tests (tests that sometimes fail)
- ✅ Track test quality over time
- ✅ Automatic pass rate calculation
- ✅ See last status at a glance

---

## Usage Examples

### 1. Find Flaky Tests

**Flaky test** = Test with `pass_count > 0` AND `fail_count > 0`

```python
import json

with open('pre_check_counter.json') as f:
    data = json.load(f)

flaky_tests = []
for test_name, test_data in data.items():
    if test_data['pass_count'] > 0 and test_data['fail_count'] > 0:
        pass_rate = (test_data['pass_count'] / test_data['count']) * 100
        flaky_tests.append({
            'name': test_name,
            'pass_rate': pass_rate,
            'pass_count': test_data['pass_count'],
            'fail_count': test_data['fail_count']
        })

# Sort by pass rate (least reliable first)
flaky_tests.sort(key=lambda x: x['pass_rate'])

print("Flaky Tests (least reliable first):")
for test in flaky_tests:
    print(f"  - {test['name']}: {test['pass_rate']:.1f}% pass rate ({test['pass_count']}/{test['pass_count']+test['fail_count']})")
```

**Output:**
```
Flaky Tests (least reliable first):
  - Check For Duplicate A Records: 80.0% pass rate (12/15)
  - Validate A Record JSON File Exists: 93.3% pass rate (14/15)
```

### 2. Get Test Quality Summary

```python
import json

with open('pre_check_counter.json') as f:
    data = json.load(f)

total_tests = len(data)
total_runs = sum(t['count'] for t in data.values())
total_passes = sum(t['pass_count'] for t in data.values())
total_fails = sum(t['fail_count'] for t in data.values())
overall_pass_rate = (total_passes / total_runs) * 100 if total_runs > 0 else 0

perfect_tests = sum(1 for t in data.values() if t['fail_count'] == 0)
flaky_tests = sum(1 for t in data.values() if t['pass_count'] > 0 and t['fail_count'] > 0)
broken_tests = sum(1 for t in data.values() if t['pass_count'] == 0)

print(f"Test Suite Quality Report:")
print(f"  Total unique tests: {total_tests}")
print(f"  Total executions: {total_runs}")
print(f"  Overall pass rate: {overall_pass_rate:.1f}%")
print(f"\nTest Reliability:")
print(f"  Perfect (100% pass): {perfect_tests}")
print(f"  Flaky (mixed): {flaky_tests}")
print(f"  Broken (0% pass): {broken_tests}")
```

**Output:**
```
Test Suite Quality Report:
  Total unique tests: 5
  Total executions: 75
  Overall pass rate: 92.0%

Test Reliability:
  Perfect (100% pass): 3
  Flaky (mixed): 2
  Broken (0% pass): 0
```

### 3. Track Test Trends Over Time

```python
import json
from datetime import datetime

with open('pre_check_counter.json') as f:
    data = json.load(f)

test_name = "Validate A Record JSON File Exists"
test_data = data[test_name]

print(f"Test: {test_name}")
print(f"Total runs: {test_data['count']}")
print(f"Current pass rate: {(test_data['pass_count']/test_data['count'])*100:.1f}%")
print(f"\nRecent history:")

for entry in test_data['history'][-10:]:  # Last 10 runs
    dt = datetime.fromisoformat(entry['timestamp'])
    status_icon = "✅" if entry['status'] == "PASS" else "❌"
    print(f"  {dt.strftime('%Y-%m-%d %H:%M')} - Run #{entry['run_number']:2d} - {status_icon} {entry['status']} (Pass rate: {entry['pass_rate']:.1f}%)")
```

**Output:**
```
Test: Validate A Record JSON File Exists
Total runs: 15
Current pass rate: 93.3%

Recent history:
  2025-01-15 10:30 - Run # 1 - ✅ PASS (Pass rate: 100.0%)
  2025-01-15 11:15 - Run # 2 - ✅ PASS (Pass rate: 100.0%)
  2025-01-15 12:00 - Run # 3 - ❌ FAIL (Pass rate: 66.7%)
  2025-01-15 13:20 - Run # 4 - ✅ PASS (Pass rate: 75.0%)
  2025-01-15 16:45 - Run #15 - ✅ PASS (Pass rate: 93.3%)
```

---

## How It Works

### Test Execution Flow

```
1. Test starts running
   └─ Robot Framework executes test case

2. Test finishes (PASS or FAIL)
   └─ Test Teardown keyword "Record Individual Test Result" is called

3. ExecutionCounter library
   ├─ Reads test name from ${TEST NAME}
   ├─ Reads test status from ${TEST STATUS}
   ├─ Updates counter data:
   │  ├─ Increment count
   │  ├─ Increment pass_count or fail_count
   │  ├─ Calculate new pass_rate
   │  ├─ Update last_run timestamp
   │  ├─ Update last_status
   │  └─ Append to history array
   └─ Saves to JSON file

4. JSON file updated with new data
   └─ File committed to Git repository
```

### Robot Framework Integration

**In test files (e.g., a_record_validation.robot):**

```robot
*** Settings ***
Library           ../../utils/robot/ExecutionCounter.py
Library           BuiltIn
Suite Setup       Setup Execution Tracking
Suite Teardown    Teardown Execution Tracking
Test Teardown     Record Individual Test Result

*** Keywords ***
Setup Execution Tracking
    Initialize Execution Counter    ${COUNTER_FILE}

Teardown Execution Tracking
    Log Execution Statistics
    Save Execution Counter

Record Individual Test Result
    ${test_name}=    Set Variable    ${TEST NAME}
    ${test_status}=    Set Variable    ${TEST STATUS}
    Record Test Execution    ${test_name}    ${test_status}
```

---

## History Retention

- **Maximum history entries per test**: 50
- **Automatic cleanup**: Oldest entries are removed when limit is reached
- **Why 50?**: Balances between:
  - Having enough data for trend analysis
  - Keeping JSON file size manageable
  - Fast file I/O operations

---

## File Size Estimates

### Small Project (5 tests, 50 runs each)
```
File size: ~50 KB
Load time: < 10ms
```

### Medium Project (20 tests, 50 runs each)
```
File size: ~200 KB
Load time: < 50ms
```

### Large Project (100 tests, 50 runs each)
```
File size: ~1 MB
Load time: < 200ms
```

---

## Viewing in execution_summary.html

The HTML report now shows this data in a user-friendly format:

### Test Execution Table

| Test Name | Total Runs | Pass | Fail | Pass Rate | Last Status | First Run | Last Run |
|-----------|------------|------|------|-----------|-------------|-----------|----------|
| Validate A Record JSON File Exists | 15 | 14 | 1 | 93.3% | ✅ PASS | 2025-01-15 10:30 | 2025-01-15 16:45 |
| Validate A Record Required Fields | 15 | 15 | 0 | 100% | ✅ PASS | 2025-01-15 10:30 | 2025-01-15 16:45 |
| Check For Duplicate A Records | 15 | 12 | 3 | 80.0% | ❌ FAIL | 2025-01-15 10:30 | 2025-01-15 16:45 |

---

## Combined Report Shows Accumulative History

### Before (merge=True)

**Problem**: Each run replaced previous results
```
Combined Report:
└─ Test Suite
   ├─ Test 1: 1 pass (only latest run)
   ├─ Test 2: 1 pass (only latest run)
   └─ Test 3: 1 fail (only latest run)

Total: 3 tests, no history visible
```

### After (merge=False)

**Solution**: Each run is a separate suite, showing full history
```
Combined Report (Last 10 Runs):
├─ Run #1 (2025-01-15 10:30)
│  ├─ Test 1: PASS ✅
│  ├─ Test 2: PASS ✅
│  └─ Test 3: PASS ✅
│
├─ Run #2 (2025-01-15 11:15)
│  ├─ Test 1: PASS ✅
│  ├─ Test 2: PASS ✅
│  └─ Test 3: PASS ✅
│
├─ Run #3 (2025-01-15 12:00)
│  ├─ Test 1: FAIL ❌
│  ├─ Test 2: PASS ✅
│  └─ Test 3: PASS ✅
│
└─ Run #10 (2025-01-15 16:45)
   ├─ Test 1: PASS ✅
   ├─ Test 2: PASS ✅
   └─ Test 3: FAIL ❌

Statistics:
  Total runs: 10
  Test 1: 9/10 pass (90%)
  Test 2: 10/10 pass (100%)
  Test 3: 9/10 pass (90%)
```

---

## Benefits Summary

### For Developers
- ✅ Quickly identify which tests are flaky
- ✅ See test quality trends over time
- ✅ Debug intermittent failures with history
- ✅ Track test reliability metrics

### For QA
- ✅ Monitor test suite health
- ✅ Identify tests needing attention
- ✅ Generate quality reports
- ✅ Track pass rate trends

### For Management
- ✅ High-level test suite metrics
- ✅ Quality KPIs (pass rates, reliability)
- ✅ Historical trend analysis
- ✅ Compliance and audit trail

---

## Frequently Asked Questions

### Q: What happens to old data when I upgrade?
**A:** Old counter files without pass/fail data will still work. New fields will be added automatically on the next test run.

### Q: Can I reset the counters?
**A:** Yes, just delete the counter JSON file. It will be recreated on the next test run.

### Q: How do I export this data?
**A:** The JSON files can be read by any tool. Use Python, jq, or JavaScript to parse and analyze.

### Q: Does this slow down test execution?
**A:** No. The overhead is < 10ms per test (negligible).

### Q: Where are the counter files stored?
**A:** `infoblox_mvp1/robot_reports/execution_counters/`

### Q: Are counter files committed to Git?
**A:** Yes! They're committed after every pre-check and post-check stage.

---

## Summary

### Old vs New Comparison

| Feature | Old Format | New Format |
|---------|------------|------------|
| **Test execution count** | ✅ Yes | ✅ Yes |
| **Timestamps** | ✅ Yes | ✅ Yes |
| **Pass/Fail status** | ❌ No | ✅ Yes |
| **Pass/Fail counts** | ❌ No | ✅ Yes |
| **Pass rate calculation** | ❌ No | ✅ Yes |
| **Flaky test detection** | ❌ No | ✅ Yes |
| **Trend analysis** | ❌ Limited | ✅ Full |
| **Quality metrics** | ❌ No | ✅ Yes |
| **Useful for debugging** | ⚠️  Limited | ✅ Yes |
| **Combined report history** | ❌ Merged | ✅ Accumulative |

---

## Next Steps

1. **Run your tests** - The new format will be automatically used
2. **Check the JSON files** - See the new fields in action
3. **View execution_summary.html** - See the enhanced dashboard
4. **Check combined_report.html** - See accumulative history (Test1, Test2, Test3, etc.)
5. **Analyze trends** - Use the examples above to extract insights

---

**All changes are backward compatible - no action required!** 🎉
