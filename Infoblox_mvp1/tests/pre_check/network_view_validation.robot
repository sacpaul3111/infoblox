*** Settings ***
Documentation     Network View validation tests - supports both add and delete operations
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
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/network_view.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json
${OPERATION_TYPE}         add

*** Test Cases ***
Validate Network View JSON File Exists
    [Documentation]    Verify that the Network View JSON file exists
    [Tags]    network_view    validation    file_check
    File Should Exist    ${JSON_FILE}
    Log    ✓ Network View JSON file found    INFO

Validate Network View Required Fields
    [Documentation]    Verify all Network Views have required fields
    [Tags]    network_view    validation    required_fields
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        Dictionary Should Contain Key    ${record}    name    msg=Missing 'name' field
        Log    ✓ Network View '${record['name']}' has all required fields    INFO
    END

Verify Network View Existence Based On Operation
    [Documentation]    For ADD: Fail if network views exist. For DELETE: Fail if network views don't exist
    [Tags]    network_view    validation    existence_check
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${name}=    Set Variable    ${record['name']}

        ${existing}=    Get Network Views    name=${name}
        ${count}=    Get Length    ${existing}

        IF    '${OPERATION_TYPE}' == 'add'
            IF    ${count} > 0
                Log    ✗ Network View '${name}' ALREADY EXISTS in Infoblox (cannot add)    ERROR
                Append To List    ${failed}    ${name}
            ELSE
                Log    ✓ Network View '${name}' does not exist (ready for creation)    INFO
            END
        ELSE IF    '${OPERATION_TYPE}' == 'delete'
            IF    ${count} == 0
                Log    ✗ Network View '${name}' does NOT exist in Infoblox (cannot delete)    ERROR
                Append To List    ${failed}    ${name}
            ELSE
                Log    ✓ Network View '${name}' exists (ready for deletion)    INFO
            END
        END
    END

    ${failed_count}=    Get Length    ${failed}
    IF    '${OPERATION_TYPE}' == 'add'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} network view(s) already exist and cannot be added: ${failed}
    ELSE IF    '${OPERATION_TYPE}' == 'delete'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} network view(s) not found and cannot be deleted: ${failed}
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
