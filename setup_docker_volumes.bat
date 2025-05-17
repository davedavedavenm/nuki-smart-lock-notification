@echo off
REM Docker Volume Setup Script for Windows
REM Sets up directories for Docker bind mounts on Windows
REM These directories will then be used by Docker containers

echo =========================================================
echo    Nuki Smart Lock Docker Volume Setup Script (Windows)
echo =========================================================
echo.

REM Create directories if they don't exist
echo Creating directories...
if not exist config mkdir config
if not exist logs mkdir logs
if not exist data mkdir data
echo [√] Directories created

echo.
echo [!] Important Notes for Windows Users:
echo     - Windows handles file permissions differently than Linux
echo     - The Docker containers run a Linux user (nuki) with UID 999
echo     - Make sure your Windows user account has full control over:
echo         * config folder
echo         * logs folder
echo         * data folder
echo.
echo [√] Setup complete!
echo.
echo You can now run the Docker containers with:
echo   docker compose up -d
echo.
echo If you encounter permission issues, see DOCKER_SETUP.md
echo for more information and advanced permission handling options.
echo.

pause
