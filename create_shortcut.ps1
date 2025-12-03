# PowerShell script to create a Windows shortcut for BKDict app
$WScriptShell = New-Object -ComObject WScript.Shell

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define shortcut location on Desktop
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "BKDict.lnk"

# Create the shortcut
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)

# Set target to the batch file
$Shortcut.TargetPath = Join-Path $ScriptDir "start_bkdict.bat"

# Set working directory to the app folder
$Shortcut.WorkingDirectory = $ScriptDir

# Set icon
$IconPath = Join-Path $ScriptDir "static\windows_icon.ico"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
    Write-Host "Icon set to: $IconPath" -ForegroundColor Green
}
else {
    Write-Host "Warning: Icon file not found at $IconPath" -ForegroundColor Yellow
}

# Set description
$Shortcut.Description = "BKDict - Vocabulary Learning Application"

# Save the shortcut
$Shortcut.Save()

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Shortcut Created Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Shortcut location: $ShortcutPath" -ForegroundColor White
Write-Host ""
Write-Host "You can now double-click the BKDict shortcut on your desktop to launch the app!" -ForegroundColor White
Write-Host ""
