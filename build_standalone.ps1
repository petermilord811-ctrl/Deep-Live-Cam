# Builds the self-contained Deep-Live-Cam and stages models + ffmpeg beside the exe.
#
#   powershell -ExecutionPolicy Bypass -File build_standalone.ps1
#
# Result: dist\Deep-Live-Cam\  (Deep-Live-Cam.exe + _internal + models + ffmpeg)
# Copy that whole folder to any Windows PC with an NVIDIA GPU — no Python or
# pip install required.

$ErrorActionPreference = "Stop"
$py = "C:\Users\admin\AppData\Local\Programs\Python\Python310\python.exe"
$root = $PSScriptRoot
$dist = Join-Path $root "dist\Deep-Live-Cam"

Write-Host "==> Running PyInstaller..." -ForegroundColor Cyan
& $py -m PyInstaller (Join-Path $root "Deep-Live-Cam.spec") --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }
if (-not (Test-Path $dist)) { throw "Expected output folder not found: $dist" }

# --- Stage ONNX models (inswapper + gfpgan) beside the exe ---
$modelsSrc = Join-Path $root "models"
$modelsDst = Join-Path $dist "models"
New-Item -ItemType Directory -Force -Path $modelsDst | Out-Null
Write-Host "==> Copying ONNX models..." -ForegroundColor Cyan
Get-ChildItem $modelsSrc -Filter *.onnx | ForEach-Object {
    Copy-Item $_.FullName -Destination $modelsDst -Force
    Write-Host ("    {0} ({1:N0} MB)" -f $_.Name, ($_.Length / 1MB))
}

# --- Stage insightface buffalo_l models (so no ~/.insightface dependency) ---
$buffaloSrc = Join-Path $env:USERPROFILE ".insightface\models\buffalo_l"
$buffaloDst = Join-Path $modelsDst "buffalo_l"
if (Test-Path $buffaloSrc) {
    Write-Host "==> Copying insightface buffalo_l..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $buffaloDst | Out-Null
    Copy-Item (Join-Path $buffaloSrc "*.onnx") -Destination $buffaloDst -Force
} else {
    Write-Warning "buffalo_l not found at $buffaloSrc - the app will download it on first run."
}

# --- Stage ffmpeg + ffprobe (required by core.pre_check / video pipeline) ---
$ffmpegBin = "D:\1. Programs\utilities\ffmpeg-7.1.1-full_build\bin"
Write-Host "==> Copying ffmpeg..." -ForegroundColor Cyan
foreach ($exe in @("ffmpeg.exe", "ffprobe.exe")) {
    $srcExe = Join-Path $ffmpegBin $exe
    if (Test-Path $srcExe) {
        Copy-Item $srcExe -Destination $dist -Force
    } else {
        Write-Warning "$exe not found at $ffmpegBin - place it next to the exe manually."
    }
}

$sizeGB = (Get-ChildItem $dist -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
Write-Host ""
Write-Host ("==> DONE. dist\Deep-Live-Cam is {0:N1} GB" -f $sizeGB) -ForegroundColor Green
Write-Host "    Launch: dist\Deep-Live-Cam\Deep-Live-Cam.exe" -ForegroundColor Green
