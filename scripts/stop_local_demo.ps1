[CmdletBinding()]
param(
    [string]$EnvFile = ".env"
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

$previousEnvFile = $env:ENV_FILE
$env:ENV_FILE = $envPath
try {
    & docker compose `
        -f (Join-Path $repoRoot "compose.yaml") `
        -f (Join-Path $repoRoot "compose.local.yaml") `
        down --remove-orphans
    if ($LASTEXITCODE -ne 0) {
        throw "Gagal menghentikan container demo."
    }
} finally {
    $env:ENV_FILE = $previousEnvFile
}

Write-Host "Container demo berhenti. Volume Redis tetap dipertahankan."
