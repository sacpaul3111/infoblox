*** Settings ***
Documentation     Fixed Address validation tests - supports both add and delete operations
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
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/fixed_address.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json
${OPERATION_TYPE}         add

*** Test Cases ***
Validate Fixed Address JSON File Exists
    [Documentation]    Verify that the Fixed Address JSON file exists
    [Tags]    fixed_address    validation    file_check
    File Should Exist    ${JSON_FILE}
    Log    ✓ Fixed Address JSON file found    INFO

Validate Fixed Address Required Fields
    [Documentation]    Verify all Fixed Addresses have required fields
    [Tags]    fixed_address    validation    required_fields
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        Dictionary Should Contain Key    ${record}    ipv4addr    msg=Missing 'ipv4addr' field
        Dictionary Should Contain Key    ${record}    mac    msg=Missing 'mac' field
        Log    ✓ Fixed Address '${record['ipv4addr']}' has all required fields    INFO
    END

Verify Fixed Address Existence Based On Operation
    [Documentation]    For ADD: Fail if fixed addresses exist. For DELETE: Fail if fixed addresses don't exist
    [Tags]    fixed_address    validation    existence_check
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${ipv4addr}=    Set Variable    ${record['ipv4addr']}
        ${mac}=    Set Variable    ${record['mac']}

        ${existing}=    Get Fixed Addresses    ipv4addr=${ipv4addr}
        ${count}=    Get Length    ${existing}

        IF    '${OPERATION_TYPE}' == 'add'
            IF    ${count} > 0
                Log    ✗ Fixed Address '${ipv4addr}' ALREADY EXISTS in Infoblox (cannot add)    ERROR
                Append To List    ${failed}    ${ipv4addr}
            ELSE
                Log    ✓ Fixed Address '${ipv4addr}' does not exist (ready for creation)    INFO
            END
        ELSE IF    '${OPERATION_TYPE}' == 'delete'
            IF    ${count} == 0
                Log    ✗ Fixed Address '${ipv4addr}' does NOT exist in Infoblox (cannot delete)    ERROR
                Append To List    ${failed}    ${ipv4addr}
            ELSE
                Log    ✓ Fixed Address '${ipv4addr}' exists (ready for deletion)    INFO
            END
        END
    END

    ${failed_count}=    Get Length    ${failed}
    IF    '${OPERATION_TYPE}' == 'add'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} fixed address(es) already exist and cannot be added: ${failed}
    ELSE IF    '${OPERATION_TYPE}' == 'delete'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} fixed address(es) not found and cannot be deleted: ${failed}
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
