# Execution Tracking Quick Reference

## 📊 Quick Start

### Using the Enhanced Pipeline

1. **Activate Enhanced Pipeline**
   ```bash
   cp .gitlab-ci-enhanced.yml .gitlab-ci.yml
   git add .gitlab-ci.yml
   git commit -m "Enable execution tracking"
   git push
   ```

2. **Run Pipeline in GitLab UI**
   - Go to: `CI/CD → Pipelines → Run Pipeline`
   - Select: Environment, Record Type, Operation
   - Paste: CSV data
   - Click: `Run Pipeline`

3. **View Reports**
   - Current run: `robot_reports/{pre_check|post_check}/report.html`
   - History: `robot_reports/{pre_check|post_check}/combined_report.html`
   - Statistics: `robot_reports/execution_summary.html`

## 📁 File Locations

| File | Purpose | Location |
|------|---------|----------|
| Enhanced Pipeline | Main CI/CD config | `.gitlab-ci-enhanced.yml` |
| Execution Counters | Track test counts | `robot_reports/execution_counters/*.json` |
| Test History | Historical XML data | `robot_reports/{type}/history/output_*.xml` |
| Combined Reports | Merged test runs | `robot_reports/{type}/combined_report.html` |
| Statistics Dashboard | Overall summary | `robot_reports/execution_summary.html` |

## 🤖 Robot Framework Integration

### Basic Template

```robot
*** Settings ***
Library    ExecutionCounter

*** Variables ***
${COUNTER_FILE}    %{COUNTER_FILE}

*** Test Cases ***
My Test
    Initialize Execution Counter    ${COUNTER_FILE}
    ${count}=    Record Test Execution    My Test
    Log    Execution #${count}
    # ... test logic ...
    Save Execution Counter
```

### ExecutionCounter Keywords

| Keyword | Purpose | Returns |
|---------|---------|---------|
| `Initialize Execution Counter` | Load counter from file | - |
| `Record Test Execution` | Increment and save | Count |
| `Increment Test Execution Count` | Increment only (no save) | Count |
| `Get Test Execution Count` | Get count for test | Count |
| `Get Total Test Executions` | Get total across all tests | Count |
| `Save Execution Counter` | Write to file | Boolean |
| `Log Execution Statistics` | Print all stats to log | - |

## 📈 Execution Counter Data

### JSON Format

```json
{
  "Test Name": {
    "count": 25,
    "first_run": "2025-10-01T10:00:00",
    "last_run": "2025-10-08T15:30:00",
    "history": [
      {"timestamp": "2025-10-08T15:30:00", "run_number": 25}
    ]
  }
}
```

### Reading Counter Data

```python
import json

with open('robot_reports/execution_counters/pre_check_counter.json') as f:
    data = json.load(f)

for test, info in data.items():
    print(f"{test}: {info['count']} executions")
```

## 🔧 Merge Reports Script

### Command Line

```bash
# Merge last 20 runs (default)
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 20

# Merge last 50 runs
python3 infoblox_mvp1/utils/robot/merge_reports.py post_check 50

# Merge all available runs
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 999
```

### Output Files

```
robot_reports/pre_check/
├── history/
│   ├── output_20251001_100000.xml
│   ├── output_20251002_140000.xml
│   └── output_20251008_153000.xml
├── combined_output.xml      # Merged XML
├── combined_log.html         # Merged log
└── combined_report.html      # Merged report
```

## 📊 Pipeline Stages

```
┌─────────────────┐
│ file-processing │
└────────┬────────┘
         ├───────────────────────┐
         │                       │
┌────────▼────────┐    ┌────────▼────────┐
│  pre_check      │    │ json_validation │
│  (with counter) │    └─────────────────┘
└────────┬────────┘
         │
┌────────▼────────┐
│  run_ansible    │
└────────┬────────┘
         │
┌────────▼────────┐
│ post_impl       │
│ (with counter)  │
└────────┬────────┘
         │
┌────────▼────────┐
│ generate_report │  ⭐ NEW STAGE
└─────────────────┘
```

## 🎯 Key Features

### ✅ What's Tracked

- Total test executions per test
- First execution timestamp
- Last execution timestamp
- Execution history (last 50 runs)
- Pipeline ID for each run
- Grid host and record type

### ✅ What's Generated

- Per-run HTML reports
- Combined historical reports
- Execution statistics dashboard
- Detailed commit messages
- JSON execution counters

### ✅ What's Committed

- Current test reports
- Execution counter files
- Historical test data
- Statistics dashboard
- All automatically pushed to `main`

## 💡 Common Tasks

