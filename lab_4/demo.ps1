#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-DemoPause {
    if ($env:LAB_DEMO_PAUSE) {
        Start-Sleep -Seconds ([int]$env:LAB_DEMO_PAUSE)
    }
}

Write-Host "`n=== Lab 4, XTEA and CBC ==="
Invoke-DemoPause

Write-Host "`nCLI help"
Write-Host 'python block_cipher.py --help'
python block_cipher.py --help
Invoke-DemoPause

Write-Host "`nPrepare samples"
Write-Host 'python block_cipher.py prepare-samples --dir samples'
python block_cipher.py prepare-samples --dir samples
Invoke-DemoPause

Write-Host "`nTask 1. Block cipher XTEA (built-in demo)"
Write-Host 'python block_cipher.py demo --dir samples'
python block_cipher.py demo --dir samples
Invoke-DemoPause

Write-Host "`nTask 2. Encrypt and decrypt file (CBC mode)"
Write-Host 'python block_cipher.py encrypt samples/plain.txt samples/cipher.bin --key-file samples/key.bin'
python block_cipher.py encrypt samples/plain.txt samples/cipher.bin --key-file samples/key.bin
Write-Host 'python block_cipher.py decrypt samples/cipher.bin samples/restored.txt --key-file samples/key.bin'
python block_cipher.py decrypt samples/cipher.bin samples/restored.txt --key-file samples/key.bin

# Compare files
$plain = Get-Content samples/plain.txt -Raw
$restored = Get-Content samples/restored.txt -Raw
if ($plain -eq $restored) {
    Write-Host "Match: true"
} else {
    Write-Host "Match: false"
}
Invoke-DemoPause

Write-Host "`nRun tests"
Write-Host 'python -m pytest test_block_cipher.py -v --tb=short'
python -m pytest test_block_cipher.py -v --tb=short

Write-Host "`nDone."