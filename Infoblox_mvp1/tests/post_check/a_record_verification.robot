*** Settings ***
Documentation     A Record post-deployment verification - verify records were created
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
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/a_record.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/post_check/execution_counter.json

*** Test Cases ***

Verify A Records Created In Infoblox
    [Documentation]    Verify all A records were created successfully
    [Tags]    a_record    verification    creation
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${total}=    Get Length    ${records}
    ${verified}=    Set Variable    ${0}
    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${name}=    Set Variable    ${record['name']}
        ${view}=    Set Variable    ${record['view']}
        ${expected_ip}=    Set Variable    ${record['ipv4addr']}

        ${existing}=    Get A Records    name=${name}    view=${view}
        ${count}=    Get Length    ${existing}

        IF    ${count} == 0
            Log    ✗ Record '${name}' was NOT found in Infoblox    ERROR
            Append To List    ${failed}    ${name}
        ELSE
            ${actual_ip}=    Set Variable    ${existing[0]['ipv4addr']}
            IF    '${actual_ip}' == '${expected_ip}'
                Log    ✓ Record '${name}' verified with IP ${actual_ip}    INFO
                ${verified}=    Evaluate    ${verified} + 1
            ELSE
                Log    ✗ Record '${name}' has wrong IP: expected ${expected_ip}, got ${actual_ip}    ERROR
                Append To List    ${failed}    ${name}
            END
        END
    END

    Log    Verification Summary:    INFO
    Log    Total records: ${total}    INFO
    Log    Successfully verified: ${verified}    INFO
    Log    Failed verification: ${failed.__len__()}    INFO

    ${failed_count}=    Get Length    ${failed}
    Should Be Equal As Numbers    ${failed_count}    0    msg=Failed to verify ${failed_count} record(s): ${failed}

*** Keywords ***
Setup Execution Tracking
    [Documentation]    Initialize execution tracking for this test suite
    Initialize Execution Counter    ${COUNTER_FILE}
    Log    📊 Execution tracking initialized    INFO

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
