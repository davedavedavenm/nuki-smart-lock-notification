@echo off
echo === Nuki Smart Lock Update Script ===
echo This script will prepare the fixes for dark mode and API errors
echo.

REM Create a timestamp for the backup
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YYYY=%dt:~0,4%"
set "MM=%dt:~4,2%"
set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%"
set "Min=%dt:~10,2%"
set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%%MM%%DD%_%HH%%Min%%Sec%"

REM Navigate to the project directory
set "PROJECT_DIR=%~dp0"
echo Working directory: %PROJECT_DIR%

REM Backup current configuration
echo Creating backup of current config...
set "BACKUP_DIR=%PROJECT_DIR%backup_%timestamp%"
mkdir "%BACKUP_DIR%" 2>nul
if exist "%PROJECT_DIR%\config" xcopy /E /I "%PROJECT_DIR%\config" "%BACKUP_DIR%\config" >nul
if exist "%PROJECT_DIR%\web" xcopy /E /I "%PROJECT_DIR%\web" "%BACKUP_DIR%\web" >nul
if exist "%PROJECT_DIR%\scripts" xcopy /E /I "%PROJECT_DIR%\scripts" "%BACKUP_DIR%\scripts" >nul
echo Backup created at: %BACKUP_DIR%

REM Git update
echo.
echo Do you want to push these changes to GitHub? (y/n)
set /p PUSH_TO_GIT=

if /i "%PUSH_TO_GIT%"=="y" (
    echo Pushing changes to GitHub...
    git add .
    git commit -m "Fix dark mode and API errors"
    git push
    echo Changes pushed to GitHub.
) else (
    echo GitHub push skipped.
)

echo.
echo === Update Preparation Complete ===
echo.
echo To deploy to your Raspberry Pi:
echo 1. Go to your Pi and run: git pull
echo 2. Then run: ./deploy-fix.sh
echo.
echo Backup of your previous configuration is at: %BACKUP_DIR%

pause
