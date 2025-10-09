*** Settings ***
Documentation    Example Robot Framework test demonstrating ExecutionCounter integration
Library          ExecutionCounter
Library          Collections
Library          BuiltIn

*** Variables ***
${GRID_HOST}         %{GRID_HOST}
${RECORD_TYPE}       %{RECORD_TYPE}
${COUNTER_FILE}      %{COUNTER_FILE}
${PIPELINE_ID}       %{PIPELINE_ID=Unknown}

*** Test Cases ***
Initialize Counter and Display Stats
    [Documentation]    Initialize the execution counter and display current statistics
    [Tags]    setup    counter

    Log    ========================================
    Log    Starting Test Execution
    Log    Grid Host: ${GRID_HOST}
    Log    Record Type: ${RECORD_TYPE}
    Log    Pipeline ID: ${PIPELINE_ID}
    Log    Counter File: ${COUNTER_FILE}
    Log    ========================================

    # Initialize the execution counter
    Initialize Execution Counter    ${COUNTER_FILE}

    # Record this test execution
    ${count}=    Record Test Execution    Initialize Counter and Display Stats
    Log    This test has been executed ${count} times

    # Display all execution statistics
    Log Execution Statistics

Example Test With Execution Tracking
    [Documentation]    Example test that demonstrates execution tracking
    [Tags]    example    tracking

    # Record this test execution
    ${count}=    Record Test Execution    Example Test With Execution Tracking

    Log    Executing test for the ${count} time(s)

    # Your actual test logic goes here
    Should Be True    ${count} > 0    Test should have at least 1 execution

    Log    Test execution count verified: ${count}

Verify Counter Persistence
    [Documentation]    Verify that execution counts persist across pipeline runs
    [Tags]    verification    counter

    # Record this test execution
    ${count}=    Record Test Execution    Verify Counter Persistence

    Log    Current execution count: ${count}

    # Get individual test counts
    ${init_count}=    Get Test Execution Count    Initialize Counter and Display Stats
    ${example_count}=    Get Test Execution Count    Example Test With Execution Tracking

    Log    Initialize Counter test count: ${init_count}
    Log    Example Test count: ${example_count}

    # Verify counts are positive
    Should Be True    ${init_count} > 0    Initialize test should have run
    Should Be True    ${example_count} > 0    Example test should have run

    # Get total executions
    ${total}=    Get Total Test Executions
    Log    Total test executions across all tests: ${total}

    Should Be True    ${total} >= 3    Should have at least 3 total executions

Save Execution Data
    [Documentation]    Save the execution counter data to file
    [Tags]    teardown    counter

    # Record this test execution
    ${count}=    Record Test Execution    Save Execution Data

    Log    Saving execution counter data...

    # Save counter (automatically done by Record Test Execution, but can be called explicitly)
    Save Execution Counter

    # Display final statistics
    Log    ========================================
    Log    Final Execution Statistics
    Log    ========================================
    Log Execution Statistics

    Log    Execution data saved to: ${COUNTER_FILE}
    Log    Pipeline ID: ${PIPELINE_ID}
    Log    ========================================

*** Keywords ***
Log Section Header
    [Arguments]    ${section_name}
    Log    ${\n}========================================
    Log    ${section_name}
    Log    ========================================${\n}
