# Understanding Robot Framework Reports

## Quick Answer

**YES!** `merge_reports.py` creates a **combined history HTML report** showing ALL test runs merged together.

## Two Reports Generated

### 1. 📄 **report.html** - Current Run Only

**File**: `infoblox_mvp1/robot_reports/{pre_check|post_check}/report.html`

**What it shows**: Results from ONLY the current pipeline run

**Use this when**: You want to see what happened in the latest test execution

**Example**:
```
Pipeline #12345 (2025-10-08 10:00)
├─ Test 1: PASS
├─ Test 2: PASS
└─ Test 3: FAIL
```

### 2. 📈 **combined_report.html** - Historical Report ⭐

**File**: `infoblox_mvp1/robot_reports/{pre_check|post_check}/combined_report.html`

**What it shows**: Results from the LAST 20 pipeline runs merged together

**Use this when**: You want to see trends, history, and overall test stability

**Example**:
```
Combined History (Last 20 Runs)
├─ Test 1: 20 executions (20 PASS, 0 FAIL)
├─ Test 2: 20 executions (19 PASS, 1 FAIL)
└─ Test 3: 20 executions (15 PASS, 5 FAIL) ⚠️ Flaky test!
```

## Where to Find Them

### In GitLab UI - Artifacts Browser

1. Navigate to `CI/CD → Pipelines`
2. Click on your pipeline number
3. Click on `pre_check` or `post_implementation` job
4. Click `Browse` button (right sidebar)
5. Navigate to `infoblox_mvp1/robot_reports/pre_check/` or `post_check/`

**You'll see:**
```
infoblox_mvp1/robot_reports/pre_check/
├── report.html              ← Current run
├── log.html                 ← Current run log
├── output.xml               ← Current run XML
├── combined_report.html     ← ⭐ HISTORY (last 20 runs)
├── combined_log.html        ← History log
├── combined_output.xml      ← History XML
└── history/
    ├── output_20251001_100000.xml
    ├── output_20251002_140000.xml
    ├── output_20251003_110000.xml
    └── ... (up to 20 files)
```

### In Repository (After Pipeline Commits)

1. Navigate to `Repository → Files`
2. Browse to `infoblox_mvp1/robot_reports/pre_check/` or `post_check/`
3. Click on the HTML file to download

### Locally (After Git Pull)

```bash
git pull origin main

# Open current run
open infoblox_mvp1/robot_reports/pre_check/report.html

# Open HISTORY (last 20 runs) ⭐
open infoblox_mvp1/robot_reports/pre_check/combined_report.html
```

## What Each Report Shows

### Current Run Report (report.html)

**Header:**
```
Pre-Check Validation - a_record - Pipeline 12345
```

**Test Results:**
```
All Tests
└─ Pre Check
   ├─ Validate A Record              ✅ PASS (2.5s)
   ├─ Check Duplicate Records        ✅ PASS (1.8s)
   └─ Verify Required Fields         ❌ FAIL (0.5s)

Statistics:
- Total: 3 tests
- Passed: 2 (66.67%)
- Failed: 1 (33.33%)
- Elapsed: 4.8s
```

### Combined History Report (combined_report.html)

**Header:**
```
Pre Check - Combined History
Merged from 20 test runs
```

**Test Results with History:**
```
All Tests (Showing results from 20 executions)
└─ Pre Check
   ├─ Validate A Record              ✅ 20/20 PASS (100%)
   │  Last executed: 2025-10-08 10:00
   │  First executed: 2025-10-01 09:00
   │
   ├─ Check Duplicate Records        ✅ 19/20 PASS (95%)
   │  Last executed: 2025-10-08 10:00
   │  Failed: 1 time (2025-10-03 14:30)
   │
   └─ Verify Required Fields         ⚠️ 15/20 PASS (75%)
      Last executed: 2025-10-08 10:00
      Failed: 5 times (flaky test)

Statistics (Combined):
- Total executions: 60 (3 tests × 20 runs)
- Passed: 54 (90%)
- Failed: 6 (10%)
- Total elapsed: 96.5s
```

## Why Two Reports?

| Purpose | Current Run | Combined History |
|---------|-------------|------------------|
| See latest results | ✅ | ❌ |
| Troubleshoot specific failure | ✅ | ❌ |
| Identify flaky tests | ❌ | ✅ |
| See trends over time | ❌ | ✅ |
| Measure test stability | ❌ | ✅ |
| View all historical data | ❌ | ✅ |
| Quick pass/fail check | ✅ | ✅ |

## How History Merging Works

