#Requires -Version 5.1
<#
.SYNOPSIS
    Inicia API e dashboard localmente para demonstracao institucional.

.DESCRIPTION
    Abre a API (uvicorn) e o dashboard (Vite) em janelas PowerShell separadas.
    Nao instala dependencias nem executa o pipeline.

.PARAMETER ApiHost
    Host da API. Padrao: 127.0.0.1

.PARAMETER ApiPort
    Porta da API. Padrao: 8000

.PARAMETER DashboardPort
    Porta do Vite. Se omitida ou 0, usa o padrao do projeto (5173).

.PARAMETER GoldBackend
    Backend Gold da API: filesystem | postgis.
    Se omitido, le GOLD_BACKEND do arquivo .env; se ausente, usa filesystem.

.PARAMETER SkipApi
    Nao inicia a API.

.PARAMETER SkipDashboard
    Nao inicia o dashboard.

.EXAMPLE
    .\scripts\start_stack.ps1

.EXAMPLE
    .\scripts\start_stack.ps1 -GoldBackend postgis

.EXAMPLE
    .\scripts\start_stack.ps1 -ApiPort 8080 -DashboardPort 5174 -GoldBackend filesystem

.EXAMPLE
    .\scripts\start_stack.ps1 -SkipDashboard

.NOTES
    GOLD_BACKEND precisa estar no processo que inicia a API (esta janela/processo).
    Nao adianta setar GOLD_BACKEND apenas no terminal do smoke.
    Para encerrar: feche cada janela PowerShell aberta ou pressione Ctrl+C nelas.
    O dashboard usa proxy /api -> API local (ver dashboard/vite.config.ts).
#>
[CmdletBinding()]
param(
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [int]$DashboardPort = 0,
    [ValidateSet("filesystem", "postgis")]
    [string]$GoldBackend = "",
    [switch]$SkipApi,
    [switch]$SkipDashboard
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$NodeModules = Join-Path $ProjectRoot "dashboard\node_modules"
$EnvFilePath = Join-Path $ProjectRoot ".env"

function Write-DependencyWarning {
    param([string]$Message)
    Write-Warning $Message
}

function Get-GoldBackendFromEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ($trimmed -eq "" -or $trimmed.StartsWith("#")) {
            continue
        }
        if ($trimmed -match '^\s*GOLD_BACKEND\s*=\s*(.+)\s*$') {
            return $Matches[1].Trim().Trim('"').Trim("'").ToLower()
        }
    }
    return $null
}

function Resolve-StackGoldBackend {
    param([string]$Explicit)
    if ($Explicit -and $Explicit.Trim()) {
        return $Explicit.Trim().ToLower()
    }
    $fromFile = Get-GoldBackendFromEnvFile -Path $EnvFilePath
    if ($fromFile) {
        if ($fromFile -notin @("filesystem", "postgis")) {
            throw "GOLD_BACKEND invalido no .env: '$fromFile'. Valores aceitos: filesystem | postgis"
        }
        return $fromFile
    }
    return "filesystem"
}

$EffectiveGoldBackend = Resolve-StackGoldBackend -Explicit $GoldBackend

$HasProblems = $false

if (-not (Test-Path $VenvDir)) {
    Write-DependencyWarning "Ambiente virtual (.venv) nao encontrado."
    Write-DependencyWarning "Crie com: python -m venv .venv"
    Write-DependencyWarning "Depois: .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    $HasProblems = $true
}

if (-not $SkipDashboard -and -not (Test-Path $NodeModules)) {
    Write-DependencyWarning "dashboard/node_modules nao encontrado."
    Write-DependencyWarning "Execute: cd dashboard; npm install"
    $HasProblems = $true
}

if ($HasProblems) {
    Write-Host ""
    Write-Host "Corrija as dependencias acima antes de usar o sistema em producao ou demonstracao." -ForegroundColor Yellow
    Write-Host "O script ainda tentara iniciar os componentes solicitados." -ForegroundColor Yellow
    Write-Host ""
}

if (-not $SkipApi) {
    Write-Host "Starting API with GOLD_BACKEND=$EffectiveGoldBackend" -ForegroundColor Cyan

    if (Test-Path $VenvPython) {
        $ApiLauncher = "`$env:GOLD_BACKEND='$EffectiveGoldBackend'; & '$VenvPython' -m uvicorn app.main:app --reload --host $ApiHost --port $ApiPort"
    }
    else {
        $ApiLauncher = "`$env:GOLD_BACKEND='$EffectiveGoldBackend'; python -m uvicorn app.main:app --reload --host $ApiHost --port $ApiPort"
    }

    $ApiCommand = "Set-Location -LiteralPath '$ProjectRoot'; $ApiLauncher"

    Write-Host "Iniciando API em nova janela..." -ForegroundColor Cyan
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-Command",
        $ApiCommand
    ) | Out-Null
}

if (-not $SkipDashboard) {
    $DashboardLauncher = "Set-Location -LiteralPath '$ProjectRoot\dashboard'; npm run dev"
    if ($DashboardPort -gt 0) {
        $DashboardLauncher += " -- --port $DashboardPort"
    }

    Write-Host "Iniciando dashboard em nova janela..." -ForegroundColor Cyan
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-Command",
        $DashboardLauncher
    ) | Out-Null
}

$EffectiveDashboardPort = if ($DashboardPort -gt 0) { $DashboardPort } else { 5173 }

Write-Host ""
Write-Host "=== CAGED Dashboard - stack local ===" -ForegroundColor Green
Write-Host ""

if (-not $SkipApi) {
    Write-Host "API:       http://${ApiHost}:$ApiPort"
    Write-Host "Docs:      http://${ApiHost}:$ApiPort/docs"
    Write-Host "Health:    http://${ApiHost}:$ApiPort/health"
    Write-Host "Ready:     http://${ApiHost}:$ApiPort/ready"
    Write-Host "GOLD_BACKEND=$EffectiveGoldBackend (processo da API)"
}

if (-not $SkipDashboard) {
    Write-Host "Dashboard: http://localhost:$EffectiveDashboardPort/"
    if ($DashboardPort -le 0) {
        Write-Host "           (Se 5173 estiver ocupada, o Vite pode usar outra porta - confira a janela do dashboard.)"
    }
}

Write-Host ""
Write-Host "Como encerrar:" -ForegroundColor Yellow
Write-Host "  - Feche as janelas PowerShell abertas para API e/ou dashboard"
Write-Host "  - Ou pressione Ctrl+C em cada janela"
Write-Host ""
Write-Host "Dica: confira GET /ready e o log de startup da API (gold_backend=...)."
Write-Host "Smoke: python scripts/smoke_platform.py --expect-gold-backend $EffectiveGoldBackend --skip-front"
