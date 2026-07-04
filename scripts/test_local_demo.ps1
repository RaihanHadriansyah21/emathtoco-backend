[CmdletBinding()]
param(
    [string]$ApiUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$baseUrl = $ApiUrl.TrimEnd("/")

$live = Invoke-RestMethod -Uri "$baseUrl/health/live" -TimeoutSec 10
if ($live.status -ne "healthy") {
    throw "API liveness tidak sehat."
}

$readyResponse = Invoke-WebRequest `
    -Uri "$baseUrl/health/ready" `
    -SkipHttpErrorCheck `
    -TimeoutSec 15
$ready = $readyResponse.Content | ConvertFrom-Json
if ($readyResponse.StatusCode -ne 200 -or $ready.status -ne "healthy") {
    $dependencyState = $ready.dependencies | ConvertTo-Json -Compress
    throw "Backend belum ready. Dependency: $dependencyState"
}

$contract = Invoke-RestMethod -Uri "$baseUrl/contracts/domain" -TimeoutSec 10
if (@($contract.section_codes).Count -ne 24) {
    throw "Kontrak domain tidak berisi 24 section."
}

Write-Host "PASS: API live, Supabase, Redis, worker, dan 24 section siap."
