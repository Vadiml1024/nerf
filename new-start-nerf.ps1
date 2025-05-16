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
    
    # On macOS, look for PowerShell/pwsh processes that might be running our commands
    $pwshProcesses = Get-Process -Name "pwsh" -ErrorAction SilentlyContinue
    if ($pwshProcesses) {
        Write-Host "Found PowerShell processes, checking if they're running our commands..." -ForegroundColor Yellow
        
        # On macOS, use ps to get more detailed command information
        $psOutput = & ps -ef | Select-String -Pattern "pwsh.*$CommandPattern"
        
        if ($psOutput) {
            Write-Host "Found matching PowerShell processes, terminating:" -ForegroundColor Yellow
            $processesFound = $true
            
            foreach ($line in $psOutput) {
                try {
                    $parts = $line -split '\s+'
                    # PID is typically the second field
                    $pid = $parts[1]
                    Write-Host "  - Terminating PowerShell process with PID: $pid" -ForegroundColor Gray
                    
                    # Try graceful termination first
                    kill $pid 2>/dev/null
                    Start-Sleep -Milliseconds 500
                    
                    # Check if still running, then force kill
                    $stillRunning = ps -p $pid -o pid= 2>/dev/null
                    if ($stillRunning) {
                        Write-Host "    - Process didn't terminate gracefully, force killing..." -ForegroundColor Yellow
                        kill -9 $pid 2>/dev/null
                    }
                } catch {
                    Write-Host "    - Error terminating process: $_" -ForegroundColor Red
                }
            }
        }
    }
    
    # Also check for regular processes running the command
    $otherProcesses = & ps -ef | Select-String -Pattern "$CommandPattern" | Select-String -NotMatch "pwsh.*$CommandPattern"
    
    if ($otherProcesses) {
        Write-Host "Found other processes running our commands:" -ForegroundColor Yellow
        $processesFound = $true
        
        foreach ($line in $otherProcesses) {
            try {
                $parts = $line -split '\s+'
                $pid = $parts[1]
                $cmd = ($line -split '(?<=\s+\d+\s+\d+\s+\d+:\d+:\d+\s+)')[1]
                Write-Host "  - Found PID $pid running: $cmd" -ForegroundColor Gray
                
                # Try graceful termination first
                kill $pid 2>/dev/null
                Start-Sleep -Milliseconds 500
                
                # Check if still running, then force kill
                $stillRunning = ps -p $pid -o pid= 2>/dev/null
                if ($stillRunning) {
                    Write-Host "    - Process didn't terminate gracefully, force killing..." -ForegroundColor Yellow
                    kill -9 $pid 2>/dev/null
                }
            } catch {
                Write-Host "    - Error terminating process: $_" -ForegroundColor Red
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
    
    # Define a unique type name with a GUID to avoid conflicts
    $typeName = "Win32_NerfControl_$(New-Guid)".Replace('-','_')
    
    # Load Windows API functions for window enumeration
    # First check if the type already exists
    if (-not ([System.Management.Automation.PSTypeName]$typeName).Type) {
        Add-Type -TypeDefinition @"
        using System;
        using System.Text;
        using System.Runtime.InteropServices;
        
        public class $typeName {
            [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
            public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
            [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
            [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
            [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
            [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
            [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
            
            // Wrapper method to handle the ref/out parameter issue
            public static uint GetProcessIdFromWindowHandle(IntPtr hWnd) {
                uint processId = 0;
                GetWindowThreadProcessId(hWnd, out processId);
                return processId;
            }
        }
"@
    }

    # Constants for window messages
    $WM_CLOSE = 0x0010
    
    Write-Host "Using Windows API to enumerate all visible windows..." -ForegroundColor Yellow
    
    # Collect all visible windows
    $matchingWindows = @()
    
    # Enumerate all windows and find any with titles containing our search string
    [Reflection.Assembly]::GetAssemblies() | Where-Object { $_.GetType($typeName) } | ForEach-Object {
        $Win32Type = $_.GetType($typeName)
        
        $enumWindowsMethod = $Win32Type.GetMethod('EnumWindows')
        $getWindowTextLengthMethod = $Win32Type.GetMethod('GetWindowTextLength')
        $getWindowTextMethod = $Win32Type.GetMethod('GetWindowText')
        $isWindowVisibleMethod = $Win32Type.GetMethod('IsWindowVisible')
        $getProcessIdFromWindowHandleMethod = $Win32Type.GetMethod('GetProcessIdFromWindowHandle')
        $postMessageMethod = $Win32Type.GetMethod('PostMessage')
        
        $enumWindowsDelegate = [System.Delegate]::CreateDelegate(
            $Win32Type.GetNestedType('EnumWindowsProc'),
            { 
                param($hWnd, $lParam)
                
                if ($isWindowVisibleMethod.Invoke($null, @($hWnd))) {
                    $length = $getWindowTextLengthMethod.Invoke($null, @($hWnd))
                    if ($length -gt 0) {
                        $builder = New-Object System.Text.StringBuilder $length
                        $getWindowTextMethod.Invoke($null, @($hWnd, $builder, $builder.Capacity + 1)) | Out-Null
                        
                        # Get process ID
                        $pid = $getProcessIdFromWindowHandleMethod.Invoke($null, @($hWnd))
                        
                        # Check if window title contains our search string
                        $windowTitle = $builder.ToString()
                        if ($windowTitle -like "*$WindowTitle*") {
                            $matchingWindows += [PSCustomObject]@{
                                Handle = $hWnd
                                ProcessId = $pid
                                WindowTitle = $windowTitle
                                PostMessage = $postMessageMethod
                            }
                        }
                    }
                }
                return $true
            }
        )
        
        $enumWindowsMethod.Invoke($null, @($enumWindowsDelegate, [IntPtr]::Zero))
    }
    
    # Fallback to a simpler method if reflection approach fails
    if ($matchingWindows.Count -eq 0) {
        Write-Host "Using simplified window detection..." -ForegroundColor Yellow
        
        # Try to find windows using Get-Process
        $processes = Get-Process | Where-Object { $_.MainWindowTitle -like "*$WindowTitle*" }
        foreach ($proc in $processes) {
            $matchingWindows += [PSCustomObject]@{
                Handle = $proc.MainWindowHandle
                ProcessId = $proc.Id
                WindowTitle = $proc.MainWindowTitle
            }
        }
    }
    
    # Process any matching windows
    if ($matchingWindows.Count -gt 0) {
        Write-Host "Found $($matchingWindows.Count) windows matching '$WindowTitle':" -ForegroundColor Yellow
        $processesFound = $true
        
        foreach ($window in $matchingWindows) {
            try {
                Write-Host "  - Closing window: '$($window.WindowTitle)' (PID: $($window.ProcessId))" -ForegroundColor Gray
                
                # Try to close the window using CloseMainWindow first
                $proc = Get-Process -Id $window.ProcessId -ErrorAction SilentlyContinue
                if ($proc) {
                    $proc.CloseMainWindow() | Out-Null
                    Start-Sleep -Seconds 1
                    
                    # Check if still running
                    $stillRunning = Get-Process -Id $window.ProcessId -ErrorAction SilentlyContinue
                    if ($stillRunning) {
                        Write-Host "    - Process still running, killing PID $($window.ProcessId)" -ForegroundColor Yellow
                        Stop-Process -Id $window.ProcessId -Force -ErrorAction SilentlyContinue
                    }
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
        $commandProcesses = Get-WmiObject Win32_Process -Filter $query
        
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