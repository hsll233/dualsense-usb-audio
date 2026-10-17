param(
    [string]$Python = 'python',
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string]$Version = '1.0.0'
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python -m unittest discover -s native_tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $Python -m PyInstaller --noconfirm --onefile --console --noupx --name DualSense-USB-Audio --collect-all pyaudiowpatch --collect-all _sounddevice_data usb-system-audio.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
$packageName = "DualSense-USB-Audio-v$Version-windows-x64"
$packagePath = Join-Path $PSScriptRoot "artifacts\$packageName"
New-Item -ItemType Directory -Path $packagePath -Force | Out-Null
Copy-Item -LiteralPath 'dist\DualSense-USB-Audio.exe', 'Start-USB-Native.cmd', 'README.md', 'LICENSE', 'CHANGELOG.md' -Destination $packagePath
& $Python collect_licenses.py (Join-Path $packagePath 'licenses')
if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
Copy-Item -LiteralPath 'licenses\PortAudio-LICENSE.txt', 'licenses\Apache-2.0.txt' -Destination (Join-Path $packagePath 'licenses')
$archivePath = "$packagePath.zip"
Compress-Archive -LiteralPath $packagePath -DestinationPath $archivePath -Force
$digest = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
"$digest  $packageName.zip" | Set-Content -LiteralPath "$archivePath.sha256" -Encoding ascii
Write-Output "Ready: $archivePath"
