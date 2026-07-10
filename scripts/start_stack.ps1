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

.PARAMETER AppEnv
    Ambiente logico da API (ex.: local, production). Herda $env:APP_ENV se omitido.

.PARAMETER AdminBearerToken
    Token admin para /api/ops/fallbacks e rotas admin em production.
    Nunca e impresso pelo script. Herda $env:ADMIN_BEARER_TOKEN se omitido.

.PARAMETER CorsAllowedOrigins
    Origens CORS separadas por virgula. Herda $env:CORS_ALLOWED_ORIGINS se omitido.

.PARAMETER EnableAdminRoutes
    true | false. Em production o default e false.

.PARAMETER RateLimitEnabled
    true | false. Em production o default e true.

.PARAMETER RateLimitPerMinute
    Limite por IP/minuto nos prefixos /api/gold, /api/ict, /api/map, /api/ops.

.PARAMETER SkipApi
    Nao inicia a API.

.PARAMETER SkipDashboard
    Nao inicia o dashboard.

.EXAMPLE
    .\scripts\start_stack.ps1

.EXAMPLE
    .\scripts\start_stack.ps1 -GoldBackend postgis

.EXAMPLE
    .\scripts\start_stack.ps1 `
      -GoldBackend postgis `
      -AppEnv production `
      -AdminBearerToken local-production-test-token `
      -EnableAdminRoutes false `
      -RateLimitEnabled true `
      -RateLimitPerMinute 120

.EXAMPLE
    .\scripts\start_stack.ps1 -SkipDashboard

.NOTES
    Variaveis P0 sao injetadas explicitamente no processo uvicorn (nao dependem so de heranca).
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
    [string]$AppEnv = "",
    [string]$AdminBearerToken = "",
    [string]$CorsAllowedOrigins = "",
    [ValidateSet("true", "false", "")]
    [string]$EnableAdminRoutes = "",
    [ValidateSet("true", "false", "")]
    [string]$RateLimitEnabled = "",
    [int]$RateLimitPerMinute = 0,
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

