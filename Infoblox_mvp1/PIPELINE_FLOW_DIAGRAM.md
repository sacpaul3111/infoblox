# Pipeline Flow Diagram

## Enhanced Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GITLAB CI/CD PIPELINE                                │
│                     Enhanced with Execution Tracking                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: BUILD-CONTAINER (Manual/On Dockerfile Change)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐                                                     │
│  │ build_container    │  Build Docker image with Kaniko                     │
│  │                    │  → infoblox-runner:latest                           │
│  └────────────────────┘                                                     │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: FILE-PROCESSING                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐                                                     │
│  │ file_processing    │                                                     │
│  ├────────────────────┤                                                     │
│  │ 1. Validate CSV    │  CSV_DATA (from GitLab variable)                   │
│  │ 2. Process to JSON │      ↓                                              │
│  │ 3. Save to file    │  infoblox_record_processor.py                       │
│  └────────────────────┘      ↓                                              │
│                          prod_changes/{GRID_HOST}/{RECORD_TYPE}.json        │
│                                                                              │
│  Artifacts:                                                                  │
│  • prod_changes/                                                             │
│  • input/                                                                    │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: PRE-IMPLEMENTATION                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────┐   ┌──────────────────────────┐               │
│  │ server_connection_test   │   │ json_validation          │               │
│  ├──────────────────────────┤   ├──────────────────────────┤               │
│  │ Test connectivity to     │   │ Validate JSON structure  │               │
│  │ Infoblox Grid            │   │ Check required fields    │               │
│  └──────────────────────────┘   └──────────────────────────┘               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │ pre_check (WITH EXECUTION TRACKING) ⭐                          │        │
│  ├─────────────────────────────────────────────────────────────────┤        │
│  │ 1. Install Robot Framework + ExecutionCounter library          │        │
│  │ 2. Run validation tests (a_record/cname/network)               │        │
│  │ 3. Track execution counts → execution_counters/                │        │
│  │ 4. Merge historical reports (last 20 runs)                     │        │
│  │ 5. Generate combined_report.html                               │        │
│  │ 6. Commit reports + counters to repository                     │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│       │                                                                      │
│       ├→ ExecutionCounter.py                                                │
│       │   ├─ Load: execution_counters/pre_check_counter.json               │
│       │   ├─ Increment test counts                                         │
│       │   └─ Save: execution_counters/pre_check_counter.json               │
│       │                                                                      │
│       └→ merge_reports.py pre_check 20                                      │
│           ├─ Collect: robot_reports/pre_check/output.xml                   │
│           ├─ Archive: robot_reports/pre_check/history/output_*.xml         │
│           └─ Generate: robot_reports/pre_check/combined_report.html        │
│                                                                              │
│  Artifacts:                                                                  │
│  • robot_reports/pre_check/ (reports, logs, combined)                       │
│  • robot_reports/execution_counters/ (counter JSON files)                   │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: DEPLOY                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐                                                     │
│  │ run_ansible_playbook                                                     │
│  ├────────────────────┤                                                     │
│  │ 1. Load JSON file  │  prod_changes/{GRID_HOST}/{RECORD_TYPE}.json       │
│  │ 2. Configure vars  │      ↓                                              │
│  │ 3. Run playbook    │  ansible-playbook playbooks/{RECORD_TYPE}.yml      │
│  │ 4. Apply to Grid   │      ↓                                              │
│  └────────────────────┘  Infoblox NIOS Grid (via WAPI)                     │
│                                                                              │
│  Operation: add (present) or delete (absent)                                │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: POST-IMPLEMENTATION                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │ post_implementation (WITH EXECUTION TRACKING) ⭐                │        │
│  ├─────────────────────────────────────────────────────────────────┤        │
│  │ 1. Install Robot Framework + ExecutionCounter library          │        │
│  │ 2. Run verification tests (a_record/cname/network)             │        │
│  │ 3. Track execution counts → execution_counters/                │        │
│  │ 4. Merge historical reports (last 20 runs)                     │        │
│  │ 5. Generate combined_report.html                               │        │
│  │ 6. Commit reports + counters to repository                     │        │
│  │ 7. Run file cleanup (clearfilecontent.py)                      │        │
│  │ 8. Commit cleanup changes                                      │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│       │                                                                      │
│       ├→ ExecutionCounter.py                                                │
│       │   ├─ Load: execution_counters/post_check_counter.json              │
│       │   ├─ Increment test counts                                         │
│       │   └─ Save: execution_counters/post_check_counter.json              │
│       │                                                                      │
│       └→ merge_reports.py post_check 20                                     │
│           ├─ Collect: robot_reports/post_check/output.xml                  │
│           ├─ Archive: robot_reports/post_check/history/output_*.xml        │
│           └─ Generate: robot_reports/post_check/combined_report.html       │
│                                                                              │
│  Artifacts:                                                                  │
│  • robot_reports/post_check/ (reports, logs, combined)                      │
│  • robot_reports/execution_counters/ (counter JSON files)                   │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 6: REPORTING ⭐ NEW STAGE                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │ generate_execution_report                                       │        │
│  ├─────────────────────────────────────────────────────────────────┤        │
│  │ 1. Load execution counters (pre-check + post-check)            │        │
│  │ 2. Calculate statistics                                        │        │
│  │    • Total unique tests                                        │        │
│  │    • Total executions                                          │        │
│  │    • Per-test breakdown                                        │        │
│  │ 3. Generate HTML dashboard                                     │        │
│  │ 4. Display console summary                                     │        │
│  │ 5. Commit execution_summary.html to repository                │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│       │                                                                      │
│       ├─ Input: execution_counters/pre_check_counter.json                   │
│       ├─ Input: execution_counters/post_check_counter.json                  │
│       └─ Output: robot_reports/execution_summary.html                       │
│                                                                              │
│  Artifacts:                                                                  │
│  • robot_reports/execution_summary.html (expires in 1 month)                │
│  • robot_reports/execution_counters/                                        │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │  COMPLETE   │
                            └─────────────┘
