*** Settings ***
Documentation     Network validation tests - supports both add and delete operations
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
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json
${OPERATION_TYPE}         add

*** Test Cases ***
Validate Network JSON File Exists
    [Documentation]    Verify that the network JSON file exists
    [Tags]    network    validation    file_check
    File Should Exist    ${JSON_FILE}
    Log    ✓ Network JSON file found    INFO

Validate Network Required Fields
    [Documentation]    Verify all networks have required fields (network, members)
    [Tags]    network    validation    required_fields
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        Dictionary Should Contain Key    ${record}    network    msg=Missing 'network' field
        Dictionary Should Contain Key    ${record}    members    msg=Missing 'members' field

        # Verify members is a list and not empty
        ${members}=    Set Variable    ${record['members']}
        ${is_list}=    Run Keyword And Return Status    Should Be True    isinstance($members, list)
        Should Be True    ${is_list}    msg=Members field must be a list

        ${member_count}=    Get Length    ${members}
        Should Be True    ${member_count} > 0    msg=Members list cannot be empty for network ${record['network']}

        Log    ✓ Network '${record['network']}' has all required fields with ${member_count} member(s)    INFO
    END

Validate Network CIDR Format
    [Documentation]    Verify all networks are in valid CIDR format
    [Tags]    network    validation    cidr_format
    Connect To Infoblox Grid    ${GRID_HOST}
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        ${network}=    Set Variable    ${record['network']}
        Validate Network CIDR    ${network}
        Log    ✓ Valid network CIDR: ${network}    INFO
    END

Verify Network Existence Based On Operation
    [Documentation]    For ADD: Fail if networks exist. For DELETE: Fail if networks don't exist
    [Tags]    network    validation    existence_check
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${network}=    Set Variable    ${record['network']}
        ${network_view}=    Set Variable If    'networkview' in $record    ${record['networkview']}    default

        ${existing}=    Get Networks    network=${network}    network_view=${network_view}
        ${count}=    Get Length    ${existing}

        IF    '${OPERATION_TYPE}' == 'add'
            # For ADD operation: FAIL if already exists
            IF    ${count} > 0
                Log    ✗ Network '${network}' ALREADY EXISTS in Infoblox (cannot add)    ERROR
                Append To List    ${failed}    ${network}
            ELSE
                Log    ✓ Network '${network}' does not exist (ready for creation)    INFO
            END
        ELSE IF    '${OPERATION_TYPE}' == 'delete'
            # For DELETE operation: FAIL if doesn't exist
            IF    ${count} == 0
                Log    ✗ Network '${network}' does NOT exist in Infoblox (cannot delete)    ERROR
                Append To List    ${failed}    ${network}
            ELSE
                Log    ✓ Network '${network}' exists (ready for deletion)    INFO
            END
        END
    END

    # Fail if any networks have issues
    ${failed_count}=    Get Length    ${failed}
    IF    '${OPERATION_TYPE}' == 'add'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} network(s) already exist and cannot be added: ${failed}
    ELSE IF    '${OPERATION_TYPE}' == 'delete'
        Should Be Equal As Numbers    ${failed_count}    0    msg=${failed_count} network(s) not found and cannot be deleted: ${failed}
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