```
Pipeline Run #1
─────────────────
Robot test runs → output.xml → Saved to history/output_20251001_100000.xml
                             └─ Creates combined_report.html (1 run)

Pipeline Run #2
─────────────────
Robot test runs → output.xml → Saved to history/output_20251002_140000.xml
                             └─ Updates combined_report.html (2 runs merged)

Pipeline Run #3
─────────────────
Robot test runs → output.xml → Saved to history/output_20251003_110000.xml
                             └─ Updates combined_report.html (3 runs merged)

...

Pipeline Run #20
─────────────────
Robot test runs → output.xml → Saved to history/output_20251020_150000.xml
                             └─ Updates combined_report.html (20 runs merged)

Pipeline Run #21
─────────────────
Robot test runs → output.xml → Saved to history/output_20251021_160000.xml
                             ├─ DELETES oldest (output_20251001_100000.xml)
                             └─ Updates combined_report.html (last 20 runs)
```

## What You'll See in the Pipeline Logs

When merge_reports.py runs, you'll see this output:

```
==========================================
  MERGING HISTORICAL TEST REPORTS
==========================================
Robot Framework Report Merger
Report Type: pre_check
Max History: 20
Base Path: infoblox_mvp1
--------------------------------------------------------------------------------

================================================================================
Test Execution Statistics - Pre Check
================================================================================
Total test runs: 20
History location: infoblox_mvp1/robot_reports/pre_check/history

Historical runs:
   1. 2025-10-01 10:00:00
   2. 2025-10-02 14:00:00
   3. 2025-10-03 11:00:00
   ...
  20. 2025-10-08 10:00:00
================================================================================

Merging 20 test runs...

✓ Successfully merged reports!
  Combined report: infoblox_mvp1/robot_reports/pre_check/combined_report.html
  Combined log: infoblox_mvp1/robot_reports/pre_check/combined_log.html
  Total runs merged: 20

✓ Report merging completed successfully!

📊 VIEW REPORTS:
   Current Run:  infoblox_mvp1/robot_reports/pre_check/report.html
   📈 HISTORY:   infoblox_mvp1/robot_reports/pre_check/combined_report.html ⭐
   History Dir:  infoblox_mvp1/robot_reports/pre_check/history/

✅ Test history merged successfully!

📊 AVAILABLE REPORTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📄 Current Run:     infoblox_mvp1/robot_reports/pre_check/report.html
  📈 HISTORY REPORT:  infoblox_mvp1/robot_reports/pre_check/combined_report.html ⭐
  📂 History Data:    infoblox_mvp1/robot_reports/pre_check/history/
  📊 Total Runs:      20
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Benefits of Combined History Report

### 1. **Identify Flaky Tests**

```
Test A: 20/20 PASS (100%) → Stable ✅
Test B: 19/20 PASS (95%)  → Mostly stable ⚠️
Test C: 12/20 PASS (60%)  → Flaky! 🔴 Needs investigation
```

### 2. **See Trends**

The combined report shows if tests are:
- Consistently passing
- Recently started failing
- Intermittently failing (flaky)

### 3. **Historical Context**

When a test fails, check the combined report to see:
- Has this test failed before?
- Is this a new failure or recurring issue?
- When did it last pass?

### 4. **Compliance & Auditing**

- Prove test coverage over time
- Show testing frequency
- Demonstrate continuous validation

## Configuration

### Change Number of Historical Runs

Default: 20 runs

**Edit pipeline** (`.gitlab-ci-enhanced.yml` or `.gitlab-ci.yml`):

```yaml
# Keep last 50 runs instead of 20
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 50
python3 infoblox_mvp1/utils/robot/merge_reports.py post_check 50
```

### Manual Merge

You can manually run merge_reports.py:

```bash
cd infoblox_mvp1

# Merge pre-check reports
python3 utils/robot/merge_reports.py pre_check 20

# Merge post-check reports
python3 utils/robot/merge_reports.py post_check 20

# Merge with more history
python3 utils/robot/merge_reports.py pre_check 100
```

## Troubleshooting

### "No combined_report.html found"

**Possible causes:**
1. First pipeline run (no history yet)
2. merge_reports.py failed
3. Not enough runs to merge

**Solution:**
- Run pipeline at least 2 times to create history
- Check pipeline logs for merge_reports.py errors
- Verify output.xml exists in current run

### "Only 1 run in combined report"

**Cause**: Only one historical run available

**Solution**: Run pipeline more times to build history

### "Old combined_report.html showing"

**Cause**: Browser cache

**Solution**:
- Hard refresh (Ctrl+F5 or Cmd+Shift+R)
- Clear browser cache
- Download file again

## Summary

✅ **YES** - merge_reports.py creates `combined_report.html` showing ALL test history

🎯 **Two Reports**:
- `report.html` = Current run only
- `combined_report.html` = Last 20 runs merged ⭐ **USE THIS FOR HISTORY**

📂 **Location**: `infoblox_mvp1/robot_reports/{pre_check|post_check}/`

📈 **Benefits**: See trends, identify flaky tests, measure stability

🔄 **Updated**: Every pipeline run automatically merges and updates history

**Always look for `combined_report.html` to see test history!** 📊
