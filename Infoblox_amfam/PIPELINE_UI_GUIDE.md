# GitLab Pipeline UI Guide

## What You'll See in GitLab Web Interface

### Step 1: Run Pipeline Page

When you click **"Run Pipeline"**, you'll see this form:

```
╔════════════════════════════════════════════════════════════════╗
║                    Run Pipeline                                ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Branch: main                                          [▼]     ║
║                                                                ║
║  ┌────────────────────────────────────────────────────────┐   ║
║  │ Variables                                              │   ║
║  ├────────────────────────────────────────────────────────┤   ║
║  │                                                        │   ║
║  │  environment [dropdown]                                │   ║
║  │  ┌──────────────────────────────────────────────┐     │   ║
║  │  │ cabgridmgr                               [▼] │     │   ║
║  │  │ ─ cabgridmgr                                 │     │   ║
║  │  │ ─ etsl                                       │     │   ║
║  │  │ ─ nhq                                        │     │   ║
║  │  │ ─ enterprise                                 │     │   ║
║  │  └──────────────────────────────────────────────┘     │   ║
║  │  Select the Grid environment to deploy to             │   ║
║  │                                                        │   ║
║  │  RECORD_TYPE [dropdown]                                │   ║
║  │  ┌──────────────────────────────────────────────┐     │   ║
║  │  │ a_record                                 [▼] │     │   ║
║  │  │ ─ a_record                                   │     │   ║
║  │  │ ─ aaaa_record                                │     │   ║
║  │  │ ─ cname_record                               │     │   ║
║  │  │ ─ fixed_address                              │     │   ║
║  │  │ ─ host_record                                │     │   ║
║  │  │ ─ mx_record                                  │     │   ║
║  │  │ ─ network                                    │     │   ║
║  │  │ ─ ptr_record                                 │     │   ║
║  │  │ ─ network_range                              │     │   ║
║  │  │ ─ srv_record                                 │     │   ║
║  │  │ ─ txt_record                                 │     │   ║
║  │  │ ─ nios_zone                                  │     │   ║
║  │  └──────────────────────────────────────────────┘     │   ║
║  │  Select the record type to process                    │   ║
║  │                                                        │   ║
║  │  OPERATION_TYPE [dropdown]                             │   ║
║  │  ┌──────────────────────────────────────────────┐     │   ║
║  │  │ add                                      [▼] │     │   ║
║  │  │ ─ add                                        │     │   ║
║  │  │ ─ delete                                     │     │   ║
║  │  └──────────────────────────────────────────────┘     │   ║
║  │  Select operation: add or delete                      │   ║
║  │                                                        │   ║
║  │  CSV_DATA [large text field]                          │   ║
║  │  ┌──────────────────────────────────────────────┐     │   ║
║  │  │                                              │     │   ║
║  │  │ Paste your CSV data here...                  │     │   ║
║  │  │                                              │     │   ║
║  │  │ Example for A Record:                        │     │   ║
║  │  │ name,ipv4addr,view,comment                   │     │   ║
║  │  │ server1.com,10.1.1.1,prod,Web               │     │   ║
║  │  │                                              │     │   ║
║  │  │                                              │     │   ║
║  │  │                                              │     │   ║
║  │  │                                              │     │   ║
║  │  │                                              │     │   ║
║  │  └──────────────────────────────────────────────┘     │   ║
║  │  Max: 5000 characters (~200 records)                  │   ║
║  │  Column order is flexible                             │   ║
║  │                                                        │   ║
║  └────────────────────────────────────────────────────────┘   ║
║                                                                ║
║                               [Run Pipeline]                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

### Step 2: Pipeline Execution View

After clicking "Run Pipeline", you'll see:

```
╔════════════════════════════════════════════════════════════════╗
║  Pipeline #12345                                               ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  [🟢 build_container]  ──→  [🟢 file_processing]  ──→         ║
║                                                                ║
║  [🟢 server_connection_test]  ──→  [🟢 json_validation]  ──→  ║
║                                                                ║
║  [🟢 validation_checkpoint]  ──→  [🔵 run_ansible_playbook]   ║
║                                   (Manual - Click Play)        ║
║                                                                ║
║                            ↓ (After deployment)                ║
║                                                                ║
║                   [⚪ post_implementation]                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

Legend:
🟢 = Passed (Green)
🔵 = Manual Action Required (Blue)
🟡 = Running (Yellow)
❌ = Failed (Red)
⚪ = Pending (Gray)
```

### Step 3: File Processing Stage Output

Click on "file_processing" to see:

```
==========================================
  INFOBLOX RECORD PROCESSING PIPELINE
==========================================
Target Grid: cabgridmgr.amfam.com
Record Type: a_record
Operation: add
==========================================

[1/5] Installing dependencies...
[2/5] Validating input data...
   Input size: 245 characters
   Estimated records: 3
   [OK] Validation passed

[3/5] Creating input file...
   Saved to: input/a_record.csv

[4/5] Input data preview:
----------------------------------------
name,ipv4addr,view,comment,Environment,Owner
webserver1.amfam.com,192.168.1.10,production,Web server,prod,teamA
dbserver1.amfam.com,192.168.1.11,production,Database server,prod,teamB
----------------------------------------

