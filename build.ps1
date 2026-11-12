param([string]$Python='python', [string]$ISCC='C:\Program Files (x86)\Inno Setup 6\ISCC.exe', [string]$OutputDir="$PSScriptRoot\dist")
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Force $OutputDir | Out-Null
    & "$PSScriptRoot\prepare_office_engine.ps1"
    & $Python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & $Python collect_licenses.py
    & $Python design_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Design asset generation failed' }
    & $Python -c "from comtypes.client import GetModule; GetModule('UIAutomationCore.dll')"
    if ($LASTEXITCODE -ne 0) { throw 'Windows UI Automation wrapper generation failed' }
    $env:JINGPEEK_ONEFILE='0'
    & $Python -m PyInstaller --noconfirm --distpath "$PSScriptRoot\stage" --workpath "$PSScriptRoot\build-dir" release.spec
    if ($LASTEXITCODE -ne 0) { throw 'Installed edition build failed' }
    & $Python build_portable.py "$PSScriptRoot\stage\JingPeek" "$OutputDir\JingPeek-Portable-1.6.0-x64.exe" "$PSScriptRoot\build-portable"
    if ($LASTEXITCODE -ne 0) { throw 'Portable edition build failed' }
    & $ISCC "/DStageDir=$PSScriptRoot\stage\JingPeek" "/DOutputDirPath=$OutputDir" installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
} finally { Pop-Location }
