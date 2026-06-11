#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-DemoPause {
    if ($env:LAB_DEMO_PAUSE) {
        Start-Sleep -Seconds ([int]$env:LAB_DEMO_PAUSE)
    }
}

Write-Host "`n=== Lab 6, Fast modular exponentiation ==="
Invoke-DemoPause

Write-Host "`nShow CLI help"
Write-Host 'python modexp_lab.py --help'
python modexp_lab.py --help
Invoke-DemoPause

Write-Host "`nTask 1. Compute 5^701 mod 11 with fast algorithm"
Write-Host 'python modexp_lab.py compute 5 701 11'
python modexp_lab.py compute 5 701 11
Invoke-DemoPause

Write-Host "`nTask 2. Detailed trace of 5^701 mod 11"
Write-Host 'python modexp_lab.py trace 5 701 11'
python modexp_lab.py trace 5 701 11
Invoke-DemoPause

Write-Host "`nAnother example: 3^800 mod 13"
Write-Host 'python modexp_lab.py trace 3 800 13'
python modexp_lab.py trace 3 800 13
Invoke-DemoPause

Write-Host "`nTask 3. Hamming weight influence (32 bits)"
Write-Host 'python modexp_lab.py hamming-demo --bits 32'
python modexp_lab.py hamming-demo --bits 32
Invoke-DemoPause

Write-Host "`nCompare fast vs naive algorithm (small x only)"
Write-Host 'python modexp_lab.py compare 7 200 1000'
python modexp_lab.py compare 7 200 1000
Invoke-DemoPause

Write-Host "`nRun tests"
Write-Host 'python -m pytest test_modexp_lab.py -v --tb=short'
python -m pytest test_modexp_lab.py -v --tb=short

Write-Host "`nDone."