```

## Data Flow: Execution Tracking

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     EXECUTION COUNTER DATA FLOW                            │
└───────────────────────────────────────────────────────────────────────────┘

Pipeline Run #1
───────────────
Robot Test                ExecutionCounter.py              Counter File
  │                              │                              │
  ├─ Initialize ────────────────→│                              │
  │                              ├─ Load (empty) ─────────────→ │
  ├─ Record Execution ──────────→│                              │
  │                              ├─ Increment count             │
  │                              │   Test A: count = 1          │
  │                              ├─ Save ────────────────────→  │
  │                                                             │
                                                    pre_check_counter.json
                                                    {
                                                      "Test A": {
                                                        "count": 1,
                                                        "first_run": "2025-10-08T10:00:00",
                                                        "last_run": "2025-10-08T10:00:00"
                                                      }
                                                    }
                                                             │
                                                             ├─ Git Add
                                                             ├─ Git Commit
                                                             └─ Git Push
                                                                   │
                                                                   ▼
                                                             Repository


Pipeline Run #2
───────────────
Robot Test                ExecutionCounter.py              Counter File
  │                              │                              │
  ├─ Initialize ────────────────→│                              │
  │                              ├─ Load (existing) ──────────→ │
  │                              │   Test A: count = 1          │
  ├─ Record Execution ──────────→│                              │
  │                              ├─ Increment count             │
  │                              │   Test A: count = 2          │
  │                              ├─ Save ────────────────────→  │
  │                                                             │
                                                    pre_check_counter.json
                                                    {
                                                      "Test A": {
                                                        "count": 2,
                                                        "first_run": "2025-10-08T10:00:00",
                                                        "last_run": "2025-10-08T11:00:00"
                                                      }
                                                    }
                                                             │
                                                             └─ Git Push
                                                                   │
                                                                   ▼
                                                             Repository
```

## Data Flow: Report Merging

```
┌───────────────────────────────────────────────────────────────────────────┐
│                       HISTORICAL REPORT MERGING                            │
└───────────────────────────────────────────────────────────────────────────┘

Current Run                    merge_reports.py                History Dir
    │                                 │                             │
    ├─ output.xml ──────────────────→ │                             │
    │                                 ├─ Copy to history ─────────→ │
    │                                 │   output_TIMESTAMP.xml      │
    │                                 │                             │
    │                                 ├─ List all history ←────────┘
    │                                 │   [output_1.xml,
    │                                 │    output_2.xml,
    │                                 │    ...,
    │                                 │    output_20.xml]
    │                                 │
    │                                 ├─ Keep last 20 only
    │                                 │   (delete older)
    │                                 │
    │                                 ├─ Robot rebot --merge
    │                                 │       ↓
    │                                 │   combined_output.xml
    │                                 │   combined_report.html
    │                                 │   combined_log.html
    │                                 │       ↓
    │                                 └─────────┐
    │                                           │
    ▼                                           ▼
robot_reports/pre_check/              robot_reports/pre_check/
├── report.html (current)             ├── combined_report.html
├── log.html                          ├── combined_log.html
├── output.xml                        └── history/
                                          ├── output_20251001_100000.xml
                                          ├── output_20251002_140000.xml
                                          └── output_20251008_153000.xml
                                                  │
                                                  ├─ Git Add
                                                  ├─ Git Commit
                                                  └─ Git Push
                                                        ▼
                                                  Repository
```

## File Locations and Purposes

