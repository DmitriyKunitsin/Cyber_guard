#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-DemoPause {
    if ($env:LAB_DEMO_PAUSE) {
        Start-Sleep -Seconds ([int]$env:LAB_DEMO_PAUSE)
    }
}

Write-Host "`n=== Lab 1, Caesar Cipher ==="
Invoke-DemoPause

Write-Host "`nCiphertext 'Khoor' in tasks 2,3,4 is 'Hello' with key 3"
Invoke-DemoPause

Write-Host "`nTask 1. Encrypt/Decrypt (key 7)"
Write-Host 'python caesar.py -v encrypt "Attack at dawn" -k 7'
python caesar.py -v encrypt "Attack at dawn" -k 7
Write-Host 'python caesar.py -v decrypt "Haahjr ha khdu" -k 7'
python caesar.py -v decrypt "Haahjr ha khdu" -k 7
Invoke-DemoPause

Write-Host "`nTask 2. Known-plaintext attack"
Write-Host 'python caesar.py -v kpa --plain "Hello" --cipher "Khoor"'
python caesar.py -v kpa --plain "Hello" --cipher "Khoor"
Write-Host "Key = 3 (shift for Hello -> Khoor)"
Invoke-DemoPause

Write-Host "`nTask 3. Brute-force (26 variants)"
Write-Host 'python caesar.py -v brute "Khoor"'
python caesar.py -v brute "Khoor"
Invoke-DemoPause

Write-Host "`nTask 4. Dictionary attack"
Write-Host 'python caesar.py -v dict-attack "Khoor"'
python caesar.py -v dict-attack "Khoor"
Invoke-DemoPause

Write-Host "`nRunning tests..."
Write-Host 'python -m pytest test_caesar.py -v --tb=short'
python -m pytest test_caesar.py -v --tb=short

Write-Host "`nDone."