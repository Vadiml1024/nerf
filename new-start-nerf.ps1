#!/usr/bin/env pwsh
# new-start-nerf.ps1 - PowerShell version of start_nerf.bat
Write-Host "Starting Nerf Gun Control System..." -ForegroundColor Cyan

#region OS Detection
# OS detection helper variables
$script:IsWindowsOS = $PSVersionTable.PSVersion.Major -ge 5 -and $IsWindows -ne $false
$script:IsMacOSOrLinux = $IsMacOS -eq $true -or $IsLinux -eq $true
#endregion

#region Docker Management Functions
function Test-DockerRunning {
    Write-Host "Checking Docker status..." -ForegroundColor Yellow
    $dockerRunning = $false
    try {
        docker info | Out-Null
        $dockerRunning = ($LASTEXITCODE -eq 0)
    } catch {
        $dockerRunning = $false
    }
    return $dockerRunning
}

function Start-DockerDesktop {
    Write-Host "Docker Desktop is not running. Starting Docker Desktop..." -ForegroundColor Yellow
    
    if ($script:IsMacOSOrLinux) {
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
            return $true
        } else {
            Write-Host "Warning: Docker Desktop may not have started properly." -ForegroundColor Red
            Write-Host "You may need to start it manually." -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "Error checking Docker status." -ForegroundColor Red
        return $false
    }
}
#endregion

#region Virtual Environment Functions
function Initialize-VirtualEnvironment {
    # PowerShell equivalent of activating virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    
    if ($script:IsMacOSOrLinux) {
        # macOS/Linux virtual environment
        if (Test-Path ".venv/bin/Activate.ps1") {
            . ./.venv/bin/Activate.ps1
            return $true
        } else {
            Write-Host "Virtual environment not found at expected location." -ForegroundColor Yellow
            return $false
        }
    } else {
        # Windows virtual environment
        if (Test-Path ".venv\Scripts\Activate.ps1") {
            . .\.venv\Scripts\Activate.ps1
            return $true
        } else {
            Write-Host "Virtual environment not found at expected location." -ForegroundColor Yellow
            return $false
        }
    }
}
#endregion

#region Process Management Functions
function Stop-ApplicationProcess {
    param (
        [string]$WindowTitle,
        [string]$CommandPattern
    )
    
    Write-Host "Checking for running $WindowTitle instances..." -ForegroundColor Yellow
    
    # Track if any processes were found
    $processesFound = $false
    
    if ($script:IsMacOSOrLinux) {
        $processesFound = Stop-MacOSProcesses -WindowTitle $WindowTitle -CommandPattern $CommandPattern
    } else {
        $processesFound = Stop-WindowsProcesses -WindowTitle $WindowTitle -CommandPattern $CommandPattern
    }
    
    if (-not $processesFound) {
        Write-Host "  - No processes found running $WindowTitle" -ForegroundColor Green
    }
}

