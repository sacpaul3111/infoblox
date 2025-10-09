# Visual Report Comparison

## Side-by-Side Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REPORT.HTML                                     │
│                         (Current Run Only)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Pre-Check Validation - a_record - Pipeline 12345                           │
│  Executed: 2025-10-08 10:00:00                                              │
│  Duration: 5.2 seconds                                                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │ Test Results                                                    │         │
│  ├────────────────────────────────────────────────────────────────┤         │
│  │ ✅ Validate A Record                               2.1s  PASS  │         │
│  │ ✅ Check Duplicate Records                         1.5s  PASS  │         │
│  │ ❌ Verify Required Fields                          0.8s  FAIL  │         │
│  │ ✅ Check IP Format                                 0.8s  PASS  │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
│  Statistics:                                                                 │
│  • Total: 4 tests                                                           │
│  • Passed: 3 (75%)                                                          │
│  • Failed: 1 (25%)                                                          │
│                                                                              │
│  ⚠️ You can only see THIS run's results                                     │
│  ⚠️ No historical context                                                   │
│  ⚠️ Can't tell if test is flaky or newly broken                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMBINED_REPORT.HTML ⭐                              │
│                    (Last 20 Runs Merged Together)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Pre Check - Combined History                                               │
│  Merged from 20 test executions                                             │
│  Time span: 2025-10-01 to 2025-10-08                                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │ Test Results (Historical View)                                 │         │
│  ├────────────────────────────────────────────────────────────────┤         │
│  │ Test: Validate A Record                                        │         │
│  │ ✅ Status: 20/20 PASS (100%)                                   │         │
│  │ │  First run: 2025-10-01 09:00                                │         │
│  │ │  Last run:  2025-10-08 10:00                                │         │
│  │ │  Trend: ✅ Stable - Always passes                            │         │
│  │ │                                                              │         │
│  │ Test: Check Duplicate Records                                  │         │
│  │ ✅ Status: 19/20 PASS (95%)                                    │         │
│  │ │  First run: 2025-10-01 09:00                                │         │
│  │ │  Last run:  2025-10-08 10:00                                │         │
│  │ │  Failed: 1 time (2025-10-04 11:30)                          │         │
│  │ │  Trend: ⚠️ Mostly stable - One failure                      │         │
│  │ │                                                              │         │
│  │ Test: Verify Required Fields                                   │         │
│  │ ⚠️ Status: 12/20 PASS (60%)                                    │         │
│  │ │  First run: 2025-10-01 09:00                                │         │
│  │ │  Last run:  2025-10-08 10:00                                │         │
│  │ │  Failed: 8 times (intermittent)                             │         │
│  │ │  Trend: 🔴 FLAKY - Needs investigation!                     │         │
│  │ │  Recent failures:                                            │         │
│  │ │    • 2025-10-08 10:00 ❌                                     │         │
│  │ │    • 2025-10-07 14:30 ❌                                     │         │
│  │ │    • 2025-10-06 09:15 ❌                                     │         │
│  │ │                                                              │         │
│  │ Test: Check IP Format                                          │         │
│  │ ✅ Status: 20/20 PASS (100%)                                   │         │
│  │ │  First run: 2025-10-01 09:00                                │         │
│  │ │  Last run:  2025-10-08 10:00                                │         │
│  │ │  Trend: ✅ Stable - Always passes                            │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
│  Combined Statistics:                                                        │
│  • Total executions: 80 (4 tests × 20 runs)                                │
│  • Passed: 71 (88.75%)                                                      │
│  • Failed: 9 (11.25%)                                                       │
│  • Time span: 7 days                                                        │
│                                                                              │
│  ✅ Shows ALL 20 historical runs                                            │
│  ✅ Identifies flaky tests (Verify Required Fields)                         │
│  ✅ Shows trends and stability                                              │
│  ✅ Provides historical context                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Example Scenario

### Scenario: Test "Verify Required Fields" just failed

#### Looking at report.html (Current Run Only):
```
❌ Verify Required Fields - FAIL

Error: Field 'view' is missing

Hmm... is this a new issue? 🤔
Has this test always failed?
Is my code broken or is the test flaky?
I don't know! 😕
```

#### Looking at combined_report.html (History):
```
⚠️ Verify Required Fields - 12/20 PASS (60%)

Failed 8 times out of 20 runs
Recent failures:
  • 2025-10-08 10:00 ❌
  • 2025-10-07 14:30 ❌
  • 2025-10-06 09:15 ❌
  • 2025-10-05 16:00 ✅ (passed!)
  • 2025-10-04 11:30 ❌

Aha! This test is FLAKY! 💡
It fails about 40% of the time.
This is a test issue, not my code.
I need to fix the test itself. ✅
```

