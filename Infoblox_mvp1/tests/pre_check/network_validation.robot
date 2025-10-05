*** Settings ***
Documentation     Network validation tests - essential pre-deployment checks only
Library           ../../utils/robot/InfobloxAPI.py
Library           ../../utils/robot/ExecutionCounter.py
Library           Collections
Library           OperatingSystem
Suite Setup       Setup Execution Tracking
Suite Teardown    Teardown Execution Tracking

*** Variables ***
${GRID_HOST}              cabgridmgr.amfam.com
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/network.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json

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

Validate Network Views Exist
    [Documentation]    Verify network views exist in Infoblox
    [Tags]    network    validation    network_view
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${network_views}=    Create List

    FOR    ${record}    IN    @{records}
        ${network_view}=    Get From Dictionary    ${record}    network_view    default=default

        ${exists}=    Run Keyword And Return Status    List Should Contain Value    ${network_views}    ${network_view}
        Run Keyword Unless    ${exists}    Append To List    ${network_views}    ${network_view}
    END

    FOR    ${network_view}    IN    @{network_views}
        ${views}=    Get Network Views    name=${network_view}
        ${view_count}=    Get Length    ${views}
        Should Be True    ${view_count} > 0    msg=Network view '${network_view}' does not exist
        Log    ✓ Network view exists: ${network_view}    INFO
    END

Validate Grid Members Exist
    [Documentation]    Verify all grid members exist in Infoblox (critical check)
    [Tags]    network    validation    grid_members
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${missing_members}=    Create List

    FOR    ${record}    IN    @{records}
        ${network}=    Set Variable    ${record['network']}
        ${members}=    Set Variable    ${record['members']}

        FOR    ${member}    IN    @{members}
            ${has_name}=    Run Keyword And Return Status    Dictionary Should Contain Key    ${member}    name

            IF    ${has_name}
                ${member_name}=    Set Variable    ${member['name']}
                ${grid_members}=    Get Grid Members    host_name=${member_name}
                ${member_count}=    Get Length    ${grid_members}

                IF    ${member_count} == 0
                    Log    ✗ ERROR: Grid member '${member_name}' does NOT exist for network ${network}    ERROR
                    Append To List    ${missing_members}    ${member_name}
                ELSE
                    Log    ✓ Grid member exists: ${member_name}    INFO
                END
            END
        END
    END

    ${missing_count}=    Get Length    ${missing_members}
    Should Be Equal As Numbers    ${missing_count}    0    msg=Missing grid members: ${missing_members}

*** Keywords ***
Setup Execution Tracking
    [Documentation]    Initialize execution tracking for this test suite
    Initialize Execution Counter    ${COUNTER_FILE}
    Log    📊 Execution tracking initialized    INFO
    Record Test Execution    Network Validation Suite
    Log Execution Statistics

Teardown Execution Tracking
    [Documentation]    Save execution tracking data and display statistics
    Log Execution Statistics
    Save Execution Counter
    ${total}=    Get Total Test Executions
    Log    ✅ Total test suite executions: ${total}    INFO