function Escape-PSSingleQuoted {
    param([string]$Value)
    return ($Value -replace "'", "''")
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

function Resolve-StackSetting {
    param(
        [string]$ParamValue,
        [string]$EnvName,
        [string]$Default = ""
    )
    if ($ParamValue -and $ParamValue.Trim()) {
        return $ParamValue.Trim()
    }
    $fromEnv = [Environment]::GetEnvironmentVariable($EnvName)
    if ($fromEnv -and $fromEnv.Trim()) {
        return $fromEnv.Trim()
    }
    return $Default
}

function Resolve-StackAppEnv {
    param([string]$Explicit)
    $value = Resolve-StackSetting -ParamValue $Explicit -EnvName "APP_ENV" -Default "local"
    return $value.ToLower()
}

function Resolve-StackEnableAdminRoutes {
    param(
        [string]$Explicit,
        [string]$EffectiveAppEnv
    )
    if ($Explicit -in @("true", "false")) {
        return $Explicit
    }
    $fromEnv = Resolve-StackSetting -ParamValue "" -EnvName "ENABLE_ADMIN_ROUTES"
    if ($fromEnv -in @("true", "false", "1", "0", "yes", "no", "on", "off")) {
        return if ($fromEnv -in @("true", "1", "yes", "on")) { "true" } else { "false" }
    }
    if ($EffectiveAppEnv -in @("production", "prod")) {
        return "false"
    }
    return "true"
}

function Resolve-StackRateLimitEnabled {
    param(
        [string]$Explicit,
        [string]$EffectiveAppEnv
    )
    if ($Explicit -in @("true", "false")) {
        return $Explicit
    }
    $fromEnv = Resolve-StackSetting -ParamValue "" -EnvName "RATE_LIMIT_ENABLED"
    if ($fromEnv -in @("true", "false", "1", "0", "yes", "no", "on", "off")) {
        return if ($fromEnv -in @("true", "1", "yes", "on")) { "true" } else { "false" }
    }
    if ($EffectiveAppEnv -in @("production", "prod")) {
        return "true"
    }
    return "false"
}

function Resolve-StackRateLimitPerMinute {
    param(
        [int]$Explicit,
        [string]$EffectiveAppEnv
    )
    if ($Explicit -gt 0) {
        return $Explicit
    }
    $fromEnv = Resolve-StackSetting -ParamValue "" -EnvName "RATE_LIMIT_PER_MINUTE"
    if ($fromEnv -match '^\d+$' -and [int]$fromEnv -gt 0) {
        return [int]$fromEnv
    }
    if ($EffectiveAppEnv -in @("production", "prod")) {
        return 60
    }
    return 60
}

function Build-ApiEnvAssignment {
    param(
        [string]$Name,
        [string]$Value
    )
    if (-not $Value) {
        return $null
    }
    return "`$env:$Name='$((Escape-PSSingleQuoted -Value $Value))'"
}

function Build-ApiEnvLauncher {
    param(
        [string]$EffectiveGoldBackend,
        [string]$EffectiveAppEnv,
        [string]$EffectiveAdminToken,
        [string]$EffectiveCorsOrigins,
        [string]$EffectiveEnableAdminRoutes,
        [string]$EffectiveRateLimitEnabled,
        [int]$EffectiveRateLimitPerMinute
    )

    $assignments = @(
        (Build-ApiEnvAssignment -Name "GOLD_BACKEND" -Value $EffectiveGoldBackend)
        (Build-ApiEnvAssignment -Name "APP_ENV" -Value $EffectiveAppEnv)
        (Build-ApiEnvAssignment -Name "ENABLE_ADMIN_ROUTES" -Value $EffectiveEnableAdminRoutes)
        (Build-ApiEnvAssignment -Name "RATE_LIMIT_ENABLED" -Value $EffectiveRateLimitEnabled)
        (Build-ApiEnvAssignment -Name "RATE_LIMIT_PER_MINUTE" -Value ([string]$EffectiveRateLimitPerMinute))
    )

    if ($EffectiveAdminToken) {
        $assignments += (Build-ApiEnvAssignment -Name "ADMIN_BEARER_TOKEN" -Value $EffectiveAdminToken)
    }

    if ($EffectiveCorsOrigins) {
        $assignments += (Build-ApiEnvAssignment -Name "CORS_ALLOWED_ORIGINS" -Value $EffectiveCorsOrigins)
    }

    foreach ($passThroughName in @(
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "ENABLE_DEBUG_ROUTES",
        "APP_VERSION"
    )) {
        $passValue = [Environment]::GetEnvironmentVariable($passThroughName)
        if ($passValue -and $passValue.Trim()) {
            $assignments += (Build-ApiEnvAssignment -Name $passThroughName -Value $passValue.Trim())
        }
    }

    return ($assignments | Where-Object { $_ }) -join "; "
}

$EffectiveGoldBackend = Resolve-StackGoldBackend -Explicit $GoldBackend
$EffectiveAppEnv = Resolve-StackAppEnv -Explicit $AppEnv
$EffectiveAdminToken = Resolve-StackSetting -ParamValue $AdminBearerToken -EnvName "ADMIN_BEARER_TOKEN"
$EffectiveCorsOrigins = Resolve-StackSetting -ParamValue $CorsAllowedOrigins -EnvName "CORS_ALLOWED_ORIGINS"
$EffectiveEnableAdminRoutes = Resolve-StackEnableAdminRoutes -Explicit $EnableAdminRoutes -EffectiveAppEnv $EffectiveAppEnv
$EffectiveRateLimitEnabled = Resolve-StackRateLimitEnabled -Explicit $RateLimitEnabled -EffectiveAppEnv $EffectiveAppEnv
$EffectiveRateLimitPerMinute = Resolve-StackRateLimitPerMinute -Explicit $RateLimitPerMinute -EffectiveAppEnv $EffectiveAppEnv

$AdminTokenStatus = if ($EffectiveAdminToken) { "set" } else { "missing" }

if ($EffectiveAppEnv -in @("production", "prod")) {
    if (-not $EffectiveAdminToken -or $EffectiveAdminToken.Trim().Length -lt 16) {
        throw @"
APP_ENV=production exige ADMIN_BEARER_TOKEN forte (minimo 16 caracteres).
Use -AdminBearerToken <token> ou defina `$env:ADMIN_BEARER_TOKEN antes de executar o script.
"@
    }
}

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
    $EnvLauncher = Build-ApiEnvLauncher `
        -EffectiveGoldBackend $EffectiveGoldBackend `
        -EffectiveAppEnv $EffectiveAppEnv `
        -EffectiveAdminToken $EffectiveAdminToken `
        -EffectiveCorsOrigins $EffectiveCorsOrigins `
        -EffectiveEnableAdminRoutes $EffectiveEnableAdminRoutes `
        -EffectiveRateLimitEnabled $EffectiveRateLimitEnabled `
        -EffectiveRateLimitPerMinute $EffectiveRateLimitPerMinute

    Write-Host "Starting API with configuracao efetiva:" -ForegroundColor Cyan
    Write-Host "  APP_ENV=$EffectiveAppEnv"
    Write-Host "  GOLD_BACKEND=$EffectiveGoldBackend"
    Write-Host "  ENABLE_ADMIN_ROUTES=$EffectiveEnableAdminRoutes"
    Write-Host "  RATE_LIMIT_ENABLED=$EffectiveRateLimitEnabled"
    Write-Host "  RATE_LIMIT_PER_MINUTE=$EffectiveRateLimitPerMinute"
    Write-Host "  ADMIN_BEARER_TOKEN=$AdminTokenStatus"

    if (Test-Path $VenvPython) {
        $ApiLauncher = "$EnvLauncher; & '$VenvPython' -m uvicorn app.main:app --reload --host $ApiHost --port $ApiPort"
    }
    else {
        $ApiLauncher = "$EnvLauncher; python -m uvicorn app.main:app --reload --host $ApiHost --port $ApiPort"
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
    Write-Host "APP_ENV=$EffectiveAppEnv | GOLD_BACKEND=$EffectiveGoldBackend"
    if ($EffectiveAppEnv -in @("production", "prod")) {
        Write-Host "Smoke: python scripts/smoke_platform.py --expect-gold-backend $EffectiveGoldBackend --admin-bearer-token <token> --skip-front"
    }
    else {
        Write-Host "Smoke: python scripts/smoke_platform.py --expect-gold-backend $EffectiveGoldBackend --skip-front"
    }
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
