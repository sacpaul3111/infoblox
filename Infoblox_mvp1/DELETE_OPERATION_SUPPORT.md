# Delete Operation Support for Pre/Post Checks

## Overview
Pre-check and post-check test suites now support both **ADD** and **DELETE** operations.

---

## Changes Made

### 1. Pre-Check Tests (`tests/pre_check/a_record_validation.robot`)

**Added OPERATION_TYPE Variable:**
```robot
*** Variables ***
${OPERATION_TYPE}         add
```

**Updated Test: "Validate A Record DNS Zones Exist"**
- **For ADD operation:** Validates that DNS zones exist before creating records
- **For DELETE operation:** Skips this check (zones not needed for deletion)

```robot
Validate A Record DNS Zones Exist
    [Documentation]    Verify parent DNS zones exist in Infoblox (for add operation)
    Skip If    '${OPERATION_TYPE}' == 'delete'    Skipping zone check for delete operation
    # ... rest of validation
```

**Updated Test: "Check For Duplicate A Records Or Verify Existence"**
- **For ADD operation:** Warns if records already exist (informational)
- **For DELETE operation:** Verifies records exist before deletion (fails if not found)

```robot
Check For Duplicate A Records Or Verify Existence
    [Documentation]    For ADD: Check if records already exist (warning). For DELETE: Verify records exist before deletion

    FOR    ${record}    IN    @{records}
        ${existing}=    Get A Records    name=${name}    view=${view}
        ${count}=    Get Length    ${existing}

        IF    '${OPERATION_TYPE}' == 'add'
            # Warn if already exists
            Run Keyword If    ${count} > 0    Log    ⚠️  Record '${name}' already exists    WARN
            ...    ELSE    Log    ✓ Record '${name}' does not exist (new record)    INFO

        ELSE IF    '${OPERATION_TYPE}' == 'delete'
            # Fail if doesn't exist
            IF    ${count} == 0
                Log    ✗ Record '${name}' does NOT exist (cannot delete)    ERROR
                Append To List    ${not_found}    ${name}
            ELSE
                Log    ✓ Record '${name}' exists (ready for deletion)    INFO
            END
        END
    END

    # For delete: fail if any records don't exist
    IF    '${OPERATION_TYPE}' == 'delete'
        ${not_found_count}=    Get Length    ${not_found}
        Should Be Equal As Numbers    ${not_found_count}    0
    END
```

---

### 2. Post-Check Tests (`tests/post_check/a_record_verification.robot`)

**Added OPERATION_TYPE Variable:**
```robot
*** Variables ***
${OPERATION_TYPE}         add
```

**Renamed and Updated Test: "Verify A Records Operation Result"**
- **For ADD operation:** Verifies records were created successfully
- **For DELETE operation:** Verifies records were removed successfully

```robot
Verify A Records Operation Result
    [Documentation]    Verify operation completed: ADD (records created) or DELETE (records removed)

    IF    '${OPERATION_TYPE}' == 'add'
        Log    Verifying ADD operation: checking if records were created    INFO

        FOR    ${record}    IN    @{records}
            ${existing}=    Get A Records    name=${name}    view=${view}
            ${count}=    Get Length    ${existing}

            IF    ${count} == 0
                Log    ✗ Record '${name}' was NOT found (creation failed)    ERROR
            ELSE
                ${actual_ip}=    Set Variable    ${existing[0]['ipv4addr']}
                IF    '${actual_ip}' == '${expected_ip}'
                    Log    ✓ Record '${name}' verified with IP ${actual_ip}    INFO
                    ${verified}=    Evaluate    ${verified} + 1
                ELSE
                    Log    ✗ Record '${name}' has wrong IP    ERROR
                END
            END
        END

    ELSE IF    '${OPERATION_TYPE}' == 'delete'
        Log    Verifying DELETE operation: checking if records were removed    INFO

        FOR    ${record}    IN    @{records}
            ${existing}=    Get A Records    name=${name}    view=${view}
            ${count}=    Get Length    ${existing}

            IF    ${count} > 0
                Log    ✗ Record '${name}' still EXISTS (deletion failed)    ERROR
            ELSE
                Log    ✓ Record '${name}' successfully removed    INFO
                ${verified}=    Evaluate    ${verified} + 1
            END
        END
    END

    # Fail if any operations failed
    ${failed_count}=    Get Length    ${failed}
    Should Be Equal As Numbers    ${failed_count}    0
```

---

## How It Works

### ADD Operation Flow

**Pre-Check:**
1. ✅ Validate JSON file exists
2. ✅ Validate required fields
3. ✅ Validate IPv4 addresses
4. ✅ Validate DNS zones exist
5. ⚠️  Warn if records already exist (informational)

**Deploy Stage:**
- Ansible creates records in Infoblox

**Post-Check:**
1. ✅ Verify records were created
2. ✅ Verify records have correct IPs

---

### DELETE Operation Flow

**Pre-Check:**
1. ✅ Validate JSON file exists
2. ✅ Validate required fields
3. ✅ Validate IPv4 addresses
4. ⏭️  **Skip** DNS zone validation (not needed)
5. ✅ **Verify records exist** before deletion (fail if not found)

**Deploy Stage:**
- Ansible deletes records from Infoblox

**Post-Check:**
1. ✅ **Verify records were removed** (fail if still exist)