```
infoblox_mvp1/
│
├── robot_reports/
│   │
│   ├── execution_counters/               ⭐ NEW: Execution tracking
│   │   ├── pre_check_counter.json        → Tracks pre-check test executions
│   │   └── post_check_counter.json       → Tracks post-check test executions
│   │
│   ├── pre_check/
│   │   ├── report.html                   → Current run HTML report
│   │   ├── log.html                      → Current run detailed log
│   │   ├── output.xml                    → Current run XML output
│   │   │
│   │   ├── combined_report.html          ⭐ NEW: Last 20 runs merged
│   │   ├── combined_log.html             ⭐ NEW: Last 20 logs merged
│   │   ├── combined_output.xml           ⭐ NEW: Last 20 XML merged
│   │   │
│   │   └── history/                      ⭐ NEW: Historical runs
│   │       ├── output_20251001_100000.xml
│   │       ├── output_20251002_140000.xml
│   │       └── output_20251008_153000.xml
│   │
│   ├── post_check/                       (Same structure as pre_check)
│   │   ├── report.html
│   │   ├── log.html
│   │   ├── output.xml
│   │   ├── combined_report.html          ⭐ NEW
│   │   ├── combined_log.html             ⭐ NEW
│   │   ├── combined_output.xml           ⭐ NEW
│   │   └── history/                      ⭐ NEW
│   │
│   └── execution_summary.html            ⭐ NEW: Overall statistics dashboard
│
└── utils/robot/
    ├── ExecutionCounter.py               → Library for tracking executions
    └── merge_reports.py                  → Script for merging historical reports
```

## Git Commit Timeline

```
Timeline of Git Commits by Enhanced Pipeline
─────────────────────────────────────────────

Pipeline #12345 (2025-10-08 10:00)
├─ Pre-check stage
│  └─ Commit: "Pre-check PASSED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 1]"
│     Files:
│     • robot_reports/pre_check/report.html
│     • robot_reports/pre_check/combined_report.html
│     • robot_reports/execution_counters/pre_check_counter.json
│
├─ Post-implementation stage
│  ├─ Commit: "Post-implementation PASSED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 1]"
│  │  Files:
│  │  • robot_reports/post_check/report.html
│  │  • robot_reports/post_check/combined_report.html
│  │  • robot_reports/execution_counters/post_check_counter.json
│  │
│  └─ Commit: "Post-implementation cleanup for cabgridmgr.amfam.com environment [Pipeline: 12345]"
│     Files:
│     • prod_changes/ (cleaned)
│
└─ Reporting stage
   └─ Commit: "Update execution statistics report [Pipeline: 12345]"
      Files:
      • robot_reports/execution_summary.html

Pipeline #12346 (2025-10-08 11:00)
├─ Commit: "Pre-check PASSED: cabgridmgr.amfam.com - a_record [Pipeline: 12346] [Total Executions: 2]"
├─ Commit: "Post-implementation PASSED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12346] [Total Executions: 2]"
├─ Commit: "Post-implementation cleanup for cabgridmgr.amfam.com environment [Pipeline: 12346]"
└─ Commit: "Update execution statistics report [Pipeline: 12346]"

... and so on ...
```

## Execution Summary Dashboard Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      EXECUTION SUMMARY DASHBOARD                         │
│                    (execution_summary.html)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📊 OVERALL STATISTICS                                                   │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │  Pre-Check Tests: 5     Pre-Check Executions: 47           │         │
│  │  Post-Check Tests: 5    Post-Check Executions: 52          │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                          │
│  📋 PRE-CHECK VALIDATION TESTS                                           │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Test Name                    | Executions | First Run | Last Run  │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │ Validate A Record            │     10     │ 2025-10-01│ 2025-10-08│  │
│  │ Check Duplicate Records      │      9     │ 2025-10-01│ 2025-10-08│  │
│  │ Validate CNAME Record        │      8     │ 2025-10-02│ 2025-10-08│  │
│  │ Validate Network Config      │     12     │ 2025-10-01│ 2025-10-08│  │
│  │ Check Required Fields        │      8     │ 2025-10-02│ 2025-10-08│  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ✅ POST-IMPLEMENTATION VERIFICATION TESTS                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Test Name                    | Executions | First Run | Last Run  │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │ Verify A Record Created      │     11     │ 2025-10-01│ 2025-10-08│  │
│  │ Verify DNS Resolution        │     10     │ 2025-10-01│ 2025-10-08│  │
│  │ Verify CNAME Created         │      9     │ 2025-10-02│ 2025-10-08│  │
│  │ Verify Network Exists        │     12     │ 2025-10-01│ 2025-10-08│  │
│  │ Verify DHCP Configuration    │     10     │ 2025-10-02│ 2025-10-08│  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Generated: 2025-10-08 15:30:00                                          │
│  Data tracked using ExecutionCounter.py and merged with merge_reports.py │
└─────────────────────────────────────────────────────────────────────────┘
```

## Legend

```
Symbol Legend
─────────────
✅  Completed successfully
❌  Failed
⭐  New feature in enhanced pipeline
→   Data flow direction
├─  Branch/fork
└─  End of branch
│   Continuation
▼   Flow downward
```

---

**This diagram shows the complete flow of the enhanced pipeline with execution tracking and historical reporting capabilities.**
