*** Settings ***
Documentation     CNAME Record post-deployment verification - verify records were created
Library           ../../utils/robot/InfobloxAPI.py
Library           ../../utils/robot/ExecutionCounter.py
Library           Collections
Library           OperatingSystem
Suite Setup       Setup Execution Tracking
Suite Teardown    Teardown Execution Tracking

*** Variables ***
${GRID_HOST}              cabgridmgr.amfam.com
${JSON_FILE}              ${CURDIR}/../../prod_changes/${GRID_HOST}/cname_record.json
${COUNTER_FILE}           ${CURDIR}/../../robot_reports/post_check/execution_counter.json

*** Test Cases ***
Verify CNAME Records Created In Infoblox
    [Documentation]    Verify all CNAME records were created successfully with correct canonical names
    [Tags]    cname_record    verification    creation
    Connect To Infoblox Grid    ${GRID_HOST}
    Test Infoblox Connection
    ${records}=    Load JSON Records    ${JSON_FILE}

    ${total}=    Get Length    ${records}
    ${verified}=    Set Variable    ${0}
    ${failed}=    Create List

    FOR    ${record}    IN    @{records}
        ${name}=    Set Variable    ${record['name']}
        ${view}=    Set Variable    ${record['view']}
        ${expected_canonical}=    Set Variable    ${record['canonical']}

        ${existing}=    Get CNAME Records    name=${name}    view=${view}
        ${count}=    Get Length    ${existing}

        IF    ${count} == 0
            Log    ✗ Record '${name}' was NOT found in Infoblox    ERROR
            Append To List    ${failed}    ${name}
        ELSE
            ${actual_canonical}=    Set Variable    ${existing[0]['canonical']}
            IF    '${actual_canonical}' == '${expected_canonical}'
                Log    ✓ Record '${name}' verified with canonical ${actual_canonical}    INFO
                ${verified}=    Evaluate    ${verified} + 1
            ELSE
                Log    ✗ Record '${name}' has wrong canonical: expected ${expected_canonical}, got ${actual_canonical}    ERROR
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
    Record Test Execution    CNAME Record Verification Suite
    Log Execution Statistics

Teardown Execution Tracking
    [Documentation]    Save execution tracking data and display statistics
    Log Execution Statistics
    Save Execution Counter
    ${total}=    Get Total Test Executions
    Log    ✅ Total test suite executions: ${total}    INFO
