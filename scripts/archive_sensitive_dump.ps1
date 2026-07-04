[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$sourcePath = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\..\supabase_data_import.sql")
)
$backupRoot = [System.IO.Path]::GetFullPath(
    "D:\PTA\Emathtoco_Backups"
)
$sevenZip = "C:\Program Files\7-Zip\7z.exe"

if (-not (Test-Path -LiteralPath $sevenZip -PathType Leaf)) {
    throw "7-Zip tidak ditemukan di lokasi standar: $sevenZip"
}
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Dump plaintext tidak ditemukan: $sourcePath"
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archivePath = Join-Path $backupRoot "$timestamp-supabase-data.7z"

Write-Host "Masukkan passphrase kuat ketika 7-Zip meminta password."
Write-Host "Passphrase tidak akan disimpan oleh script ini."

& $sevenZip a -t7z -m0=lzma2 -mhe=on -p -- $archivePath $sourcePath
if ($LASTEXITCODE -ne 0) {
    throw "Pembuatan arsip terenkripsi gagal. Plaintext tetap dipertahankan."
}

Write-Host "Masukkan passphrase yang sama untuk verifikasi arsip."
& $sevenZip t -p -- $archivePath
if ($LASTEXITCODE -ne 0) {
    throw "Verifikasi arsip gagal. Plaintext tetap dipertahankan."
}

$resolvedArchive = [System.IO.Path]::GetFullPath($archivePath)
if (-not $resolvedArchive.StartsWith(
    $backupRoot + [System.IO.Path]::DirectorySeparatorChar,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Lokasi arsip berada di luar direktori backup yang diizinkan."
}

Remove-Item -LiteralPath $sourcePath -Force
Write-Host "Selesai. Arsip terverifikasi: $resolvedArchive"
Write-Host "Plaintext telah dihapus: $sourcePath"
