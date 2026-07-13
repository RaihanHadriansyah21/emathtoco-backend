[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$sourcePath = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..\..\supabase_data_import.sql")
)
$backupRoot = [System.IO.Path]::GetFullPath(
    "D:\PTA\Emathtoco_Backups"
)
$sevenZipCandidates = @(
    "C:\Program Files\7-Zip\7z.exe",
    "C:\Program Files (x86)\7-Zip\7z.exe",
    (Get-Command 7z.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
) | Where-Object { $_ }

if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Dump plaintext tidak ditemukan: $sourcePath"
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$sevenZip = $sevenZipCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1

function Get-PlainTextFromSecureString {
    param([Parameter(Mandatory)][securestring]$SecureString)

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function New-Aes256EncryptedBackup {
    param(
        [Parameter(Mandatory)][string]$InputPath,
        [Parameter(Mandatory)][string]$OutputPath
    )

    $first = Read-Host "Masukkan passphrase kuat untuk arsip AES-256" -AsSecureString
    $second = Read-Host "Ulangi passphrase" -AsSecureString
    $password = Get-PlainTextFromSecureString -SecureString $first
    $passwordConfirm = Get-PlainTextFromSecureString -SecureString $second
    if ($password -ne $passwordConfirm) {
        throw "Passphrase tidak sama. Plaintext tetap dipertahankan."
    }
    if ($password.Length -lt 12) {
        throw "Passphrase minimal 12 karakter. Plaintext tetap dipertahankan."
    }

    $plainBytes = [IO.File]::ReadAllBytes($InputPath)
    $salt = New-Object byte[] 16
    $iv = New-Object byte[] 16
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($salt)
    $rng.GetBytes($iv)

    $kdf = New-Object Security.Cryptography.Rfc2898DeriveBytes(
        $password,
        $salt,
        200000,
        [Security.Cryptography.HashAlgorithmName]::SHA256
    )
    $keyMaterial = $kdf.GetBytes(64)
    $aesKey = $keyMaterial[0..31]
    $hmacKey = $keyMaterial[32..63]

    $aes = [Security.Cryptography.Aes]::Create()
    $aes.KeySize = 256
    $aes.Mode = [Security.Cryptography.CipherMode]::CBC
    $aes.Padding = [Security.Cryptography.PaddingMode]::PKCS7
    $aes.Key = $aesKey
    $aes.IV = $iv

    $encryptor = $aes.CreateEncryptor()
    $cipherBytes = $encryptor.TransformFinalBlock($plainBytes, 0, $plainBytes.Length)
    $header = [Text.Encoding]::ASCII.GetBytes("EMATHAES1")
    $iterations = [BitConverter]::GetBytes([int]200000)
    if (-not [BitConverter]::IsLittleEndian) {
        [Array]::Reverse($iterations)
    }

    $payload = New-Object byte[] ($header.Length + $iterations.Length + $salt.Length + $iv.Length + $cipherBytes.Length)
    [Buffer]::BlockCopy($header, 0, $payload, 0, $header.Length)
    [Buffer]::BlockCopy($iterations, 0, $payload, $header.Length, $iterations.Length)
    [Buffer]::BlockCopy($salt, 0, $payload, $header.Length + $iterations.Length, $salt.Length)
    [Buffer]::BlockCopy($iv, 0, $payload, $header.Length + $iterations.Length + $salt.Length, $iv.Length)
    [Buffer]::BlockCopy($cipherBytes, 0, $payload, $header.Length + $iterations.Length + $salt.Length + $iv.Length, $cipherBytes.Length)

    $hmac = New-Object Security.Cryptography.HMACSHA256(,$hmacKey)
    $tag = $hmac.ComputeHash($payload)

    $finalBytes = New-Object byte[] ($payload.Length + $tag.Length)
    [Buffer]::BlockCopy($payload, 0, $finalBytes, 0, $payload.Length)
    [Buffer]::BlockCopy($tag, 0, $finalBytes, $payload.Length, $tag.Length)
    [IO.File]::WriteAllBytes($OutputPath, $finalBytes)

    $readBack = [IO.File]::ReadAllBytes($OutputPath)
    $storedPayloadLength = $readBack.Length - 32
    $storedPayload = New-Object byte[] $storedPayloadLength
    $storedTag = New-Object byte[] 32
    [Buffer]::BlockCopy($readBack, 0, $storedPayload, 0, $storedPayloadLength)
    [Buffer]::BlockCopy($readBack, $storedPayloadLength, $storedTag, 0, 32)
    $computedTag = $hmac.ComputeHash($storedPayload)
    if (-not [Linq.Enumerable]::SequenceEqual($storedTag, $computedTag)) {
        throw "Verifikasi HMAC arsip gagal. Plaintext tetap dipertahankan."
    }

    $decryptor = $aes.CreateDecryptor()
    $offset = $header.Length + $iterations.Length + $salt.Length + $iv.Length
    $storedCipherLength = $storedPayload.Length - $offset
    $storedCipher = New-Object byte[] $storedCipherLength
    [Buffer]::BlockCopy($storedPayload, $offset, $storedCipher, 0, $storedCipherLength)
    $decryptedBytes = $decryptor.TransformFinalBlock($storedCipher, 0, $storedCipher.Length)

    $plainHash = [Security.Cryptography.SHA256]::Create().ComputeHash($plainBytes)
    $decryptedHash = [Security.Cryptography.SHA256]::Create().ComputeHash($decryptedBytes)
    if (-not [Linq.Enumerable]::SequenceEqual($plainHash, $decryptedHash)) {
        throw "Verifikasi decrypt arsip gagal. Plaintext tetap dipertahankan."
    }
}

if ($sevenZip) {
    $archivePath = Join-Path $backupRoot "$timestamp-supabase-data.7z"

    Write-Host "7-Zip ditemukan: $sevenZip"
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
} else {
    $archivePath = Join-Path $backupRoot "$timestamp-supabase-data.sql.aes"
    Write-Host "7-Zip tidak ditemukan. Menggunakan fallback AES-256 + HMAC bawaan PowerShell."
    New-Aes256EncryptedBackup -InputPath $sourcePath -OutputPath $archivePath
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