function Stop-MacOSProcesses {
    param (
        [string]$WindowTitle,
        [string]$CommandPattern
    )
    
    $processesFound = $false
    
    # On macOS, we need to use a different approach since window titles aren't easily accessible
    Write-Host "Searching for processes matching '$CommandPattern' on macOS..." -ForegroundColor Yellow
    
    # Use ps with a wider grep search to catch both direct processes and those running in any shell
    $allMatchingProcesses = @()
    
    # Look for any process with our command pattern
    $psOutput = & ps -ef | grep -i "$CommandPattern" | grep -v grep
    
    if ($psOutput) {
        Write-Host "Found processes matching pattern:" -ForegroundColor Yellow
        $processesFound = $true
        
        # Parse each process
        foreach ($line in $psOutput) {
            try {
                # Extract PID (typically the 2nd field in ps output)
                $parts = $line -split '\s+'
                if ($parts.Count -ge 2) {
                    $pid = $parts[1]
                    
                    # Add to our collection
                    $allMatchingProcesses += [PSCustomObject]@{
                        PID = $pid
                        CommandLine = $line
                    }
                    
                    Write-Host "  - Found process PID $pid with command: $line" -ForegroundColor Gray
                }
            } catch {
                Write-Host "  - Error parsing process line: $_" -ForegroundColor Red
            }
        }
        
        # Now terminate each process
        foreach ($proc in $allMatchingProcesses) {
            try {
                Write-Host "  - Terminating process PID $($proc.PID)" -ForegroundColor Gray
                
                # Try graceful termination first (SIGTERM)
                & kill $proc.PID 2>/dev/null
                Start-Sleep -Milliseconds 500
                
                # Check if still running, then force kill (SIGKILL)
                $stillRunning = & ps -p $proc.PID -o pid= 2>/dev/null
                if ($stillRunning) {
                    Write-Host "    - Process didn't terminate gracefully, force killing..." -ForegroundColor Yellow
                    & kill -9 $proc.PID 2>/dev/null
                } else {
                    Write-Host "    - Process terminated gracefully" -ForegroundColor Green
                }
            } catch {
                Write-Host "    - Error terminating process: $_" -ForegroundColor Red
            }
        }
    }
    
    # Also specifically look for shell processes that might be hosting our commands
    # This catches PowerShell, bash, zsh, etc. that might be running our commands
    $shellPatterns = @("pwsh", "bash", "zsh", "sh", "terminal")
    
    foreach ($shellPattern in $shellPatterns) {
        # Find shell processes
        $shellProcesses = & ps -ef | grep -i $shellPattern | grep -v grep
        
        if ($shellProcesses) {
            foreach ($line in $shellProcesses) {
                # If the shell process command line contains our command pattern
                if ($line -like "*$CommandPattern*") {
                    $processesFound = $true
                    try {
                        $parts = $line -split '\s+'
                        if ($parts.Count -ge 2) {
                            $pid = $parts[1]
                            Write-Host "  - Found shell process ($shellPattern) with PID $pid running our command" -ForegroundColor Yellow
                            
                            # Try graceful termination first
                            & kill $pid 2>/dev/null
                            Start-Sleep -Milliseconds 500
                            
                            # Check if still running, then force kill
                            $stillRunning = & ps -p $pid -o pid= 2>/dev/null
                            if ($stillRunning) {
                                Write-Host "    - Process didn't terminate gracefully, force killing..." -ForegroundColor Yellow
                                & kill -9 $pid 2>/dev/null
                            } else {
                                Write-Host "    - Process terminated gracefully" -ForegroundColor Green
                            }
                        }
                    } catch {
                        Write-Host "    - Error handling shell process: $_" -ForegroundColor Red
                    }
                }
            }
        }
    }
    
    return $processesFound
}

