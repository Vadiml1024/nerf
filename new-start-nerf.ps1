#!/usr/bin/env pwsh
# new-start-nerf.ps1 - PowerShell version of start_nerf.bat
Write-Host "Starting Nerf Gun Control System..." -ForegroundColor Cyan

# Check if Docker Desktop is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
$dockerRunning = $false
try {
    docker info | Out-Null
    $dockerRunning = ($LASTEXITCODE -eq 0)
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host "Docker Desktop is not running. Starting Docker Desktop..." -ForegroundColor Yellow
    
    # Start Docker Desktop - path may need to be adjusted for macOS
    if ($IsMacOS) {
        # macOS path for Docker
        Start-Process "/Applications/Docker.app"
    } else {
        # Windows path for Docker
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    }
    
    # Wait for Docker to initialize
    Write-Host "Waiting for Docker to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    # Check again if Docker is now running
    try {
        docker info | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Docker Desktop has started successfully." -ForegroundColor Green
        } else {
            Write-Host "Warning: Docker Desktop may not have started properly." -ForegroundColor Red
            Write-Host "You may need to start it manually." -ForegroundColor Red
            Pause
        }
    } catch {
        Write-Host "Error checking Docker status." -ForegroundColor Red
    }
} else {
    Write-Host "Docker Desktop is already running." -ForegroundColor Green
}

# Activate the virtual environment
# PowerShell equivalent of activating virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
if ($IsMacOS -or $IsLinux) {
    # macOS/Linux virtual environment
    if (Test-Path ".venv/bin/Activate.ps1") {
        . ./.venv/bin/Activate.ps1
    } else {
        Write-Host "Virtual environment not found at expected location." -ForegroundColor Yellow
    }
} else {
    # Windows virtual environment
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        . .\.venv\Scripts\Activate.ps1
    } else {
        Write-Host "Virtual environment not found at expected location." -ForegroundColor Yellow
    }
}

# Function to check and kill processes
function Stop-ApplicationProcess {
    param (
        [string]$WindowTitle,
        [string]$CommandPattern
    )
    
    Write-Host "Checking for running $WindowTitle instances..." -ForegroundColor Yellow
    
    # Check for processes with specific window title
    if (-not $IsMacOS) {
        # Windows way to check for window titles
        $processesByTitle = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowTitle*" }
        if ($processesByTitle) {
            Write-Host "Closing windows and killing previous $WindowTitle instances by window title..." -ForegroundColor Yellow
            foreach ($process in $processesByTitle) {
                try {
                    # Try to gracefully close the window first
                    $process.CloseMainWindow() | Out-Null
                    # Give it a moment to close
                    Start-Sleep -Milliseconds 500
                    # If still running, force kill
                    if (!$process.HasExited) {
                        $process | Stop-Process -Force
                    }
                    Write-Host "  - Closed process with ID: $($process.Id)" -ForegroundColor Gray
                } catch {
                    Write-Host "  - Failed to close process with ID: $($process.Id). Forcing termination." -ForegroundColor Red
                    $process | Stop-Process -Force -ErrorAction SilentlyContinue
                }
            }
        } else {
            Write-Host "  - No processes found with window title containing '$WindowTitle'" -ForegroundColor Gray
        }
    }
    
    # Check processes by command line (works on both Windows and macOS)
    if ($IsMacOS -or $IsLinux) {
        # macOS/Linux way
        Write-Host "Checking for $WindowTitle processes by command pattern on macOS/Linux..." -ForegroundColor Yellow
        $processes = ps -ef | Select-String -Pattern $CommandPattern
        
        if ($processes) {
            Write-Host "Found matching processes, terminating:" -ForegroundColor Yellow
            foreach ($procLine in $processes) {
                try {
                    $procParts = $procLine -split '\s+'
                    $pid = $procParts[1]
                    Write-Host "  - Terminating process with PID: $pid" -ForegroundColor Gray
                    # On macOS, try graceful termination first (SIGTERM)
                    $null = kill $pid 2>/dev/null
                    Start-Sleep -Milliseconds 500
                    # Check if still running, then force kill (SIGKILL)
                    $stillRunning = ps -p $pid -o pid= 2>/dev/null
                    if ($stillRunning) {
                        $null = kill -9 $pid 2>/dev/null
                        Write-Host "    - Process didn't terminate gracefully, force killed" -ForegroundColor Gray
                    }
                } catch {
                    Write-Host "    - Error terminating process: $_" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "  - No processes found matching pattern '$CommandPattern'" -ForegroundColor Gray
        }
    } else {
        # Windows way using WMI
        $query = "CommandLine like '%$CommandPattern%'"
        try {
            $processes = Get-WmiObject Win32_Process -Filter $query
            if ($processes) {
                Write-Host "Found processes by command pattern on Windows, terminating:" -ForegroundColor Yellow
                foreach ($proc in $processes) {
                    try {
                        # Try to get a Process object to close its window
                        $processObj = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
                        if ($processObj -and $processObj.MainWindowHandle -ne 0) {
                            Write-Host "  - Closing window for process $($proc.ProcessId)" -ForegroundColor Gray
                            $processObj.CloseMainWindow() | Out-Null
                            Start-Sleep -Milliseconds 500
                        }
                        
                        # Check if still running
                        $stillRunning = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
                        if ($stillRunning) {
                            Write-Host "  - Terminating process $($proc.ProcessId)" -ForegroundColor Gray
                            Stop-Process -Id $proc.ProcessId -Force
                        }
                    } catch {
                        Write-Host "  - Error handling process $($proc.ProcessId): $_" -ForegroundColor Red
                    }
                }
            } else {
                Write-Host "  - No processes found matching pattern '$CommandPattern'" -ForegroundColor Gray
            }
        } catch {
            Write-Host "Error querying processes: $_" -ForegroundColor Red
        }
    }
}

# Stop any running instances of nerf-admin
Stop-ApplicationProcess -WindowTitle "nerf-gun-admin" -CommandPattern "streamlit run nerf-admin"

# Stop any running instances of nerf-gun-control
Stop-ApplicationProcess -WindowTitle "nerf-gun-control" -CommandPattern "python nerf-gun-control\\main.py"

# Start both applications with specific titles
Write-Host "Starting applications..." -ForegroundColor Green

if ($IsMacOS -or $IsLinux) {
    # macOS/Linux way to start processes
    Start-Process -FilePath "streamlit" -ArgumentList "run nerf-admin\nerf-admin.py" -WindowStyle Normal
    Start-Process -FilePath "python" -ArgumentList "nerf-gun-control\main.py" -WindowStyle Normal
} else {
    # Windows way with cmd.exe and titles
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k title nerf-gun-admin && streamlit run nerf-admin\nerf-admin.py"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k title nerf-gun-control && python nerf-gun-control\main.py"
}

Write-Host "Applications started in separate windows." -ForegroundColor Green