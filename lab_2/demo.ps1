#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-DemoPause {
    if ($env:LAB_DEMO_PAUSE) {
        Start-Sleep -Seconds ([int]$env:LAB_DEMO_PAUSE)
    }
}

Write-Host "`n=== Lab 2: Entropy and byte frequencies ==="
Invoke-DemoPause

Write-Host "`nStep 0. Generate test files"
Write-Host 'python entropy_lab.py demo -n 8000 --seed 42'
python entropy_lab.py demo -n 8000 --seed 42
Invoke-DemoPause

Write-Host "`nStep 1. Available commands"
Write-Host 'python entropy_lab.py --help'
python entropy_lab.py --help
Invoke-DemoPause

Write-Host "`nStep 2. Byte frequencies (text file)"
Write-Host 'python entropy_lab.py freq samples/text.txt --top 8'
python entropy_lab.py freq samples/text.txt --top 8
Invoke-DemoPause

Write-Host "`nStep 3. Single symbol file (const.bin) - H ~ 0"
Write-Host 'python entropy_lab.py entropy samples/const.bin --top 4'
python entropy_lab.py entropy samples/const.bin --top 4
Invoke-DemoPause

Write-Host "`nStep 4. Random '0'/'1' (coin.txt) - H ~ 1 bit"
Write-Host 'python entropy_lab.py entropy samples/coin.txt --top 4'
python entropy_lab.py entropy samples/coin.txt --top 4
Invoke-DemoPause

Write-Host "`nStep 5. Random bytes 0..255 (uniform.bin) - H ~ 8 bits"
Write-Host 'python entropy_lab.py entropy samples/uniform.bin --top 8'
python entropy_lab.py entropy samples/uniform.bin --top 8
Invoke-DemoPause

Write-Host "`nStep 6. Two symbols 50/50 (two_equal.bin) - H ~ 1 bit"
Write-Host 'python entropy_lab.py entropy samples/two_equal.bin --top 4'
python entropy_lab.py entropy samples/two_equal.bin --top 4
Invoke-DemoPause

Write-Host "`nStep 7. Repeating text (text.txt) - entropy lower than max"
Write-Host 'python entropy_lab.py entropy samples/text.txt --top 8'
python entropy_lab.py entropy samples/text.txt --top 8
Invoke-DemoPause

Write-Host "`nStep 8. Run tests"
Write-Host 'python -m pytest test_entropy_new.py -v --tb=short'
python -m pytest test_entropy_new.py -v --tb=short

Write-Host "`n=== Done ==="