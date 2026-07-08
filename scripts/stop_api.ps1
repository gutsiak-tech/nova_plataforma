#Requires -Version 5.1
<#
.SYNOPSIS
    Encerra com seguranca processos locais da API (uvicorn) nas portas configuradas.

.DESCRIPTION
    Lista processos Python/Uvicorn escutando nas portas 8000, 8002 e 8006.
    Solicita confirmacao antes de encerrar qualquer processo.
    Nao encerra processos fora dessas portas nem processos que nao sejam uvicorn/Python da API.

    Use apos homologacao ou demonstracao para evitar conflitos de porta ao trocar
    GOLD_BACKEND (filesystem <-> postgis) com start_stack.ps1.

.PARAMETER Ports
    Portas a inspecionar. Padrao: 8000, 8002, 8006.

.PARAMETER Force
    Encerra os processos sem pedir confirmacao interativa.

.EXAMPLE
    .\scripts\stop_api.ps1

    Lista processos nas portas padrao e pede confirmacao (S/N) antes de encerrar.

.EXAMPLE
    .\scripts\stop_api.ps1 -Force

    Encerra imediatamente os processos uvicorn encontrados nas portas padrao.

.NOTES
    Complementa scripts/start_stack.ps1.
    Se a API foi iniciada em outra porta, use -Ports para inclui-la explicitamente.
    Processos em janelas PowerShell abertas por start_stack.ps1 tambem podem ser
    encerrados com Ctrl+C na janela correspondente.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [int[]]$Ports = @(8000, 8002, 8006),
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Test-UvicornApiProcess {
    param(
        [int]$ProcessId,
        [string]$CommandLine
    )

    if (-not $CommandLine) {
        return $false
    }

    $normalized = $CommandLine.ToLowerInvariant()
    $isPython = $normalized -match 'python'
    $isUvicorn = $normalized -match 'uvicorn'
    $isAppMain = $normalized -match 'app\.main:app'

    return ($isPython -and $isUvicorn -and $isAppMain)
}

function Get-ApiListenerTargets {
    param([int[]]$TargetPorts)

    $targets = @{}
    $uniquePorts = $TargetPorts | Sort-Object -Unique

    foreach ($port in $uniquePorts) {
        $connections = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
        foreach ($connection in $connections) {
            $processId = [int]$connection.OwningProcess
            if ($processId -le 0) {
                continue
            }

            $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
            if (-not $process) {
                Write-Warning "Porta $port : PID $processId escutando, mas processo nao encontrado (pode ser fantasma). Ignorado."
                continue
            }

            $commandLine = [string]$process.CommandLine
            if (-not (Test-UvicornApiProcess -ProcessId $processId -CommandLine $commandLine)) {
                Write-Warning "Porta $port : PID $processId nao e uvicorn app.main:app. Ignorado por seguranca."
                Write-Warning "  CommandLine: $commandLine"
                continue
            }

            if (-not $targets.ContainsKey($processId)) {
                $targets[$processId] = [pscustomobject]@{
                    ProcessId   = $processId
                    Name        = $process.Name
                    Ports       = @($port)
                    CommandLine = $commandLine
                }
            }
            elseif ($port -notin $targets[$processId].Ports) {
                $targets[$processId].Ports += $port
            }
        }
    }

    return @($targets.Values | Sort-Object ProcessId)
}

Write-Host ""
Write-Host "=== CAGED Dashboard - encerrar API local ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Portas alvo: $($Ports -join ', ')"
Write-Host ""

$targets = Get-ApiListenerTargets -TargetPorts $Ports

if ($targets.Count -eq 0) {
    Write-Host "Nenhum processo uvicorn (app.main:app) encontrado nas portas informadas." -ForegroundColor Green
    Write-Host ""
    exit 0
}

Write-Host "Processos candidatos a encerramento:" -ForegroundColor Cyan
foreach ($target in $targets) {
    $portList = ($target.Ports | Sort-Object -Unique) -join ', '
    Write-Host ""
    Write-Host "  PID $($target.ProcessId) | portas: $portList | $($target.Name)"
    Write-Host "  $($target.CommandLine)"
}

Write-Host ""

$shouldStop = $Force
if (-not $shouldStop) {
    $answer = Read-Host "Encerrar esses processos? (S/N)"
    $shouldStop = $answer.Trim().ToUpperInvariant() -in @('S', 'SIM', 'Y', 'YES')
}

if (-not $shouldStop) {
    Write-Host "Operacao cancelada. Nenhum processo foi encerrado." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

$stopped = 0
foreach ($target in $targets) {
    $processId = $target.ProcessId
    if ($PSCmdlet.ShouldProcess("PID $processId", "Stop-Process")) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "Encerrado PID $processId" -ForegroundColor Green
            $stopped++
        }
        catch {
            Write-Warning "Falha ao encerrar PID ${processId}: $($_.Exception.Message)"
        }
    }
}

Write-Host ""
Write-Host "Total encerrado: $stopped de $($targets.Count)" -ForegroundColor Green
Write-Host "Dica: confira com 'Get-NetTCPConnection -LocalPort 8000 -State Listen' se a porta ficou livre."
Write-Host ""
