*** Settings ***
Documentation     A Record validation tests - essential pre-deployment checks only
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
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json

*** Test Cases ***
Validate A Record JSON File Exists
    [Documentation]    Verify that the A record JSON file exists
    [Tags]    a_record    validation    file_check
    File Should Exist    ${JSON_FILE}
    Log    ✓ A record JSON file found    INFO

Validate A Record Required Fields
    [Documentation]    Verify all A records have required fields
    [Tags]    a_record    validation    required_fields
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        Dictionary Should Contain Key    ${record}    name    msg=Missing 'name' field
        Dictionary Should Contain Key    ${record}    ipv4addr    msg=Missing 'ipv4addr' field
        Dictionary Should Contain Key    ${record}    view    msg=Missing 'view' field
        Log    ✓ Record '${record['name']}' has all required fields    INFO
    END

Validate A Record IPv4 Addresses
    [Documentation]    Verify all IPv4 addresses are in valid format
    [Tags]    a_record    validation    ip_format
    Connect To Infoblox Grid    ${GRID_HOST}
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        ${ip}=    Set Variable    ${record['ipv4addr']}
        Validate IPv4 Address    ${ip}
        Log    ✓ Valid IP address: ${ip} for ${record['name']}    INFO
    END

Validate A Record DNS Zones Exist
    [Documentation]    Verify parent DNS zones exist in Infoblox
    [Tags]    a_record    validation    dns_zone
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    # Get unique parent domains
    ${parent_domains}=    Create List

    FOR    ${record}    IN    @{records}
        ${parent}=    Extract Parent Domain    ${record['name']}
        ${view}=    Set Variable    ${record['view']}
        ${domain_view}=    Set Variable    ${parent}|${view}

        ${exists}=    Run Keyword And Return Status    List Should Contain Value    ${parent_domains}    ${domain_view}
        Run Keyword Unless    ${exists}    Append To List    ${parent_domains}    ${domain_view}
    END

    FOR    ${domain_view}    IN    @{parent_domains}
        ${parts}=    Split String    ${domain_view}    |
        ${domain}=    Set Variable    ${parts[0]}
        ${view}=    Set Variable    ${parts[1]}

        ${zones}=    Get DNS Zones    fqdn=${domain}    view=${view}
        ${zone_count}=    Get Length    ${zones}
        Should Be True    ${zone_count} > 0    msg=DNS zone '${domain}' does not exist in view '${view}'
        Log    ✓ DNS zone exists: ${domain} in view ${view}    INFO
    END

Check For Duplicate A Records
    [Documentation]    Check if A records already exist in Infoblox (informational only)
    [Tags]    a_record    validation    duplicates
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    FOR    ${record}    IN    @{records}
        ${name}=    Set Variable    ${record['name']}
        ${view}=    Set Variable    ${record['view']}

        ${existing}=    Get A Records    name=${name}    view=${view}
        ${count}=    Get Length    ${existing}

        Run Keyword If    ${count} > 0    Log    ⚠️  Record '${name}' already exists in Infoblox with IP ${existing[0]['ipv4addr']}    WARN
        ...    ELSE    Log    ✓ Record '${name}' does not exist (new record)    INFO
    END

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
