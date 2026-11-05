$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m pip install -r (Join-Path $root "requirements.txt")
python -m unittest discover -v
Write-Host "NimblePDF is ready. Run .\run-nimblepdf.bat"
