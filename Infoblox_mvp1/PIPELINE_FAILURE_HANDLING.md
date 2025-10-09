# Pipeline Failure Handling - How Reports Are Generated

## Quick Answer: YES! ✅

**Reports are ALWAYS generated and committed to Git, even when tests fail.**

The pipeline is designed to capture failure reports so you can see what went wrong.

---

## How It Works

### 1️⃣ Pre-Check Stage

**What happens when pre-check FAILS:**

```
1. Robot tests run → Some tests FAIL ❌
2. ExecutionCounter tracks the failures ✅
3. merge_reports.py creates combined history ✅
4. Git commit happens with message:
   "Pre-check FAILED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]" ✅
5. Reports pushed to Git repository ✅
6. Stage exits with code 1 (failure) ❌
7. Pipeline STOPS - does NOT proceed to deploy ⛔
8. Reporting stage STILL RUNS (see below) ✅
```

**Files committed to Git (even on failure):**
```
✅ infoblox_mvp1/robot_reports/pre_check/output.xml
✅ infoblox_mvp1/robot_reports/pre_check/log.html
✅ infoblox_mvp1/robot_reports/pre_check/report.html
✅ infoblox_mvp1/robot_reports/pre_check/combined_report.html ⭐
✅ infoblox_mvp1/robot_reports/pre_check/history/output_*.xml
✅ infoblox_mvp1/robot_reports/execution_counters/pre_check_counter.json
```

**Configuration that makes this work:**
```yaml
artifacts:
  when: always  # ← Artifacts saved even on failure
```

---

### 2️⃣ Post-Implementation Stage

**What happens when post-check FAILS:**

```
1. Robot tests run → Some tests FAIL ❌
2. ExecutionCounter tracks the failures ✅
3. merge_reports.py creates combined history ✅
4. Git commit happens with message:
   "Post-implementation FAILED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 52]" ✅
5. Reports pushed to Git repository ✅
6. Stage exits with code 1 (failure) ❌
7. Reporting stage STILL RUNS (see below) ✅
```

**Files committed to Git (even on failure):**
```
✅ infoblox_mvp1/robot_reports/post_check/output.xml
✅ infoblox_mvp1/robot_reports/post_check/log.html
✅ infoblox_mvp1/robot_reports/post_check/report.html
✅ infoblox_mvp1/robot_reports/post_check/combined_report.html ⭐
✅ infoblox_mvp1/robot_reports/post_check/history/output_*.xml
✅ infoblox_mvp1/robot_reports/execution_counters/post_check_counter.json
```

---

### 3️⃣ Reporting Stage (ALWAYS RUNS!)

**Configuration:**
```yaml
generate_execution_report:
  stage: reporting
  when: always  # ← Runs even if previous stages failed!
```

**What happens:**

| Scenario | Reporting Stage Behavior |
|----------|------------------------|
| **Pre-check fails** | ✅ RUNS (generates summary with pre-check failure data) |
| **Post-check fails** | ✅ RUNS (generates summary with post-check failure data) |
| **Both fail** | ✅ RUNS (generates summary showing both failures) |
| **Both succeed** | ✅ RUNS (generates summary showing all passes) |

**Files committed to Git (always):**
```
✅ infoblox_mvp1/robot_reports/execution_summary.html
```

---

## Complete Failure Scenarios

### Scenario A: Pre-Check Fails

```
Pipeline Flow:
├─ build-container ✅
├─ file-processing ✅
├─ pre-implementation
│  ├─ pre_check ❌ FAILS
│  │  ├─ Tests run (some fail)
│  │  ├─ Reports generated
│  │  ├─ Git commit: "Pre-check FAILED: ..." ✅
│  │  └─ Exit code 1
│  │
│  ├─ json_validation ⛔ SKIPPED (pre_check failed)
│  └─ server_connection_test ⛔ SKIPPED
│
├─ deploy ⛔ SKIPPED (validation failed - SAFE!)
├─ post-implementation ⛔ SKIPPED
│
└─ reporting
   └─ generate_execution_report ✅ RUNS!
      ├─ Reads pre_check_counter.json (shows failure)
      ├─ Generates execution_summary.html
      └─ Git commit: "Update execution statistics report" ✅

Pipeline Status: ❌ FAILED (but reports committed!)
```

