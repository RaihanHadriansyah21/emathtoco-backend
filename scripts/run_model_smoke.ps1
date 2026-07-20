[CmdletBinding()]
param(
    [switch]$WriteGolden,
    [string]$Image = "emathtoco-worker:local",
    [string]$ModelDirectory = "Models_New",
    [ValidateRange(0, 71)]
    [int]$StartIndex = 0,
    [ValidateRange(1, 72)]
    [int]$BatchSize = 72
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$modelRoot = Join-Path $projectRoot $ModelDirectory
$manifestPath = Join-Path $modelRoot "manifest.json"
$goldenPath = Join-Path $projectRoot "Models\golden_inference.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$artifacts = @($manifest.artifacts) |
    Select-Object -Skip $StartIndex -First $BatchSize

foreach ($artifact in $artifacts) {
    $arguments = @(
        "run", "--rm", "--memory=6g", "--cpus=6",
        "-e", "PYTHONPATH=/workspace",
        "-e", "TF_CPP_MIN_LOG_LEVEL=3",
        "-e", "TF_ENABLE_ONEDNN_OPTS=0",
        "-v", "${projectRoot}:/workspace",
        "-v", "${modelRoot}:/models:ro",
        $Image,
        "python", "/workspace/scripts/smoke_model_artifacts.py",
        "--model-root", "/models",
        "--golden", "/workspace/Models/golden_inference.json",
        "--architecture", $artifact.architecture,
        "--section", $artifact.section
    )
    if ($WriteGolden) {
        $arguments += "--write-golden"
    }
    & docker @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Model smoke gagal: $($artifact.architecture) $($artifact.section)"
    }
}

if ($StartIndex -eq 0 -and $BatchSize -eq 72) {
    $golden = Get-Content -LiteralPath $goldenPath -Raw | ConvertFrom-Json
    if (@($golden.artifacts.PSObject.Properties).Count -ne 72) {
        throw "Golden inference harus berisi tepat 72 artifact."
    }
    Write-Host "Seluruh 72 model lolos smoke inference."
} else {
    Write-Host "Batch model $StartIndex..$($StartIndex + $artifacts.Count - 1) lulus."
}
