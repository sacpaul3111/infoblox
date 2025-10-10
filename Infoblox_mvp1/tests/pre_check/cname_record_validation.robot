*** Settings ***
Documentation     CNAME Record validation tests - supports both add and delete operations
Library           ../../utils/robot/InfobloxAPI.py
Library           ../../utils/robot/ExecutionCounter.py
Library           Collections
Library           OperatingSystem
Library           BuiltIn
Suite Setup       Setup Execution Tracking
Suite Teardown    Teardown Execution Tracking
Test Teardown     Record Individual Test Result

*** Variables ***
${GRID_HOST}              cabgridmgr.amfam.com
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/cname_record.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json
${OPERATION_TYPE}         add

*** Test Cases ***
Validate CNAME Record JSON File Exists
    [Documentation]    Verify that the CNAME record JSON file exists
    [Tags]    cname_record    validation    file_check
    File Should Exist    ${JSON_FILE}
    Log    ✓ CNAME record JSON file found    INFO

Validate CNAME Record Required Fields
    [Documentation]    Verify all CNAME records have required fields (name, canonical, view)
    [Tags]    cname_record    validation    required_fields
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        Dictionary Should Contain Key    ${record}    name    msg=Missing 'name' field
        Dictionary Should Contain Key    ${record}    canonical    msg=Missing 'canonical' field
        Dictionary Should Contain Key    ${record}    view    msg=Missing 'view' field
        Log    ✓ Record '${record['name']}' has all required fields    INFO
    END

Verify CNAME Record Existence Based On Operation
    [Documentation]    For ADD: Fail if records exist. For DELETE: Fail if records don't exist
    [Tags]    cname_record    validation    existence_check
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${name}=    Set Variable    ${record['name']}
        ${view}=    Set Variable    ${record['view']}

        ${existing}=    Get CNAME Records    name=${name}    view=${view}
        ${count}=    Get Length    ${existing}

        IF    '${OPERATION_TYPE}' == 'add'
            # For ADD operation: FAIL if already exists
            IF    ${count} > 0
                Log    ✗ Record '${name}' ALREADY EXISTS in Infoblox with canonical ${existing[0]['canonical']} (cannot add)    ERROR
                Append To List    ${failed}    ${name}
            ELSE
                Log    ✓ Record '${name}' does not exist (ready for creation)    INFO
            END
        ELSE IF    '${OPERATION_TYPE}' == 'delete'
            # For DELETE operation: FAIL if doesn't exist
            IF    ${count} == 0
                Log    ✗ Record '${name}' does NOT exist in Infoblox (cannot delete)    ERROR
                Append To List    ${failed}    ${name}
            ELSE
                Log    ✓ Record '${name}' exists with canonical ${existing[0]['canonical']} (ready for deletion)    INFO
            END
        END
    END

    # Fail if any records have issues
    ${failed_count}=    Get Length    ${failed}
    IF    '${OPERATION_TYPE}' == 'add'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} CNAME record(s) already exist and cannot be added: ${failed}
    ELSE IF    '${OPERATION_TYPE}' == 'delete'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} CNAME record(s) not found and cannot be deleted: ${failed}
    END

*** Keywords ***
Setup Execution Tracking
    [Documentation]    Initialize execution tracking for this test suite
    Initialize Execution Counter    ${COUNTER_FILE}
    Log    📊 Execution tracking initialized for ${OPERATION_TYPE} operation    INFO

Teardown Execution Tracking
    [Documentation]    Save execution tracking data and display statistics
    Log Execution Statistics
    Save Execution Counter
    ${total}=    Get Total Test Executions
    Log    ✅ Total test suite executions: ${total}    INFO

Record Individual Test Result
    [Documentation]    Record the result of each individual test
    ${test_name}=    Set Variable    ${TEST NAME}
    ${test_status}=    Set Variable    ${TEST STATUS}
    Record Test Execution    ${test_name}    ${test_status}
    Log    📊 Recorded: ${test_name} - ${test_status}    INFO
