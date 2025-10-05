*** Settings ***
Documentation     CNAME Record validation tests - essential pre-deployment checks only
Library           ../../utils/robot/InfobloxAPI.py
Library           ../../utils/robot/ExecutionCounter.py
Library           Collections
Library           OperatingSystem
Suite Setup       Setup Execution Tracking
Suite Teardown    Teardown Execution Tracking

*** Variables ***
${GRID_HOST}              cabgridmgr.amfam.com
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/cname_record.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/pre_check/execution_counter.json

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

Validate CNAME Record DNS Zones Exist
    [Documentation]    Verify parent DNS zones exist in Infoblox
    [Tags]    cname_record    validation    dns_zone
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

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

Check For Duplicate CNAME Records
    [Documentation]    Check if CNAME records already exist in Infoblox (will cause deployment failure)
    [Tags]    cname_record    validation    duplicates
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${has_duplicates}=    Set Variable    ${False}

    FOR    ${record}    IN    @{records}
        ${name}=    Set Variable    ${record['name']}
        ${view}=    Set Variable    ${record['view']}

        ${existing}=    Get CNAME Records    name=${name}    view=${view}
        ${count}=    Get Length    ${existing}

        IF    ${count} > 0
            Log    ✗ ERROR: CNAME record '${name}' already exists in view '${view}'    ERROR
            Log    Existing canonical: ${existing[0]['canonical']}    ERROR
            Log    New canonical: ${record['canonical']}    ERROR
            ${has_duplicates}=    Set Variable    ${True}
        ELSE
            Log    ✓ Record '${name}' does not exist (new record)    INFO
        END
    END

    Should Not Be True    ${has_duplicates}    msg=Duplicate CNAME records found - deployment will fail

*** Keywords ***
Setup Execution Tracking
    [Documentation]    Initialize execution tracking for this test suite
    Initialize Execution Counter    ${COUNTER_FILE}
    Log    📊 Execution tracking initialized    INFO
    Record Test Execution    CNAME Record Validation Suite
    Log Execution Statistics

Teardown Execution Tracking
    [Documentation]    Save execution tracking data and display statistics
    Log Execution Statistics
    Save Execution Counter
    ${total}=    Get Total Test Executions
    Log    ✅ Total test suite executions: ${total}    INFO
