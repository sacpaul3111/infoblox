@echo off
REM ====================================================================
REM Demo Pre-Check Test Runner
REM Shows what pre-check validation reports look like
REM ====================================================================

echo.
echo ========================================
echo   PRE-CHECK VALIDATION DEMO
echo ========================================
echo.

REM Create output directory
if not exist "demo_reports\pre_check" mkdir demo_reports\pre_check

echo [INFO] Running A Record Pre-Check Validation (Demo)...
echo.

REM Run A record validation with demo data
robot ^
    --variable GRID_HOST:demo.infoblox.local ^
    --variable JSON_FILE:%cd%\demo_test_data\cabgridmgr.amfam.com\a_record.json ^
    --outputdir demo_reports/pre_check ^
    --name "Pre-Check Validation Demo - A Records" ^
    --loglevel INFO ^
    --test "Validate A Record JSON File Exists" ^
    --test "Validate A Record Required Fields" ^
    tests/pre_check/a_record_validation.robot

echo.
echo ========================================
echo   PRE-CHECK DEMO COMPLETED
echo ========================================
echo.
echo Reports Generated:
echo   - HTML Report: demo_reports\pre_check\report.html
echo   - Log File:    demo_reports\pre_check\log.html
echo   - XML Output:  demo_reports\pre_check\output.xml
echo.
echo Opening HTML report...
start demo_reports\pre_check\report.html
echo.
pause
