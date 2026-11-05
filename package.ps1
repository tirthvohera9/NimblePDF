$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m pip install -r (Join-Path $root "requirements.txt")
winget install --id UB-Mannheim.TesseractOCR --source winget --accept-source-agreements --accept-package-agreements
winget install --id oschwartz10612.Poppler --source winget --accept-source-agreements --accept-package-agreements
python -m unittest discover -v
Write-Host "NimblePDF is ready. Run .\run-nimblepdf.bat"
