@echo off
echo Starting Nerf Gun Control System...

:: Activate the virtual environment
call .venv\Scripts\activate.bat

:: Start both applications
start cmd /k python nerf-admin\nerf-admin.py
start cmd /k python nerf-gun-control\main.py

echo Applications started in separate windows. 