---

### Scenario B: Pre-Check Passes, Post-Check Fails

```
Pipeline Flow:
├─ build-container ✅
├─ file-processing ✅
├─ pre-implementation
│  ├─ pre_check ✅ PASSES
│  │  └─ Git commit: "Pre-check PASSED: ..." ✅
│  ├─ json_validation ✅
│  └─ server_connection_test ✅
│
├─ deploy ✅ (validation passed, safe to deploy)
│
├─ post-implementation
│  └─ post_implementation ❌ FAILS
│     ├─ Tests run (some fail)
│     ├─ Reports generated
│     ├─ Git commit: "Post-implementation FAILED: ..." ✅
│     └─ Exit code 1
│
└─ reporting
   └─ generate_execution_report ✅ RUNS!
      ├─ Reads both counters (pre: pass, post: fail)
      ├─ Generates execution_summary.html
      └─ Git commit: "Update execution statistics report" ✅

Pipeline Status: ❌ FAILED (but all reports committed!)
```

---

### Scenario C: Both Pass

```
Pipeline Flow:
├─ build-container ✅
├─ file-processing ✅
├─ pre-implementation
│  ├─ pre_check ✅ PASSES
│  │  └─ Git commit: "Pre-check PASSED: ..." ✅
│  ├─ json_validation ✅
│  └─ server_connection_test ✅
│
├─ deploy ✅
│
├─ post-implementation
│  └─ post_implementation ✅ PASSES
│     ├─ Tests pass
│     ├─ Reports generated
│     └─ Git commit: "Post-implementation PASSED: ..." ✅
│
└─ reporting
   └─ generate_execution_report ✅ RUNS!
      ├─ Reads both counters (both passed)
      ├─ Generates execution_summary.html
      └─ Git commit: "Update execution statistics report" ✅

Pipeline Status: ✅ SUCCESS (all reports committed!)
```

---

## Key Configuration Settings

### Pre-Check Stage
```yaml
pre_check:
  stage: pre-implementation
  artifacts:
    when: always        # ← Save artifacts even on failure
  # No allow_failure    # ← Pipeline stops if this fails (SAFE!)
```

**Why no `allow_failure`?**
- We DON'T want to deploy if pre-check fails
- Pipeline MUST stop to prevent bad changes
- But reports are still saved and committed

---

### Post-Implementation Stage
```yaml
post_implementation:
  stage: post-implementation
  artifacts:
    when: always        # ← Save artifacts even on failure
  # No allow_failure    # ← Mark pipeline as failed if tests fail
```

**Why no `allow_failure`?**
- We need to know if post-check failed
- Pipeline status shows failure (alerts team)
- But reports are still saved and committed

---

### Reporting Stage
```yaml
generate_execution_report:
  stage: reporting
  when: always          # ← ALWAYS run, even if previous stages failed!
  artifacts:
    when: always        # ← Save artifacts even on failure
```

**Why `when: always`?**
- We ALWAYS want execution statistics
- Even failures need to be tracked
- Historical data must be complete

---

## Git Commits on Failure

### Commit Message Examples

**Pre-check failure:**
```
Pre-check FAILED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]
```

**Post-check failure:**
```
Post-implementation FAILED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 52]
```

**Reporting (always):**
```
Update execution statistics report [Pipeline: 12345]
```

---

## Where to Find Failure Reports

### In Git Repository (Permanent)

**After pre-check failure:**
```
Repository → infoblox_mvp1/robot_reports/pre_check/
├── combined_report.html ⭐ (shows failure in history)
├── log.html (detailed failure logs)
└── report.html (current run failure)
```

**After post-check failure:**
```
Repository → infoblox_mvp1/robot_reports/post_check/
├── combined_report.html ⭐ (shows failure in history)
├── log.html (detailed failure logs)
└── report.html (current run failure)
```

**Execution summary (always):**
```
Repository → infoblox_mvp1/robot_reports/execution_summary.html
(Shows all executions, including failures)
```

---

### In GitLab Artifacts (Temporary - 1 week)

```
Pipeline → Job → Browse Artifacts
└─ Same files as in Git repository
```

---

## Code Implementation

