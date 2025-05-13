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

:: Start both applications
start cmd /k streamlit run nerf-admin\nerf-admin.py
start cmd /k python nerf-gun-control\main.py

echo Applications started in separate windows.
