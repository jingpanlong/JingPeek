param([string]$Destination="$PSScriptRoot\office_runtime",[string]$WorkDir="$PSScriptRoot\engine-build")
$ErrorActionPreference='Stop'
$version='26.8.2'
$expected='FF4B911403B67EE9E6249F820F9782C44BB32C94FDAA45B0DA53A8E419E5307A'
$url="https://download.documentfoundation.org/libreoffice/stable/$version/win/x86_64/LibreOffice_${version}_Win_x86-64.msi"
if(Test-Path -LiteralPath (Join-Path $Destination 'program\python.exe')) { Write-Output 'Bundled Office renderer already present'; return }
New-Item -ItemType Directory -Force $WorkDir,$Destination | Out-Null
$package=Join-Path $WorkDir 'LibreOffice.msi'
if(-not(Test-Path -LiteralPath $package)){Invoke-WebRequest -Uri $url -OutFile $package}
if((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $expected){throw 'Office renderer package hash mismatch'}
if((Get-AuthenticodeSignature -LiteralPath $package).Status -ne 'Valid'){throw 'Office renderer signature is not valid'}
$image=[IO.Path]::GetFullPath((Join-Path $WorkDir 'extracted'))
$p=Start-Process msiexec.exe -ArgumentList @('/a',('"'+[IO.Path]::GetFullPath($package)+'"'),'/qn',('TARGETDIR="'+$image+'"')) -WindowStyle Hidden -PassThru -Wait
if($p.ExitCode -ne 0){throw "Office renderer extraction failed: $($p.ExitCode)"}
foreach($name in @('program','share','presets','Fonts','readmes')){Copy-Item -LiteralPath (Join-Path $image $name) -Destination $Destination -Recurse -Force}
foreach($name in @('LICENSE.html','license.txt','NOTICE','CREDITS.fodt','update-settings.ini')){Copy-Item -LiteralPath (Join-Path $image $name) -Destination $Destination -Force}
Get-ChildItem (Join-Path $image 'System64') -Filter '*.dll' | ForEach-Object {if(-not(Test-Path -LiteralPath (Join-Path $Destination ('program\'+$_.Name)))){Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Destination 'program')}}
@{version=$version;sha256=$expected;url=$url;publisher='The Document Foundation'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination 'engine-manifest.json') -Encoding utf8