### How Reports Are Committed Even on Failure

```bash
# In pre_check stage (lines 340-462)

# Run Robot tests and capture exit code
robot ... || robot_exit_code=$?

# Generate reports (happens BEFORE exit)
python3 -c "from ExecutionCounter import update_counter; ..."
python3 -c "from merge_reports import merge_robot_reports; ..."

# Commit to Git (happens BEFORE exit)
git add -f infoblox_mvp1/robot_reports/pre_check/* || true
git add -f infoblox_mvp1/robot_reports/execution_counters/* || true

if ! git diff --cached --quiet; then
  if [ $robot_exit_code -ne 0 ]; then
    commit_msg="Pre-check FAILED: ..."
  else
    commit_msg="Pre-check PASSED: ..."
  fi

  git commit -m "$commit_msg"
  git push origin HEAD:main
fi

# NOW exit with failure (if tests failed)
if [ $robot_exit_code -ne 0 ]; then
  exit 1  # ← Pipeline stops, but reports already committed!
fi
```

**Key insight:** Reports are generated and committed **BEFORE** the `exit 1` command.

---

## Benefits of This Approach

### ✅ 1. Failure Visibility
- Every test failure is tracked
- Historical failure patterns visible
- Can identify flaky tests

### ✅ 2. Audit Trail
- Complete record of all test runs
- Pass/fail history preserved
- Compliance requirements met

### ✅ 3. Debugging Support
- Detailed logs available even for failed runs
- Can investigate failures weeks later
- No data loss

### ✅ 4. Safety First
- Pipeline stops on pre-check failure (won't deploy bad changes)
- But reports are preserved for analysis
- Best of both worlds

### ✅ 5. Complete Statistics
- execution_summary.html shows ALL runs
- Includes both passes and failures
- Accurate execution counts

---

## Testing the Behavior

### How to Verify Failure Handling

1. **Manually fail a test:**
   ```robot
   *** Test Cases ***
   Test That Will Fail
       Should Be Equal    1    2    # Will fail!
   ```

2. **Run pipeline**

3. **Check Git commits:**
   ```bash
   git log --oneline | head -5
   ```

   Should see:
   ```
   abc123 Update execution statistics report [Pipeline: 12345]
   def456 Pre-check FAILED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 48]
   ```

4. **Check repository files:**
   ```
   Repository → infoblox_mvp1/robot_reports/
   ├── pre_check/combined_report.html (shows failure)
   └── execution_summary.html (includes failure in stats)
   ```

---

## Summary Table

| Stage | On Failure | Reports Generated? | Reports Committed? | Pipeline Continues? |
|-------|-----------|-------------------|-------------------|-------------------|
| **pre_check** | Exit 1 | ✅ Yes | ✅ Yes | ❌ No (SAFE!) |
| **post_implementation** | Exit 1 | ✅ Yes | ✅ Yes | ❌ No (marks failed) |
| **generate_execution_report** | Never fails | ✅ Yes | ✅ Yes | ✅ Always runs |

---

## Common Questions

### Q: Will I see failure reports in Git?
**A:** ✅ YES! Reports are committed before the stage exits with failure.

### Q: Will the pipeline deploy if pre-check fails?
**A:** ❌ NO! Pipeline stops at pre-check failure (safe behavior).

### Q: Will execution_summary.html be generated if tests fail?
**A:** ✅ YES! The reporting stage has `when: always`, so it runs regardless.

### Q: Will failure statistics be tracked?
**A:** ✅ YES! ExecutionCounter tracks both passes and failures.

### Q: Can I see historical failures in combined_report.html?
**A:** ✅ YES! Failed runs are included in the merged history.

---

## Final Answer

### ✅ YES - Reports Generated Even on Failure!

**Every scenario covered:**
- ✅ Pre-check fails → Reports committed to Git
- ✅ Post-check fails → Reports committed to Git
- ✅ Both fail → Both sets of reports committed
- ✅ Execution summary → Always generated and committed

**Safety maintained:**
- ⛔ Pipeline stops on pre-check failure (won't deploy)
- ⛔ Pipeline marked as failed on post-check failure
- ✅ But all reports are preserved for analysis

**You will ALWAYS have failure reports in Git!** 📦✅