---

## Pipeline Configuration

The pipeline already passes `OPERATION_TYPE` to the Robot tests:

```yaml
robot \
  --variable GRID_HOST:$GRID_HOST \
  --variable RECORD_TYPE:$RECORD_TYPE \
  --variable OPERATION_TYPE:$OPERATION_TYPE \
  --variable PIPELINE_ID:${CI_PIPELINE_ID} \
  $test_suite
```

**The variable is automatically passed from pipeline inputs to the test suites.**

---

## Benefits

### 1. **Flexible Test Logic**
- Same test files handle both add and delete operations
- No need for separate test suites

### 2. **Proper Validation**
- ADD: Ensures DNS zones exist before creation
- DELETE: Ensures records exist before deletion

### 3. **Clear Feedback**
- ADD: Shows if records already exist (warning)
- DELETE: Shows if records don't exist (error)

### 4. **Accurate Verification**
- ADD: Confirms records were created with correct IPs
- DELETE: Confirms records were removed completely

---

## Test Behavior Comparison

| Test | ADD Operation | DELETE Operation |
|------|---------------|------------------|
| **Validate JSON File Exists** | ✅ Check file exists | ✅ Check file exists |
| **Validate Required Fields** | ✅ Validate all fields | ✅ Validate all fields |
| **Validate IPv4 Addresses** | ✅ Validate format | ✅ Validate format |
| **Validate DNS Zones Exist** | ✅ Must exist | ⏭️  **Skipped** |
| **Check Record Existence** | ⚠️  Warn if exists | ❌ **Fail if doesn't exist** |
| **Post-Check Verification** | ✅ Records created | ✅ **Records deleted** |

---

## Example Output

### ADD Operation - Pre-Check
```
Validate A Record JSON File Exists
✓ A record JSON file found

Validate A Record Required Fields
✓ Record 'test1.example.com' has all required fields
✓ Record 'test2.example.com' has all required fields

Validate A Record IPv4 Addresses
✓ Valid IP address: 192.168.1.10 for test1.example.com
✓ Valid IP address: 192.168.1.11 for test2.example.com

Validate A Record DNS Zones Exist
✓ DNS zone exists: example.com in view default

Check For Duplicate A Records Or Verify Existence
⚠️  Record 'test1.example.com' already exists in Infoblox with IP 192.168.1.10
✓ Record 'test2.example.com' does not exist (new record)
```

### DELETE Operation - Pre-Check
```
Validate A Record JSON File Exists
✓ A record JSON file found

Validate A Record Required Fields
✓ Record 'test1.example.com' has all required fields
✓ Record 'test2.example.com' has all required fields

Validate A Record IPv4 Addresses
✓ Valid IP address: 192.168.1.10 for test1.example.com
✓ Valid IP address: 192.168.1.11 for test2.example.com

Validate A Record DNS Zones Exist
⏭️  SKIPPED: Skipping zone check for delete operation

Check For Duplicate A Records Or Verify Existence
✓ Record 'test1.example.com' exists with IP 192.168.1.10 (ready for deletion)
✗ Record 'test2.example.com' does NOT exist in Infoblox (cannot delete)
❌ FAILED: 1 record(s) not found for deletion: ['test2.example.com']
```

### ADD Operation - Post-Check
```
Verify A Records Operation Result
Verifying ADD operation: checking if records were created

✓ Record 'test1.example.com' verified with IP 192.168.1.10
✓ Record 'test2.example.com' verified with IP 192.168.1.11

ADD Operation Summary:
Total records to create: 2
Successfully created: 2
Failed to create: 0
```

### DELETE Operation - Post-Check
```
Verify A Records Operation Result
Verifying DELETE operation: checking if records were removed

✓ Record 'test1.example.com' successfully removed from Infoblox
✓ Record 'test2.example.com' successfully removed from Infoblox

DELETE Operation Summary:
Total records to delete: 2
Successfully deleted: 2
Failed to delete: 0
```

---

## Files Modified

1. **`tests/pre_check/a_record_validation.robot`**
   - Added `${OPERATION_TYPE}` variable
   - Updated DNS zone validation to skip for delete
   - Updated duplicate check to verify existence for delete

2. **`tests/post_check/a_record_verification.robot`**
   - Added `${OPERATION_TYPE}` variable
   - Renamed test to "Verify A Records Operation Result"
   - Added conditional logic for add/delete verification

---

## Next Steps

### To Apply to Other Record Types:

1. **CNAME Record:**
   - Update `tests/pre_check/cname_record_validation.robot`
   - Update `tests/post_check/cname_record_verification.robot`

2. **Network:**
   - Update `tests/pre_check/network_validation.robot`
   - Update `tests/post_check/network_verification.robot`

### Pattern to Follow:
- Add `${OPERATION_TYPE}` variable
- Skip DNS zone checks for delete operations
- Verify existence before deletion in pre-check
- Verify removal in post-check for delete operations

---

## Summary

✅ Pre-check and post-check now support both ADD and DELETE operations
✅ Tests adapt behavior based on OPERATION_TYPE variable
✅ DELETE pre-check ensures records exist before deletion
✅ DELETE post-check verifies records were removed
✅ ADD operations work as before with enhanced logging
✅ No pipeline changes needed - OPERATION_TYPE already passed

**Ready for testing with both add and delete operations!** 🚀
