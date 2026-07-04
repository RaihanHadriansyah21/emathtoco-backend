[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [switch]$NoBuild,
    [int]$ReadyTimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    [System.IO.Path]::GetFullPath($EnvFile)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $EnvFile))
}

if (-not $envPath.StartsWith(
    $repoRoot + [System.IO.Path]::DirectorySeparatorChar,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Env file wajib berada di dalam repository backend."
}
if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Env file tidak ditemukan: $envPath"
}

$envValues = @{}
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match "^\s*([A-Z][A-Z0-9_]*)=(.*)$") {
        $envValues[$Matches[1]] = $Matches[2].Trim()
    }
}

if (-not $envValues["SUPABASE_URL"]) {
    throw "SUPABASE_URL belum diisi di env file."
}
if (
    (-not $envValues["SUPABASE_SECRET_KEY"]) -and
    (-not $envValues["SUPABASE_SERVICE_ROLE_KEY"])
) {
    throw "SUPABASE_SECRET_KEY belum diisi di env file."
}

& (Join-Path $PSScriptRoot "test_supabase_contract.ps1") -EnvFile $envPath

$modelRoot = Join-Path $repoRoot "Models"
$manifestPath = Join-Path $modelRoot "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Manifest model tidak ditemukan: $manifestPath"
}
$modelCount = @(
    Get-ChildItem -LiteralPath $modelRoot -Recurse -File -Filter "*.h5"
).Count
if ($modelCount -ne 72) {
    throw "Jumlah model harus 72, ditemukan: $modelCount"
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop belum aktif atau masih paused."
}

$previousEnvFile = $env:ENV_FILE
$env:ENV_FILE = $envPath
$composeArgs = @(
    "compose",
    "-f", (Join-Path $repoRoot "compose.yaml"),
    "-f", (Join-Path $repoRoot "compose.local.yaml")
)

$locationPushed = $false
try {
    Push-Location $repoRoot
    $locationPushed = $true
    & docker @composeArgs config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Validasi Docker Compose gagal."
    }

    $upArgs = @($composeArgs + @("up", "-d"))
    if (-not $NoBuild) {
        $upArgs += "--build"
    }
    $upArgs += @("redis", "api", "worker")
    & docker @upArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Container demo gagal dijalankan."
    }

    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
    do {
        try {
            & (Join-Path $PSScriptRoot "test_local_demo.ps1")
            Write-Host ""
            Write-Host "Backend lokal siap di http://127.0.0.1:8000"
            Write-Host "Langkah berikutnya: ngrok http 8000"
            exit 0
        } catch {
            $exitedWorkers = @(
                & docker @composeArgs ps --status exited --services worker
            )
            if ($exitedWorkers -contains "worker") {
                & docker @composeArgs logs --tail=100 worker
                throw "Worker AI berhenti saat startup. Periksa log di atas."
            }
            if ((Get-Date) -ge $deadline) {
                Write-Host ""
                Write-Host "Log API dan worker terakhir:"
                & docker @composeArgs logs --tail=100 api worker
                throw "Backend tidak ready dalam $ReadyTimeoutSeconds detik. $($_.Exception.Message)"
            }
            Start-Sleep -Seconds 5
        }
    } while ($true)
} finally {
    if ($locationPushed) {
        Pop-Location
    }
    $env:ENV_FILE = $previousEnvFile
}