function Stop-WindowsProcesses {
    param (
        [string]$WindowTitle,
        [string]$CommandPattern
    )
    
    $processesFound = $false
    
    Write-Host "Detecting windows with title containing '$WindowTitle'..." -ForegroundColor Yellow
    
    # Use a more direct approach with Get-Process which is more reliable
    # Find processes with matching window titles
    $windowProcesses = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowTitle*" -and $_.MainWindowHandle -ne 0 }
    
    if ($windowProcesses -and $windowProcesses.Count -gt 0) {
        Write-Host "Found $($windowProcesses.Count) windows matching '$WindowTitle':" -ForegroundColor Yellow
        $processesFound = $true
        
        foreach ($proc in $windowProcesses) {
            try {
                Write-Host "  - Closing window: '$($proc.MainWindowTitle)' (PID: $($proc.Id))" -ForegroundColor Gray
                
                # Try to gracefully close the window
                $proc.CloseMainWindow() | Out-Null
                Start-Sleep -Milliseconds 500
                
                # Check if process is still running and force terminate if necessary
                $stillRunning = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
                if ($stillRunning) {
                    Write-Host "    - Process still running, killing PID $($proc.Id)" -ForegroundColor Yellow
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                } else {
                    Write-Host "    - Process closed gracefully" -ForegroundColor Green
                }
            } catch {
                Write-Host "    - Error handling window: $_" -ForegroundColor Red
            }
        }
    }
    
    # Also search by command line to catch processes that might not have a matching window title
    try {
        Write-Host "Searching for processes with command line matching '$CommandPattern'..." -ForegroundColor Yellow
        
        # Use WMI to search by command line
        $query = "CommandLine like '%$CommandPattern%'"
        $commandProcesses = Get-WmiObject Win32_Process -Filter $query -ErrorAction SilentlyContinue
        
        if ($commandProcesses) {
            Write-Host "Found processes by command pattern:" -ForegroundColor Yellow
            $processesFound = $true
            
            foreach ($proc in $commandProcesses) {
                try {
                    Write-Host "  - Found process: $($proc.ProcessId), Command: $($proc.CommandLine)" -ForegroundColor Gray
                    
                    # Try to get associated process object
                    $processObj = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
                    if ($processObj) {
                        if ($processObj.MainWindowHandle -ne 0) {
                            # Try to gracefully close the window
                            Write-Host "    - Process has a main window, trying to close it gracefully" -ForegroundColor Gray
                            $processObj.CloseMainWindow() | Out-Null
                            Start-Sleep -Milliseconds 500
                        }
                        
                        # Check if still running
                        $stillRunning = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
                        if ($stillRunning) {
                            Write-Host "    - Process still running, terminating PID $($proc.ProcessId)" -ForegroundColor Yellow
                            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
                        }
                    } else {
                        # Process no longer exists or couldn't be accessed
                        Write-Host "    - Couldn't access process object, may have already terminated" -ForegroundColor Gray
                    }
                } catch {
                    Write-Host "    - Error handling process: $_" -ForegroundColor Red
                }
            }
        }
    } catch {
        Write-Host "Error querying processes by command line: $_" -ForegroundColor Red
    }
    
    # Also look for specific exe processes that might be running our applications
    try {
        $exeProcesses = Get-Process -Name "python", "streamlit", "cmd" -ErrorAction SilentlyContinue
        
        if ($exeProcesses) {
            # For each process, check its command line if we can access it
            foreach ($proc in $exeProcesses) {
                try {
                    # Try to get the command line from WMI
                    $wmiProc = Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue
                    
                    if ($wmiProc -and $wmiProc.CommandLine -like "*$CommandPattern*") {
                        Write-Host "  - Found $($proc.Name) process with matching command (PID: $($proc.Id))" -ForegroundColor Gray
                        $processesFound = $true
                        
                        # Try to close gracefully if it has a window
                        if ($proc.MainWindowHandle -ne 0) {
                            $proc.CloseMainWindow() | Out-Null
                            Start-Sleep -Milliseconds 500
                        }
                        
                        # Check if still running
                        $stillRunning = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
                        if ($stillRunning) {
                            Write-Host "    - Process still running, terminating PID $($proc.Id)" -ForegroundColor Yellow
                            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                        }
                    }
                } catch {
                    Write-Host "    - Error handling process: $_" -ForegroundColor Red
                }
            }
        }
    } catch {
        Write-Host "Error finding executable processes: $_" -ForegroundColor Red
    }
    
    return $processesFound
}

function Start-NerfApplications {
    Write-Host "Starting applications..." -ForegroundColor Green

    if ($script:IsMacOSOrLinux) {
        Start-MacOSApplications
    } else {
        Start-WindowsApplications
    }
    
    Write-Host "Applications started in separate windows." -ForegroundColor Green
}

function Start-MacOSApplications {
    # macOS way to start processes
    Start-Process -FilePath "streamlit" -ArgumentList "run nerf-admin\nerf-admin.py" -WindowStyle Normal
    Start-Process -FilePath "python" -ArgumentList "nerf-gun-control\main.py" -WindowStyle Normal
}

function Start-WindowsApplications {
    # Windows way with cmd.exe and titles
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k title nerf-gun-admin && streamlit run nerf-admin\nerf-admin.py"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k title nerf-gun-control && python nerf-gun-control\main.py"
}
#endregion

#region Main Script Execution

# Check if Docker Desktop is running
$dockerRunning = Test-DockerRunning
if (-not $dockerRunning) {
    $dockerStarted = Start-DockerDesktop
    if (-not $dockerStarted) {
        Write-Host "Warning: Docker may not be available. Applications may not function correctly." -ForegroundColor Red
    }
} else {
    Write-Host "Docker Desktop is already running." -ForegroundColor Green
}

# Activate the virtual environment
$envActivated = Initialize-VirtualEnvironment

# Stop any running instances of nerf-admin
Stop-ApplicationProcess -WindowTitle "nerf-gun-admin" -CommandPattern "streamlit run nerf-admin"

# Stop any running instances of nerf-gun-control
Stop-ApplicationProcess -WindowTitle "nerf-gun-control" -CommandPattern "python nerf-gun-control\\main.py"

# Start both applications with specific titles
Start-NerfApplications

#endregion