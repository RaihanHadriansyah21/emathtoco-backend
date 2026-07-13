[CmdletBinding()]
param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
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
        $envValues[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
    }
}

$supabaseUrl = $envValues["SUPABASE_URL"]
$supabaseKey = $envValues["SUPABASE_SECRET_KEY"]
if (-not $supabaseKey) {
    $supabaseKey = $envValues["SUPABASE_SERVICE_ROLE_KEY"]
}
if (-not $supabaseUrl -or -not $supabaseKey) {
    throw "SUPABASE_URL dan SUPABASE_SECRET_KEY wajib diisi."
}
$supabaseUrl = $supabaseUrl.TrimEnd("/")
if ($supabaseUrl -notmatch "^https?://[^/]+$") {
    throw "Format SUPABASE_URL tidak valid."
}

function Invoke-ContractWebRequest {
    param(
        [Parameter(Mandatory)]
        [string]$Uri,
        [string]$Method = "Get",
        [Parameter(Mandatory)]
        [hashtable]$Headers,
        [string]$Body,
        [int]$TimeoutSec = 20
    )

    $request = @{
        Uri = $Uri
        Method = $Method
        Headers = $Headers
        TimeoutSec = $TimeoutSec
        UseBasicParsing = $true
    }
    if ($PSBoundParameters.ContainsKey("Body")) {
        $request["Body"] = $Body
    }

    try {
        return Invoke-WebRequest @request
    } catch {
        $response = $_.Exception.Response
        if ($null -eq $response) {
            throw
        }

        $content = ""
        try {
            $stream = $response.GetResponseStream()
            if ($null -ne $stream) {
                $reader = New-Object System.IO.StreamReader($stream)
                $content = $reader.ReadToEnd()
            }
        } catch {
            $content = ""
        }

        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            Content = $content
        }
    }
}

$headers = @{
    apikey = $supabaseKey
    Authorization = "Bearer $supabaseKey"
    Accept = "application/json"
}

try {
    $settingsResponse = Invoke-ContractWebRequest `
        -Uri "$supabaseUrl/rest/v1/system_settings?select=setting_key&limit=1" `
        -Headers $headers `
        -TimeoutSec 20
} catch {
    throw "Koneksi REST Supabase gagal. Periksa URL, secret key, dan internet."
}

if ($settingsResponse.StatusCode -ne 200) {
    throw (
        "Supabase terhubung, tetapi tabel system_settings belum tersedia " +
        "melalui REST. Terapkan migration dan GRANT hardening."
    )
}

function Test-RpcExistsWithoutMutation {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [hashtable]$Body
    )

    $rpcHeaders = $headers.Clone()
    $rpcHeaders["Content-Type"] = "application/json"
    $rpcResponse = Invoke-ContractWebRequest `
        -Uri "$supabaseUrl/rest/v1/rpc/$Name" `
        -Method Post `
        -Headers $rpcHeaders `
        -Body ($Body | ConvertTo-Json -Compress) `
        -TimeoutSec 20

    if ($rpcResponse.StatusCode -eq 404) {
        return $false
    }
    if ($rpcResponse.StatusCode -ge 500) {
        throw "Supabase RPC $Name gagal diperiksa."
    }

    if ($rpcResponse.StatusCode -ge 400) {
        try {
            $errorPayload = $rpcResponse.Content | ConvertFrom-Json
            if ($errorPayload.code -in @("PGRST202", "PGRST204")) {
                return $false
            }
        } catch {
            throw "Respons pemeriksaan RPC $Name tidak valid."
        }
    }
    return $true
}

$rpcProbes = @(
    @{
        Name = "claim_ai_job"
        Body = @{
            p_submission_id = "invalid-uuid"
            p_model_ai = "MobileNetV2"
        }
    },
    @{
        Name = "fail_ai_job"
        Body = @{
            p_submission_id = "invalid-uuid"
            p_error_code = "PREFLIGHT_ONLY"
        }
    },
    @{
        Name = "complete_ai_job"
        Body = @{
            p_submission_id = "invalid-uuid"
            p_total_score = 0
        }
    },
    @{
        Name = "reconcile_stale_ai_jobs"
        Body = @{
            p_stale_before = "invalid-timestamp"
        }
    }
)
$missingRpcs = @(
    foreach ($probe in $rpcProbes) {
        if (-not (Test-RpcExistsWithoutMutation `
            -Name $probe.Name `
            -Body $probe.Body
        )) {
            $probe.Name
        }
    }
)
if ($missingRpcs.Count -gt 0) {
    $missingText = $missingRpcs -join ", "
    throw (
        "Supabase terhubung, tetapi migration hardening belum lengkap. " +
        "RPC yang hilang: $missingText"
    )
}

$storageHeaders = @{
    apikey = $supabaseKey
    Authorization = "Bearer $supabaseKey"
}
try {
    $bucketResponse = Invoke-ContractWebRequest `
        -Uri "$supabaseUrl/storage/v1/bucket/lembar-jawaban" `
        -Headers $storageHeaders `
        -TimeoutSec 20
} catch {
    throw "REST Supabase siap, tetapi bucket lembar-jawaban tidak dapat diverifikasi."
}
if ($bucketResponse.StatusCode -ne 200) {
    throw "Bucket lembar-jawaban tidak siap (HTTP $($bucketResponse.StatusCode))."
}

Write-Host "PASS: Supabase REST, kontrak RPC, dan bucket Storage siap."
