# Git Upload Process - What Gets Committed to Repository

## Quick Answer: YES! ✅

**Both pre-check and post-check stages upload ALL their files to the GitLab repository.**

The pipeline automatically commits and pushes reports after each stage runs.

---

## What Gets Uploaded (Complete List)

### 1️⃣ Pre-Check Stage Uploads

**What files:**
```bash
git add -f infoblox_mvp1/robot_reports/pre_check/*
git add -f infoblox_mvp1/robot_reports/execution_counters/*
```

**Files uploaded:**
```
✅ infoblox_mvp1/robot_reports/pre_check/output.xml
✅ infoblox_mvp1/robot_reports/pre_check/log.html
✅ infoblox_mvp1/robot_reports/pre_check/report.html
✅ infoblox_mvp1/robot_reports/pre_check/combined_output.xml
✅ infoblox_mvp1/robot_reports/pre_check/combined_log.html
✅ infoblox_mvp1/robot_reports/pre_check/combined_report.html ⭐
✅ infoblox_mvp1/robot_reports/pre_check/history/output_*.xml (all history files)
✅ infoblox_mvp1/robot_reports/execution_counters/pre_check_counter.json
✅ infoblox_mvp1/robot_reports/execution_counters/post_check_counter.json (if exists)
```

**Commit message:**
```
Pre-check PASSED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]
```
or
```
Pre-check FAILED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]
```

---

### 2️⃣ Post-Check Stage Uploads

**What files:**
```bash
git add -f infoblox_mvp1/robot_reports/post_check/*
git add -f infoblox_mvp1/robot_reports/execution_counters/*
```

**Files uploaded:**
```
✅ infoblox_mvp1/robot_reports/post_check/output.xml
✅ infoblox_mvp1/robot_reports/post_check/log.html
✅ infoblox_mvp1/robot_reports/post_check/report.html
✅ infoblox_mvp1/robot_reports/post_check/combined_output.xml
✅ infoblox_mvp1/robot_reports/post_check/combined_log.html
✅ infoblox_mvp1/robot_reports/post_check/combined_report.html ⭐
✅ infoblox_mvp1/robot_reports/post_check/history/output_*.xml (all history files)
✅ infoblox_mvp1/robot_reports/execution_counters/pre_check_counter.json
✅ infoblox_mvp1/robot_reports/execution_counters/post_check_counter.json
```

**Commit message:**
```
Post-implementation PASSED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 52]
```
or
```
Post-implementation FAILED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 52]
```

---

### 3️⃣ Reporting Stage Uploads

**What files:**
```bash
git add -f infoblox_mvp1/robot_reports/execution_summary.html
```

**Files uploaded:**
```
✅ infoblox_mvp1/robot_reports/execution_summary.html
```

**Commit message:**
```
Update execution statistics report [Pipeline: 12345]
```

---

## Complete Upload Flow (Timeline)

```
Pipeline Run #12345 Started
│
├─ [Pre-Check Stage]
│  ├─ Robot tests run
│  ├─ ExecutionCounter updates
│  ├─ merge_reports.py runs
│  │
│  └─ Git Commit #1 📤
│     ├─ git add pre_check/*
│     ├─ git add execution_counters/*
│     ├─ git commit -m "Pre-check PASSED: ..."
│     └─ git push origin main
│        └─ ✅ Files now in repository!
│
├─ [Deploy Stage]
│  └─ (No git commits)
│
├─ [Post-Implementation Stage]
│  ├─ Robot tests run
│  ├─ ExecutionCounter updates
│  ├─ merge_reports.py runs
│  │
│  ├─ Git Commit #2 📤
│  │  ├─ git add post_check/*
│  │  ├─ git add execution_counters/*
│  │  ├─ git commit -m "Post-implementation PASSED: ..."
│  │  └─ git push origin main
│  │     └─ ✅ Files now in repository!
│  │
│  └─ Git Commit #3 📤 (Cleanup)
│     ├─ git add -A (cleanup changes)
│     ├─ git commit -m "Post-implementation cleanup..."
│     └─ git push origin main
│        └─ ✅ Cleanup committed!
│
└─ [Reporting Stage]
   ├─ Generate execution_summary.html
   │
   └─ Git Commit #4 📤
      ├─ git add execution_summary.html
      ├─ git commit -m "Update execution statistics report..."
      └─ git push origin main
         └─ ✅ Summary committed!

Total: 4 git commits to repository per pipeline run
```

---

## Git Commits Per Pipeline Run

### Typical Pipeline Creates 4 Commits:

1. **Pre-check results** ✅
   - All pre-check reports
   - Execution counters

