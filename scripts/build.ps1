param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python -m pip install -q -r requirements.txt pyinstaller
python scripts\make_icon.py
python -m PyInstaller --noconfirm msfs-resume.spec

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $SkipInstaller -and $iscc) {
    & $iscc "installer\msfs-resume.iss"
    Write-Host "Installer: dist\MSFSResumeSetup-0.4.3.exe"
} else {
    Write-Host "PyInstaller folder: dist\MSFSResume\"
    if (-not $iscc) {
        Write-Host "Inno Setup 6 not found. Zip dist\MSFSResume or install Inno Setup to build MSFSResumeSetup."
    }
}
