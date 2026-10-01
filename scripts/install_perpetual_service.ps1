# scripts/install_perpetual_service.ps1
# Configures Windows Scheduled Task and User Startup to ensure TalentOps runs 24/7/365

$ErrorActionPreference = "SilentlyContinue"
$pythonwPath = (Get-Command pythonw.exe).Source
if (-not $pythonwPath) {
    $pythonPath = (Get-Command python.exe).Source
    $pythonwPath = $pythonPath.Replace("python.exe", "pythonw.exe")
}

$supervisorScript = "c:\TalentOpsAI\backend\talentops_supervisor.py"
$vbsPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\TalentOpsPerpetualSupervisor.vbs"

Write-Host "Configuring TalentOps Perpetual Background Supervisor..."
Write-Host "Pythonw Executable: $pythonwPath"
Write-Host "Supervisor Script:  $supervisorScript"

# 1. Dual Fail-Safe: User Startup Folder VBScript (Zero Console Window, Runs at Logon)
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & "$pythonwPath" & Chr(34) & " " & Chr(34) & "$supervisorScript" & Chr(34), 0, False
Set WshShell = Nothing
"@

[System.IO.File]::WriteAllText($vbsPath, $vbsContent)
Write-Host "[OK] Startup folder persistence registered at: $vbsPath"

# 2. Windows Task Scheduler Registration (Runs at Logon & System Startup)
$taskName = "TalentOpsPerpetualSupervisor"
$action = New-ScheduledTaskAction -Execute $pythonwPath -Argument "`"$supervisorScript`"" -WorkingDirectory "c:\TalentOpsAI"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false 2>$null
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "TalentOps AI 24/7 Perpetual Autonomous Discovery Supervisor" 2>$null

Write-Host "[OK] Windows Scheduled Task registered: $taskName"
Write-Host "TalentOps Perpetual Service configured successfully."