2. **Post-check results** ✅
   - All post-check reports
   - Execution counters (updated)

3. **Cleanup** ✅
   - Cleared prod_changes files

4. **Execution summary** ✅
   - Overall statistics dashboard

---

## Where to See Uploaded Files

### In GitLab UI

**Method 1: Repository Browser**
```
1. Go to: Repository → Files
2. Navigate to: infoblox_mvp1/robot_reports/
3. You'll see:
   ├── pre_check/
   │   ├── output.xml
   │   ├── log.html
   │   ├── report.html
   │   ├── combined_report.html ⭐
   │   └── history/
   │       └── output_*.xml
   ├── post_check/
   │   ├── (same structure)
   ├── execution_counters/
   │   ├── pre_check_counter.json
   │   └── post_check_counter.json
   └── execution_summary.html
```

**Method 2: Git Commit History**
```
1. Go to: Repository → Commits
2. You'll see commits like:
   ✅ "Pre-check PASSED: cabgridmgr.amfam.com - a_record [Pipeline: 12345] [Total Executions: 47]"
   ✅ "Post-implementation PASSED: cabgridmgr.amfam.com - a_record - add [Pipeline: 12345] [Total Executions: 52]"
   ✅ "Update execution statistics report [Pipeline: 12345]"
```

**Method 3: Specific Commit View**
```
1. Click on a commit message
2. See all files that were uploaded in that commit
3. Click "View file @ hash" to see the file contents
```

---

## Git Upload Code (How It Works)

### Pre-Check Stage (Lines 410-450)

```bash
# Configure git
git config --global user.name "GitLab_Runner"
git config --global user.email "ens@amfam.com"

# Pull latest changes to avoid conflicts
git pull origin main || true

# Stage files for commit
git add -f infoblox_mvp1/robot_reports/pre_check/* || true
git add -f infoblox_mvp1/robot_reports/execution_counters/* || true

# Check if there are changes to commit
if ! git diff --cached --quiet; then
  # Calculate total executions
  total_executions=$(python3 -c "import json; import os; ...")

  # Create commit message
  if [ $robot_exit_code -ne 0 ]; then
    commit_msg="Pre-check FAILED: $GRID_HOST - $RECORD_TYPE [Pipeline: ${CI_PIPELINE_ID}] [Total Executions: $total_executions]"
  else
    commit_msg="Pre-check PASSED: $GRID_HOST - $RECORD_TYPE [Pipeline: ${CI_PIPELINE_ID}] [Total Executions: $total_executions]"
  fi

  # Commit
  git commit -m "$commit_msg"

  # Configure remote URL with authentication
  git remote set-url origin "https://GitLab_Runner:${GITLAB_CI_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git"

  # Push with retry (3 attempts)
  for i in 1 2 3; do
    if git push origin HEAD:main; then
      echo "[OK] Pre-check results committed to repository"
      break
    else
      echo "[WARN] Push attempt $i failed, retrying..."
      sleep 2
      git pull --rebase origin main || true
    fi
  done
else
  echo "[INFO] No new test results to commit"
fi
```

### Post-Check Stage (Lines 755-795)

**Same process as pre-check**, but for post-check files.

---

## Important Features

### ✅ 1. Automatic Retry Logic

If git push fails, the pipeline **retries 3 times**:

```bash
for i in 1 2 3; do
  if git push origin HEAD:main; then
    echo "[OK] Results committed"
    break
  else
    echo "[WARN] Push attempt $i failed, retrying..."
    sleep 2
    git pull --rebase origin main || true
  fi
done
```

**Why**: Prevents conflicts if multiple pipelines run simultaneously

---

### ✅ 2. Force Add with -f Flag

```bash
git add -f infoblox_mvp1/robot_reports/pre_check/*
```

**Why**: Ensures files are added even if they're in .gitignore

---

### ✅ 3. Conditional Commit

```bash
if ! git diff --cached --quiet; then
  # Only commit if there are changes
  git commit -m "..."
fi
```

**Why**: Avoids empty commits if no files changed

---

### ✅ 4. Pull Before Push

```bash
git pull origin main || true
# ... stage files ...
git push origin HEAD:main
```

**Why**: Ensures we have latest changes, reduces conflicts

---

## What Happens to the Files?

### Lifecycle:

```
1. Pipeline runs on GitLab Runner (temporary environment)
   └─ Creates files in /tmp/gitlab-runner/.../robot_reports/

2. Files committed to Git
   └─ git add → git commit → git push

3. Files now in GitLab repository (permanent)
   └─ Accessible via Repository → Files

4. Runner environment deleted
   └─ Temporary files gone

5. Next pipeline run
   └─ Pulls existing files from repository
   └─ Updates them with new results
   └─ Commits updated files back
```