[5/5] Processing records...
Detected record type: a_record
Successfully processed 3 a_record records
Output: add/prod_changes/cabgridmgr.amfam.com/a_record.json

==========================================
  PROCESSING COMPLETE
==========================================
Generated files:
add/prod_changes/cabgridmgr.amfam.com/a_record.json

Records will be deployed to: cabgridmgr.amfam.com
Using playbook: add/playbooks/nios_a_record.yml
==========================================
```

### Step 4: Validation Checkpoint Output

```
===========================================================
  PRE-IMPLEMENTATION VALIDATION COMPLETE
===========================================================
Grid: cabgridmgr.amfam.com
Record Type: a_record
Operation: add

Ready to deploy. Run deployment stage manually to proceed.
===========================================================
```

### Step 5: Manual Deployment Trigger

You'll see the "run_ansible_playbook" stage with a **PLAY** button:

```
┌──────────────────────────────────────────────┐
│  run_ansible_playbook                        │
│                                              │
│  Manual action required                      │
│                                              │
│              [▶ Play]                        │
│                                              │
└──────────────────────────────────────────────┘
```

**Click the PLAY button to execute deployment**

### Step 6: Deployment Output

After clicking Play:

```
==========================================
  ANSIBLE DEPLOYMENT
==========================================
Grid: cabgridmgr.amfam.com
Record Type: a_record
Playbook: add/playbooks/nios_a_record.yml
Operation: add
==========================================

Executing playbook...

PLAY [localhost] *******************************************

TASK [Set fact from JSON file data] **********************
ok: [localhost]

TASK [Ensure A records are present] **********************
changed: [localhost] => (item={'name': 'webserver1.amfam.com', 'ipv4addr': '192.168.1.10'...})
changed: [localhost] => (item={'name': 'dbserver1.amfam.com', 'ipv4addr': '192.168.1.11'...})
changed: [localhost] => (item={'name': 'appserver1.amfam.com', 'ipv4addr': '192.168.1.12'...})

PLAY RECAP *********************************************
localhost  : ok=2    changed=1    unreachable=0    failed=0

==========================================
  DEPLOYMENT SUCCESSFUL
==========================================
```

## 📱 Mobile/Tablet View

The interface is responsive and works on mobile devices, but for large CSV data, desktop is recommended.

## 🎨 Color Coding

### Stage Status Colors in GitLab

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green | passed | Stage completed successfully |
| 🔵 Blue | manual | Waiting for manual trigger |
| 🟡 Yellow | running | Stage currently executing |
| ⚪ Gray | pending | Stage waiting to run |
| 🟠 Orange | warning | Stage completed with warnings |
| ❌ Red | failed | Stage failed, check logs |

## 📊 Progress Indicators

### Pipeline Timeline View

```
Start → File Processing (2 min) → Validation (1 min) → ⏸️ Manual Deploy → Complete
```

### Typical Execution Times

- **File Processing:** 1-3 minutes
- **Pre-Implementation:** 1-2 minutes
- **Validation Checkpoint:** < 10 seconds
- **Deployment:** 2-5 minutes (depends on record count)
- **Post-Implementation:** < 1 minute

**Total Time:** ~5-10 minutes (excluding manual trigger wait)

## 🔍 Where to Find Things

### Pipeline List
**CI/CD → Pipelines**
- Shows all pipeline runs
- Status, duration, triggered by
- Click pipeline number to view details

### Pipeline Details
Click on any pipeline to see:
- Stage-by-stage view
- Job logs
- Artifacts (JSON files)
- Variables used

### Job Logs
Click on any stage to see:
- Detailed execution logs
- Error messages
- Processing output
- Validation results

### Artifacts
Click "Browse" button to see:
- Generated JSON files
- Input CSV files
- Available for 1 hour

## 💡 Quick Tips

1. **Copy Pipeline Number** - Easy to reference in tickets
2. **Download Artifacts** - Save JSON for records
3. **Check Each Stage** - Review logs before deploying
4. **Bookmark Pipeline URL** - Quick access
5. **Use Browser Search** - Find specific records in logs

## 🎯 Common UI Actions

### Retry Failed Stage
Click retry button (circular arrow) on failed stage

### Cancel Pipeline
Click stop button (square) to cancel running pipeline

### Download Artifacts
Click "Browse" or "Download" button on successful stage

### View Raw Logs
Click "Show complete raw" link in job logs

### Expand All Stages
Click "Expand all" to see all job outputs

## 📸 Screenshot Locations

When documenting issues, capture:
1. Run Pipeline form (with variables filled)
2. Pipeline stage view (showing failed stage)
3. Job logs (showing error messages)
4. Artifacts list (if generated)

## 🚀 Quick Access

### Direct Links (replace {project})

- Pipeline List: `gitlab.com/{project}/-/pipelines`
- Run Pipeline: `gitlab.com/{project}/-/pipelines/new`
- CI/CD Settings: `gitlab.com/{project}/-/settings/ci_cd`

---

**Pro Tip:** Bookmark the "Run Pipeline" page for quick access!
