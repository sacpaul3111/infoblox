# Report Files Quick Reference Card

## 📁 All Files Generated (Per Stage)

### Pre-Check Stage Files (9 files total)

```
infoblox_mvp1/robot_reports/pre_check/
├── output.xml                    📄 Robot Framework XML output
├── log.html                      📋 Detailed step-by-step log
├── report.html                   📊 Current run summary
├── combined_output.xml           📦 Last 20 runs XML merged
├── combined_log.html             📚 Last 20 runs log merged
├── combined_report.html          ⭐ Last 20 runs summary (HISTORY!)
└── history/                      📂 Individual run archives
    ├── output_20251001_100000.xml
    ├── output_20251002_140000.xml
    └── ... (up to 20 files)
```

### Post-Check Stage Files (9 files total)

```
infoblox_mvp1/robot_reports/post_check/
├── output.xml                    📄 Robot Framework XML output
├── log.html                      📋 Detailed step-by-step log
├── report.html                   📊 Current run summary
├── combined_output.xml           📦 Last 20 runs XML merged
├── combined_log.html             📚 Last 20 runs log merged
├── combined_report.html          ⭐ Last 20 runs summary (HISTORY!)
└── history/                      📂 Individual run archives
    ├── output_20251001_110000.xml
    ├── output_20251002_150000.xml
    └── ... (up to 20 files)
```

### Execution Tracking Files (2 files)

```
infoblox_mvp1/robot_reports/execution_counters/
├── pre_check_counter.json        🔢 Pre-check execution counts
└── post_check_counter.json       🔢 Post-check execution counts
```

### Overall Statistics File (1 file)

```
infoblox_mvp1/robot_reports/
└── execution_summary.html        📈 Dashboard of all test activity
```

---

## 🎯 Quick Decision Tree

```
What do you need?
│
├─ Latest test results?
│  └─ Use: report.html (current run only)
│
├─ Test history/trends? ⭐
│  └─ Use: combined_report.html (last 20 runs)
│
├─ Debug current failure?
│  └─ Use: log.html (step-by-step details)
│
├─ Debug historical issue?
│  └─ Use: combined_log.html (all runs)
│
├─ Identify flaky tests?
│  └─ Use: combined_report.html (shows patterns)
│
├─ Overall statistics?
│  └─ Use: execution_summary.html (all tests)
│
└─ How many times test ran?
   └─ Use: *_counter.json (execution counts)
```

---

## 📊 File Comparison Table

| File | Scope | Size | Use For |
|------|-------|------|---------|
| **report.html** | Current run | Small | ✅ Latest results |
| **combined_report.html** ⭐ | Last 20 runs | Medium | ✅ Test history & trends |
| **log.html** | Current run | Medium | 🔍 Debug current failure |
| **combined_log.html** | Last 20 runs | Large | 🔍 Debug historical issues |
| **output.xml** | Current run | Small | 🤖 Automation/scripting |
| **combined_output.xml** | Last 20 runs | Medium | 🤖 Historical data access |
| **execution_summary.html** | All time | Small | 📈 Big picture stats |
| ***_counter.json** | All time | Tiny | 🔢 Execution counts |

---

## ⭐ The 3 Most Important Files

### 1. **combined_report.html** (Pre-Check & Post-Check)
**What**: Last 20 test runs merged together
**Why**: Shows if tests are stable or flaky
**When**: ALWAYS check this for historical context!

### 2. **report.html** (Pre-Check & Post-Check)
**What**: Current pipeline run results only
**Why**: Quick pass/fail check for latest run
**When**: Just need to see if current run passed

### 3. **execution_summary.html**
**What**: Overall dashboard of ALL test activity
**Why**: See total execution counts across all tests
**When**: Want big picture view of testing

---

## 🔢 Total File Count

**Per Pipeline Run**:
- Pre-check: 9 files (3 current + 3 combined + 1 history + counters)
- Post-check: 9 files (3 current + 3 combined + 1 history + counters)
- Overall: 1 file (execution_summary.html)

**Total: ~19 files generated per pipeline run**

---

## 📂 File Locations

### GitLab Artifacts (Temporary)
```
Pipeline → Job → Browse Artifacts
└─ infoblox_mvp1/robot_reports/
   ├─ pre_check/
   ├─ post_check/
   ├─ execution_counters/
   └─ execution_summary.html
```

### Git Repository (Permanent)
```
Repository → infoblox_mvp1/robot_reports/
└─ (same structure, committed after each run)
```

---

## 📋 File Generation Order

```
1. Robot Framework runs
   → Creates: output.xml, log.html, report.html

2. ExecutionCounter updates
   → Updates: *_counter.json

3. merge_reports.py runs
   → Copies: output.xml to history/
   → Creates: combined_output.xml
   → Creates: combined_log.html
   → Creates: combined_report.html ⭐

4. Git commit
   → Commits all files to repository

5. Reporting stage runs (after both pre & post)
   → Creates: execution_summary.html
```

---

## 💡 Pro Tips

### Tip 1: Always Check History
❌ Don't just look at `report.html`
✅ Also check `combined_report.html` for context!

### Tip 2: Identify Flaky Tests
Open `combined_report.html` and look for:
- Tests with < 100% pass rate
- Intermittent failures
- Recent failure patterns

### Tip 3: Debug Effectively
**Current failure?** → `log.html`
**Historical/intermittent?** → `combined_log.html`

### Tip 4: Share Reports
**For management:** `execution_summary.html`
**For developers:** `combined_report.html`
**For debugging:** `log.html`

---

## 🎯 Common Scenarios

### Scenario 1: Test Just Failed
```
1. Open: report.html (see which test failed)
2. Open: log.html (see why it failed)
3. Open: combined_report.html (is this new or recurring?)
```

### Scenario 2: Test Sometimes Fails
```
1. Open: combined_report.html
2. Look for test with < 100% pass rate
3. Review failure pattern (every 3rd run? specific times?)
4. Open: combined_log.html for detailed history
```

### Scenario 3: Generate Report for Management
```
1. Open: execution_summary.html
2. Shows total tests, execution counts, trends
3. Professional dashboard view
```

### Scenario 4: Audit/Compliance
```
1. Use: combined_report.html (shows test frequency)
2. Use: execution_summary.html (shows coverage)
3. Use: *_counter.json (exact execution counts)
```

---

## 📖 Full Documentation

For complete details, see:
- **REPORT_FILES_GUIDE.md** - Comprehensive file documentation
- **UNDERSTANDING_REPORTS.md** - Report.html vs combined_report.html
- **REPORT_COMPARISON.md** - Visual side-by-side comparison

---

## ✅ Summary

**Total Files**: ~19 per pipeline run
**Most Important**: combined_report.html ⭐
**For Current Results**: report.html
**For Statistics**: execution_summary.html
**All Generated**: Automatically by the pipeline

**No manual work needed - just view the reports!** 🎉