---

## Checking If Files Were Uploaded

### Method 1: Check Git Log

```bash
# Locally
git log --oneline | head -10

# You'll see:
a1b2c3d Update execution statistics report [Pipeline: 12345]
d4e5f6g Post-implementation PASSED: cabgridmgr... [Pipeline: 12345] [Total Executions: 52]
h7i8j9k Pre-check PASSED: cabgridmgr... [Pipeline: 12345] [Total Executions: 47]
```

### Method 2: Check File in Repository

```bash
# In GitLab UI
Repository → Files → infoblox_mvp1/robot_reports/pre_check/combined_report.html

# Or clone locally and check
git clone <your-repo-url>
cd infoblox_mvp1/robot_reports/pre_check
ls -la
# Should see all files including combined_report.html
```

### Method 3: Check Pipeline Logs

In the pipeline job output, look for:
```
[OK] Pre-check results committed to repository
[OK] Post-implementation results committed to repository
[OK] Cleanup changes committed and pushed
```

---

## Files NOT Uploaded

### Temporary Files (Cleaned Up)

```bash
✅ Uploaded: robot_reports/ (all files)
❌ Not uploaded: input/ (temporary CSV files)
❌ Not uploaded: prod_changes/ (cleaned up after deployment)
❌ Not uploaded: provider_config.json (deleted after use)
```

---

## Storage Considerations

### Repository Size Growth

Each pipeline run adds:
- **Pre-check**: ~500 KB - 2 MB
- **Post-check**: ~500 KB - 2 MB
- **Execution summary**: ~50 KB
- **Total per run**: ~1-4 MB

**History management**:
- Old XML files auto-deleted (keeps last 20 runs)
- Combined reports replace previous versions
- Execution counters just update (don't accumulate)

**After 100 runs**:
- Repository grows by ~100-400 MB
- But old history deleted, so actual growth is less

---

## Benefits of Uploading to Repository

### ✅ 1. Permanent Storage
- Reports preserved even after pipeline artifacts expire
- Execution history maintained indefinitely

### ✅ 2. Version Control
- Every test run tracked in git history
- Can see who ran what and when

### ✅ 3. Accessibility
- Anyone with repo access can view reports
- No need to download artifacts
- Direct links work: `https://gitlab.com/.../blob/main/robot_reports/...`

### ✅ 4. Historical Analysis
- Can go back months/years
- See test trends over time
- Compliance/audit trail

### ✅ 5. Collaboration
- Team can review test results
- Easy to share specific reports
- Integrated with Git workflow

---

## Summary Table

| What | Uploaded? | When | Where |
|------|-----------|------|-------|
| **Pre-check reports** | ✅ Yes | After pre-check stage | `robot_reports/pre_check/` |
| **Post-check reports** | ✅ Yes | After post-implementation | `robot_reports/post_check/` |
| **Execution counters** | ✅ Yes | After both stages | `robot_reports/execution_counters/` |
| **Execution summary** | ✅ Yes | After reporting stage | `robot_reports/execution_summary.html` |
| **History files** | ✅ Yes | With each stage | `robot_reports/{type}/history/` |
| **Combined reports** | ✅ Yes | With each stage | `robot_reports/{type}/combined_*.html` |
| **Temporary CSV** | ❌ No | Never | Deleted after processing |
| **Ansible configs** | ❌ No | Never | Deleted after use |

---

## Git Commits Summary

### Per Pipeline Run (4 commits):

1. **Pre-check commit**
   ```
   Commit: Pre-check PASSED: ...
   Files: pre_check/*, execution_counters/*
   ```

2. **Post-check commit**
   ```
   Commit: Post-implementation PASSED: ...
   Files: post_check/*, execution_counters/*
   ```

3. **Cleanup commit**
   ```
   Commit: Post-implementation cleanup...
   Files: prod_changes/ (cleared)
   ```

4. **Statistics commit**
   ```
   Commit: Update execution statistics report...
   Files: execution_summary.html
   ```

---

## Final Answer

### ✅ YES - Everything is uploaded!

**Pre-check stage**: ✅ Uploads ALL pre-check files + execution counters
**Post-check stage**: ✅ Uploads ALL post-check files + execution counters
**Reporting stage**: ✅ Uploads execution summary

**Total commits per run**: 4 commits
**Files uploaded**: ALL reports, logs, history, and counters
**Storage**: Permanent in GitLab repository
**Access**: Via Repository → Files or direct links

**You can access all reports anytime from the GitLab repository!** 📦✅