### View Total Executions

```bash
# Pre-check
python3 -c "import json; data=json.load(open('robot_reports/execution_counters/pre_check_counter.json')); print(f'Total: {sum(t[\"count\"] for t in data.values())}')"

# Post-check
python3 -c "import json; data=json.load(open('robot_reports/execution_counters/post_check_counter.json')); print(f'Total: {sum(t[\"count\"] for t in data.values())}')"
```

### Find Most Executed Test

```python
import json

with open('robot_reports/execution_counters/pre_check_counter.json') as f:
    data = json.load(f)

most_run = max(data.items(), key=lambda x: x[1]['count'])
print(f"Most executed: {most_run[0]} - {most_run[1]['count']} times")
```

### Export to CSV

```python
import json
import csv

with open('robot_reports/execution_counters/pre_check_counter.json') as f:
    data = json.load(f)

with open('executions.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Test', 'Count', 'First Run', 'Last Run'])
    for test, info in data.items():
        writer.writerow([test, info['count'], info['first_run'], info['last_run']])

print("Exported to executions.csv")
```

### Reset Counters

```bash
# Backup first
cp robot_reports/execution_counters/pre_check_counter.json pre_check_counter.backup

# Reset
echo '{}' > robot_reports/execution_counters/pre_check_counter.json

# Commit
git add robot_reports/execution_counters/pre_check_counter.json
git commit -m "Reset execution counter"
git push
```

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Counter not updating | Check `Save Execution Counter` is called |
| Reports not merging | Verify `output.xml` exists in history directory |
| Git push fails | Check `GITLAB_CI_TOKEN` permissions |
| Missing statistics | Ensure `generate_execution_report` stage ran |
| Old data showing | Clear browser cache or use incognito |

## 📝 Git Commit Message Format

```
Pre-check PASSED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]
                  └─ Grid Host ─┘        └─Type─┘  └─ Pipeline ─┘  └─ Total Count ─┘

Post-implementation PASSED: gridmgr.amfam.com - network - add [Pipeline: 67890] [Total Executions: 52]
                            └─ Grid ─┘          └─Type┘  └Op┘  └─ Pipeline ─┘  └─ Total ─┘
```

## 🔍 Viewing Reports in GitLab

### Artifacts Browser

1. `CI/CD → Pipelines`
2. Click pipeline number
3. Click job (e.g., `pre_check`)
4. Click `Browse` on right sidebar
5. Navigate to `robot_reports/`

### Repository Browser

1. `Repository → Files`
2. Navigate to `infoblox_mvp1/robot_reports/`
3. Click on HTML files to download/view

### Direct Links

```
# Current run
${CI_PROJECT_URL}/-/jobs/${CI_JOB_ID}/artifacts/browse/infoblox_mvp1/robot_reports/pre_check/

# Repository
${CI_PROJECT_URL}/-/tree/main/infoblox_mvp1/robot_reports
```

## ⚙️ Configuration

### Adjust History Retention

Edit `.gitlab-ci-enhanced.yml`:

```yaml
# Line ~380 (pre_check stage)
python3 infoblox_mvp1/utils/robot/merge_reports.py pre_check 50  # Keep 50 runs

# Line ~720 (post_implementation stage)
python3 infoblox_mvp1/utils/robot/merge_reports.py post_check 100  # Keep 100 runs
```

### Adjust Artifact Expiration

```yaml
artifacts:
  when: always
  paths:
    - infoblox_mvp1/robot_reports/pre_check/
  expire_in: 2 weeks  # Change from 1 week to 2 weeks
```

## 📚 Additional Resources

- **Full Guide**: `ENHANCED_PIPELINE_GUIDE.md`
- **Original Pipeline**: `.gitlab-ci.yml`
- **Enhanced Pipeline**: `.gitlab-ci-enhanced.yml`
- **Example Test**: `tests/example_with_counter.robot`
- **ExecutionCounter**: `utils/robot/ExecutionCounter.py`
- **Merge Reports**: `utils/robot/merge_reports.py`

## 🎓 Best Practices

1. ✅ **Always call** `Initialize Execution Counter` first
2. ✅ **Use** `Record Test Execution` for simple tracking
3. ✅ **Save counters** before test suite ends
4. ✅ **Review** execution summary weekly
5. ✅ **Monitor** combined reports for trends
6. ✅ **Commit** counter files to repository
7. ✅ **Don't** manually edit counter JSON files
8. ✅ **Do** backup counters before major changes

---

**Quick Help**: For questions, check `ENHANCED_PIPELINE_GUIDE.md` or contact the automation team.
