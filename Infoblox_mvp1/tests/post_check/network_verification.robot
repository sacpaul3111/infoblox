*** Settings ***
Documentation     Network post-deployment verification - verify networks were created
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
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/network.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/post_check/execution_counter.json

*** Test Cases ***
Verify Networks Created In Infoblox
    [Documentation]    Verify all networks were created successfully
    [Tags]    network    verification    creation
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${total}=    Get Length    ${records}
    ${verified}=    Set Variable    ${0}
    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${network}=    Set Variable    ${record['network']}
        ${network_view}=    Get From Dictionary    ${record}    network_view    default=default

        ${existing}=    Get Networks    network=${network}    network_view=${network_view}
        ${count}=    Get Length    ${existing}

        IF    ${count} == 0
            Log    ✗ Network '${network}' was NOT found in Infoblox    ERROR
            Append To List    ${failed}    ${network}
        ELSE
            Log    ✓ Network '${network}' verified in network view ${network_view}    INFO
            ${verified}=    Evaluate    ${verified} + 1

            # Optionally verify comment if specified
            ${has_comment}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${record}    comment
            IF    ${has_comment}
                ${expected_comment}=    Set Variable    ${record['comment']}
                ${actual_comment}=    Get From Dictionary    ${existing[0]}    comment    default=
                IF    '${actual_comment}' == '${expected_comment}'
                    Log    ✓ Comment matches: ${expected_comment}    INFO
                ELSE
                    Log    ⚠️  Comment mismatch: expected '${expected_comment}', got '${actual_comment}'    WARN
                END
            END
        END
    END

    Log    Verification Summary:    INFO
    Log    Total networks: ${total}    INFO
    Log    Successfully verified: ${verified}    INFO
    Log    Failed verification: ${failed.__len__()}    INFO

    ${failed_count}=    Get Length    ${failed}
    Should Be Equal As Numbers    ${failed_count}    0    msg=Failed to verify ${failed_count} network(s): ${failed}

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