## Real-World Example: Debugging a Failure

### Pipeline #12345 - Test Failed

**Step 1: Check report.html**
```
View: infoblox_mvp1/robot_reports/pre_check/report.html

Result:
❌ Validate A Record - FAIL
Error: Connection timeout to 10.74.3.80

Status: Failed
Time: 30.5s
```

**Question**: Is this a new issue or has it happened before?

**Step 2: Check combined_report.html**
```
View: infoblox_mvp1/robot_reports/pre_check/combined_report.html

Result:
Validate A Record - Execution History

Run #20 (2025-10-08 10:00): ❌ FAIL - Connection timeout
Run #19 (2025-10-07 14:30): ✅ PASS
Run #18 (2025-10-06 09:15): ✅ PASS
Run #17 (2025-10-05 16:00): ✅ PASS
...
Run #1  (2025-10-01 09:00): ✅ PASS

Overall: 19/20 PASS (95%)
```

**Answer**: This is a NEW failure! Test has been stable for 19 runs. Likely a temporary network issue, not a test problem.

## File Structure in Repository

```
infoblox_mvp1/robot_reports/pre_check/
│
├── 📄 report.html                    ← Current run
├── 📄 log.html                       ← Current run detailed log
├── 📄 output.xml                     ← Current run XML
│
├── 📈 combined_report.html           ← ⭐ HISTORY (last 20 runs)
├── 📈 combined_log.html              ← History detailed log
├── 📈 combined_output.xml            ← History XML
│
└── 📂 history/
    ├── output_20251001_100000.xml    ← Run #1
    ├── output_20251002_140000.xml    ← Run #2
    ├── output_20251003_110000.xml    ← Run #3
    ├── output_20251004_113000.xml    ← Run #4
    ├── output_20251005_160000.xml    ← Run #5
    ├── output_20251006_091500.xml    ← Run #6
    ├── output_20251007_143000.xml    ← Run #7
    └── output_20251008_100000.xml    ← Run #8 (most recent)
```

## When to Use Each Report

### Use report.html when:
- ✅ You want to see ONLY the latest test results
- ✅ You're debugging a specific failure in the current run
- ✅ You need detailed logs for the current execution
- ✅ You want to verify the current pipeline passed/failed

### Use combined_report.html when:
- ✅ You want to see test history and trends
- ✅ You're investigating if a test is flaky
- ✅ You need to show test stability over time
- ✅ You want to know when a test started failing
- ✅ You're doing compliance or audit reporting
- ✅ You want to identify problem tests
- ✅ You need historical context for a failure

## Quick Decision Tree

```
                    ┌─────────────────────┐
                    │  Need test results? │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
         ┌──────▼───────┐            ┌───────▼──────┐
         │ Latest run   │            │  Historical  │
         │    only?     │            │   context?   │
         └──────┬───────┘            └───────┬──────┘
                │                            │
                ▼                            ▼
        ┌──────────────┐          ┌────────────────┐
        │ report.html  │          │ combined_      │
        │              │          │ report.html ⭐ │
        └──────────────┘          └────────────────┘
```

## Summary Table

| Feature | report.html | combined_report.html |
|---------|-------------|----------------------|
| **Scope** | Single run | Last 20 runs |
| **Created by** | Robot Framework | merge_reports.py |
| **Updated** | Each run (new file) | Each run (merged) |
| **Shows trends** | ❌ No | ✅ Yes |
| **Identifies flaky tests** | ❌ No | ✅ Yes |
| **Historical context** | ❌ No | ✅ Yes |
| **Detailed current logs** | ✅ Yes | ⚠️ Limited |
| **Quick pass/fail** | ✅ Yes | ✅ Yes |
| **Time span** | 1 execution | Up to 20 executions |
| **Best for** | Current troubleshooting | Historical analysis |

## Key Takeaway

📊 **ALWAYS CHECK combined_report.html FOR HISTORICAL CONTEXT!**

When a test fails, looking at combined_report.html will tell you:
- Is this a new failure or recurring issue?
- Is the test flaky?
- When did it start failing?
- What's the overall pass rate?

This information is **invaluable** for debugging and test maintenance!

---

**Bottom line**:
- `report.html` = What happened **NOW**
- `combined_report.html` = What happened **OVER TIME** ⭐
