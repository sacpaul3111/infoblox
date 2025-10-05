@echo off
REM ====================================================================
REM Demo Post-Check Test Runner
REM Shows what post-check verification reports look like
REM Note: This will fail without actual Infoblox connection
REM ====================================================================

echo.
echo ========================================
echo   POST-CHECK VERIFICATION DEMO
echo ========================================
echo.
echo NOTE: This demo requires Infoblox connection
echo It will show you what the test tries to verify
echo.

REM Create output directory
if not exist "demo_reports\post_check" mkdir demo_reports\post_check

echo [INFO] Running A Record Post-Check Verification (Demo)...
echo.

REM Run A record verification with demo data
robot ^
    --variable GRID_HOST:demo.infoblox.local ^
    --variable JSON_FILE:%cd%\demo_test_data\cabgridmgr.amfam.com\a_record.json ^
    --outputdir demo_reports/post_check ^
    --name "Post-Check Verification Demo - A Records" ^
    --loglevel INFO ^
    tests/post_check/a_record_verification.robot

echo.
echo ========================================
echo   POST-CHECK DEMO COMPLETED
echo ========================================
echo.
echo Reports Generated:
echo   - HTML Report: demo_reports\post_check\report.html
echo   - Log File:    demo_reports\post_check\log.html
echo   - XML Output:  demo_reports\post_check\output.xml
echo.
echo Opening HTML report...
start demo_reports\post_check\report.html
echo.
pause
