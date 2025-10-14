*** Settings ***
Documentation     Network Range post-deployment verification - supports both add and delete operations
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
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/network_range.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/post_check/execution_counter.json
${OPERATION_TYPE}         add

*** Test Cases ***

Verify Network Ranges Operation Result
    [Documentation]    Verify operation completed successfully: ADD (ranges created) or DELETE (ranges removed)
    [Tags]    network_range    verification    operation_result
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${total}=    Get Length    ${records}
    ${verified}=    Set Variable    ${0}
    ${failed}=    Create List

    IF    '${OPERATION_TYPE}' == 'add'
        Log    Verifying ADD operation: checking if network ranges were created    INFO

        FOR    ${record}    IN    @{records}
            ${network}=    Set Variable    ${record['network']}
            ${start}=    Set Variable    ${record['start_addr']}
            ${end}=    Set Variable    ${record['end_addr']}

            ${existing}=    Get Network Ranges    network=${network}    start_addr=${start}    end_addr=${end}
            ${count}=    Get Length    ${existing}

            IF    ${count} == 0
                Log    ✗ Network Range '${start}-${end}' was NOT found in Infoblox (creation failed)    ERROR
                Append To List    ${failed}    ${start}-${end}
            ELSE
                Log    ✓ Network Range '${start}-${end}' verified    INFO
                ${verified}=    Evaluate    ${verified} + 1
            END
        END

        Log    ADD Operation Summary:    INFO
        Log    Total network ranges to create: ${total}    INFO
        Log    Successfully created: ${verified}    INFO
        Log    Failed to create: ${failed.__len__()}    INFO

    ELSE IF    '${OPERATION_TYPE}' == 'delete'
        Log    Verifying DELETE operation: checking if network ranges were removed    INFO

        FOR    ${record}    IN    @{records}
            ${network}=    Set Variable    ${record['network']}
            ${start}=    Set Variable    ${record['start_addr']}
            ${end}=    Set Variable    ${record['end_addr']}

            ${existing}=    Get Network Ranges    network=${network}    start_addr=${start}    end_addr=${end}
            ${count}=    Get Length    ${existing}

            IF    ${count} > 0
                Log    ✗ Network Range '${start}-${end}' still EXISTS in Infoblox (deletion failed)    ERROR
                Append To List    ${failed}    ${start}-${end}
            ELSE
                Log    ✓ Network Range '${start}-${end}' successfully removed from Infoblox    INFO
                ${verified}=    Evaluate    ${verified} + 1
            END
        END

        Log    DELETE Operation Summary:    INFO
        Log    Total network ranges to delete: ${total}    INFO
        Log    Successfully deleted: ${verified}    INFO
        Log    Failed to delete: ${failed.__len__()}    INFO
    END

    ${failed_count}=    Get Length    ${failed}
    Should Be Equal As Numbers    ${failed_count}    0    msg=${OPERATION_TYPE} operation failed for ${failed_count} network range(s): ${failed}

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
