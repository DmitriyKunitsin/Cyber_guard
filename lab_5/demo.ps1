#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-DemoPause {
    if ($env:LAB_DEMO_PAUSE) {
        Start-Sleep -Seconds ([int]$env:LAB_DEMO_PAUSE)
    }
}

Write-Host "`n=== Lab 5, SHA-256 and Birthday Paradox ==="
Invoke-DemoPause

Write-Host "`nCLI help"
Write-Host 'python hash_lab.py --help'
python hash_lab.py --help
Invoke-DemoPause

Write-Host "`nTask 1. Full SHA-256 hash"
Write-Host 'python hash_lab.py hash-hex "lab5"'
python hash_lab.py hash-hex "lab5"
Write-Host 'python hash_lab.py hash-hex "Hash functions lab5 demo text."'
python hash_lab.py hash-hex "Hash functions lab5 demo text."
Invoke-DemoPause

Write-Host "`nTask 2. Truncated hash: first bits only"
Write-Host 'python hash_lab.py truncate "collision" --bits 32'
python hash_lab.py truncate "collision" --bits 32
Invoke-DemoPause

Write-Host "`nTask 3. Birthday paradox for truncated hash"
Write-Host "With bits=20, collision is found much earlier than 2^20 attempts"
Write-Host 'python hash_lab.py birthday-search --bits 20'
python hash_lab.py birthday-search --bits 20
Invoke-DemoPause

Write-Host "`nBuilt-in demo with explanation"
Write-Host 'python hash_lab.py demo'
python hash_lab.py demo
Invoke-DemoPause

Write-Host "`nRun tests"
Write-Host 'python -m pytest test_hash_lab.py -v --tb=short'
python -m pytest test_hash_lab.py -v --tb=short

Write-Host "`nDone."