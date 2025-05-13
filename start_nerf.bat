@echo off
echo Starting Nerf Gun Control System...

:: Check if Docker Desktop is running
echo Checking Docker status...
docker info > nul 2>&1
if %errorlevel% neq 0 (
    echo Docker Desktop is not running. Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    :: Wait for Docker to initialize
    echo Waiting for Docker to start...
    timeout /t 30 /nobreak
    
    :: Check again if Docker is now running
    docker info > nul 2>&1
    if %errorlevel% neq 0 (
        echo Warning: Docker Desktop may not have started properly.
        echo You may need to start it manually.
        pause
    ) else (
        echo Docker Desktop has started successfully.
    )
) else (
    echo Docker Desktop is already running.
)

:: Activate the virtual environment
call .venv\Scripts\activate.bat

:: Check if nerf-admin is already running and kill it if found
echo Checking for running nerf-admin instances...
tasklist /FI "WINDOWTITLE eq *nerf-admin*" 2>NUL | find "cmd.exe" >NUL
if %errorlevel% equ 0 (
    echo Killing previous nerf-admin instances...
    taskkill /FI "WINDOWTITLE eq *nerf-admin*" /F
)

:: Also check for any streamlit processes related to nerf-admin
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find "python.exe" >NUL
if %errorlevel% equ 0 (
    wmic process where "commandline like '%%streamlit run nerf-admin%%'" call terminate >NUL 2>NUL
    echo Previous nerf-admin streamlit instances terminated.
)

:: Check if nerf-gun-control is already running and kill it if found
echo Checking for running nerf-gun-control instances...
tasklist /FI "WINDOWTITLE eq *nerf-gun-control*" 2>NUL | find "cmd.exe" >NUL
if %errorlevel% equ 0 (
    echo Killing previous nerf-gun-control instances...
    taskkill /FI "WINDOWTITLE eq *nerf-gun-control*" /F
)

:: Also check for any python processes running nerf-gun-control
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find "python.exe" >NUL
if %errorlevel% equ 0 (
    wmic process where "commandline like '%%python nerf-gun-control\\main.py%%'" call terminate >NUL 2>NUL
    echo Previous nerf-gun-control instances terminated.
)

:: Start both applications
start cmd /k streamlit run nerf-admin\nerf-admin.py
start cmd /k python nerf-gun-control\main.py

echo Applications started in separate windows.
