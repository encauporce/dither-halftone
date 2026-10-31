<#
.SYNOPSIS
    One-Click ADB Deployment Script for Dither Halftone (抖动网点).
.DESCRIPTION
    Pushes halftone.glsl and mpv.conf directly to your connected Hisense A7 E-ink phone.
.EXAMPLE
    .\deploy.ps1
#>

[CmdletBinding()]
param (
    [string]$DeviceSerial = "",
    [string]$TargetShaderDir = "/sdcard/mpv/shaders",
    [string]$TargetConfigDir = "/sdcard/mpv"
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " 抖动网点 (Dither Halftone) - ADB 部署脚本 (PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check ADB Availability
$adbCmd = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adbCmd) {
    Write-Error "Error: 'adb' command not found in PATH! Please ensure Android SDK Platform-Tools are installed."
    exit 1
}

# 2. Check Device Connection
$rawDevices = & adb devices | Select-String -Pattern "\bdevice$"

if (-not $rawDevices) {
    Write-Warning "No authorized Android device detected via ADB!"
    Write-Warning "Please check:"
    Write-Warning "  1. USB Debugging is enabled on your Hisense A7."
    Write-Warning "  2. The phone screen is unlocked and ADB prompt is accepted."
    Write-Warning "  3. USB cable is securely connected (or wireless adb connect <IP>:5555 is active)."
    exit 1
}

$detected = ($rawDevices | Select-Object -First 1).ToString().Split("`t")[0].Trim()
$targetDevice = if ($DeviceSerial) { $DeviceSerial } else { $detected }
Write-Host "[+] Target Android Device: $targetDevice" -ForegroundColor Green

$scriptDir = $PSScriptRoot
$shaderPath = Join-Path $scriptDir "halftone.glsl"
$configPath = Join-Path $scriptDir "mpv.conf"

if (-not (Test-Path $shaderPath)) {
    Write-Error "Error: halftone.glsl not found at $shaderPath!"
    exit 1
}

# 3. Create Remote Directories
Write-Host "[*] Creating remote MPV shader directories on device..." -ForegroundColor Yellow
& adb -s $targetDevice shell "mkdir -p $TargetShaderDir"

# 4. Push halftone.glsl
Write-Host "[*] Pushing halftone.glsl to $TargetShaderDir/halftone.glsl ..." -ForegroundColor Yellow
& adb -s $targetDevice push "$shaderPath" "$TargetShaderDir/halftone.glsl"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to push halftone.glsl!"
    exit 1
}

# 5. Push mpv.conf if present
if (Test-Path $configPath) {
    Write-Host "[*] Pushing mpv.conf to $TargetConfigDir/mpv.conf ..." -ForegroundColor Yellow
    & adb -s $targetDevice push "$configPath" "$TargetConfigDir/mpv.conf"
}

# 6. Verify Installation
Write-Host "[*] Verifying remote files..." -ForegroundColor Yellow
$remoteLs = & adb -s $targetDevice shell "ls -l $TargetShaderDir/halftone.glsl"
Write-Host "    $remoteLs" -ForegroundColor Gray

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] 抖动网点 (Dither Halftone) Shader successfully deployed to your Hisense A7!" -ForegroundColor Green
Write-Host " How to run:" -ForegroundColor Green
Write-Host "   1. Launch 'mpv-android' on your phone." -ForegroundColor White
Write-Host "   2. Play any video (films, animations, gameplay)." -ForegroundColor White
Write-Host "   3. Enjoy high contrast deep ink, 15Hz anti-ghosting, and smooth DU4 gray!" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Green
