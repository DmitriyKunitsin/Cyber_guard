#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-DemoPause {
    if ($env:LAB_DEMO_PAUSE) {
        Start-Sleep -Seconds ([int]$env:LAB_DEMO_PAUSE)
    }
}

Write-Host "`n=== Lab 3, Stream Ciphers ==="
Invoke-DemoPause

Write-Host "`nShow CLI help"
Write-Host 'python stream_ciphers.py -v --help'
python stream_ciphers.py -v --help
Invoke-DemoPause

Write-Host "`nPrepare samples using main Python code"
Write-Host 'python stream_ciphers.py prepare-samples --dir samples --method secrets'
python stream_ciphers.py prepare-samples --dir samples --method secrets
Invoke-DemoPause

Write-Host "`nTask 1. Key file from random bytes (PRNG)"
Write-Host "Key already generated in samples/key.bin"
Write-Host "File sizes:"
Get-ChildItem samples/plain.txt, samples/key.bin | Format-Table Name, Length
Invoke-DemoPause

Write-Host "`nTask 2. Vernam cipher (XOR): encrypt and decrypt file"
Write-Host 'python stream_ciphers.py vernam-encrypt samples/plain.txt samples/key.bin samples/vernam.bin'
python stream_ciphers.py vernam-encrypt samples/plain.txt samples/key.bin samples/vernam.bin
Write-Host 'python stream_ciphers.py vernam-decrypt samples/vernam.bin samples/key.bin samples/recovered.txt'
python stream_ciphers.py vernam-decrypt samples/vernam.bin samples/key.bin samples/recovered.txt
# Compare files: if identical, print success
$plain = Get-Content samples/plain.txt -Raw
$recovered = Get-Content samples/recovered.txt -Raw
if ($plain -eq $recovered) {
    Write-Host "Files match: true"
} else {
    Write-Host "Files differ: false"
}
Invoke-DemoPause

Write-Host "`nTask 3. Apply ready-made stream cipher ChaCha20"
Write-Host 'python stream_ciphers.py chacha-encrypt samples/plain.txt samples/key.bin samples/chacha.bin'
python stream_ciphers.py chacha-encrypt samples/plain.txt samples/key.bin samples/chacha.bin
Write-Host 'python stream_ciphers.py chacha-decrypt samples/chacha.bin samples/key.bin samples/chacha_plain.txt'
python stream_ciphers.py chacha-decrypt samples/chacha.bin samples/key.bin samples/chacha_plain.txt
$chacha_plain = Get-Content samples/chacha_plain.txt -Raw
if ($plain -eq $chacha_plain) {
    Write-Host "Round-trip: true"
} else {
    Write-Host "Round-trip: false"
}
Invoke-DemoPause

Write-Host "`nRun tests"
Write-Host 'python -m pytest test_stream_ciphers.py -v --tb=short'
python -m pytest test_stream_ciphers.py -v --tb=short

Write-Host "`nDone."