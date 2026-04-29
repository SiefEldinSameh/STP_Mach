<#
  STP_Mach - start backend (FastAPI) and frontend (Vite) for local development.

  Model weights: backend\ckpts\td, backend\ckpts\tsr, backend\ckpts\ocr (see README).

  Prereqs: pip install -r backend\requirements.txt, npm install in frontend.
#>
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Test-Ckpts {
    $td = Join-Path $Backend "ckpts\td\model.safetensors"
    $tsr = Join-Path $Backend "ckpts\tsr\model.safetensors"
    $ocr = Join-Path $Backend "ckpts\ocr"
    $ocrOk = (Test-Path $ocr) -and ((Get-ChildItem -Path $ocr -File -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)
    if (-not (Test-Path $td)) { Write-Warning "Missing: backend\ckpts\td\model.safetensors - table detection will fail at load." }
    if (-not (Test-Path $tsr)) { Write-Warning "Missing: backend\ckpts\tsr\model.safetensors - structure recognition will fail at load." }
    if (-not $ocrOk) { Write-Warning "Missing or empty: backend\ckpts\ocr\ - TrOCR will fail at load." }
}

Test-Ckpts

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { Write-Error "Python not found on PATH. Install Python or activate your venv first." }

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) { Write-Error "npm not found on PATH." }

$viteMod = Join-Path $Frontend "node_modules\vite"
if (-not (Test-Path $viteMod)) {
    Write-Error "Frontend deps not installed (missing node_modules\vite). Run: cd frontend; npm install"
}
$ShellExe = if ($Pwsh) { $Pwsh.Source } else {
    Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
}
$PyExe = $py.Source

Write-Host "Starting backend at http://127.0.0.1:8000 and frontend at http://localhost:5173 (new windows)" -ForegroundColor Cyan

# Use -WorkingDirectory so paths with spaces/special chars do not break -Command parsing
$backendCmd = "& `"$PyExe`" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process -FilePath $ShellExe -WorkingDirectory $Backend -ArgumentList "-NoExit", "-NoProfile", "-Command", $backendCmd

$frontendCmd = "npm run dev"
Start-Process -FilePath $ShellExe -WorkingDirectory $Frontend -ArgumentList "-NoExit", "-NoProfile", "-Command", $frontendCmd
