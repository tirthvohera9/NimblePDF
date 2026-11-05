[CmdletBinding()]
param(
  [string]$BaseUrl = "http://127.0.0.1:3000",
  [string]$FixturePath,
  [switch]$ValidateFixture,
  [int]$TimeoutSeconds = 5
)

$ErrorActionPreference = "Stop"
$failures = [System.Collections.Generic.List[string]]::new()

function Assert([bool]$Condition, [string]$Message) {
  if (-not $Condition) { $failures.Add($Message) }
}

function Read-Json([string]$Path) {
  Assert (Test-Path -LiteralPath $Path -PathType Leaf) "Fixture not found: $Path"
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Validate-Fixture($Fixture) {
  if ($null -eq $Fixture) { return }
  $allowed = @("id", "input", "health", "workflow", "ui")
  foreach ($p in $Fixture.PSObject.Properties.Name) {
    Assert ($allowed -contains $p) "Unknown fixture property: $p"
  }
  Assert (-not [string]::IsNullOrWhiteSpace([string]$Fixture.id)) "fixture.id is required"
  Assert ($null -ne $Fixture.input) "fixture.input is required"
  if ($null -ne $Fixture.input) {
    $path = [string]$Fixture.input.path
    Assert (-not [string]::IsNullOrWhiteSpace($path)) "input.path is required"
    Assert (-not [System.IO.Path]::IsPathRooted($path)) "input.path must be relative"
    Assert (-not ($path -match '(^|[/\\])\.\.([/\\]|$)|^[A-Za-z]:|^[A-Za-z][A-Za-z0-9+.-]*://')) "input.path must be local and traversal-free"
    Assert ($path -match '\.pdf$') "input.path must end in .pdf"
    Assert ([string]$Fixture.input.sha256 -match '^[0-9a-f]{64}$') "input.sha256 must be lowercase SHA-256"
    Assert ([int64]$Fixture.input.bytes -ge 0) "input.bytes must be non-negative"
    Assert ([int]$Fixture.input.pages -ge 0) "input.pages must be non-negative"
  }
  Assert ($null -ne $Fixture.health) "fixture.health is required"
  if ($null -ne $Fixture.health) {
    Assert ([int]$Fixture.health.minimumFindings -ge 0 -and [int]$Fixture.health.minimumFindings -le 100) "health.minimumFindings must be 0..100"
  }
  Assert ($null -ne $Fixture.workflow) "fixture.workflow is required"
  if ($null -ne $Fixture.workflow) {
    Assert ([int]$Fixture.workflow.maxSteps -ge 1 -and [int]$Fixture.workflow.maxSteps -le 50) "workflow.maxSteps must be 1..50"
    Assert ([int64]$Fixture.workflow.maxBytes -gt 0) "workflow.maxBytes must be positive"
  }
}

if ($ValidateFixture -and -not $FixturePath) {
  Write-Error "-ValidateFixture requires -FixturePath"
  exit 1
}
if ($FixturePath) { Validate-Fixture (Read-Json $FixturePath) }
if ($ValidateFixture) {
  if ($failures.Count -eq 0) { Write-Output "Fixture validation passed"; exit 0 }
  $failures | ForEach-Object { Write-Error $_ }; exit 1
}

try {
  $uri = [Uri]$BaseUrl
  Assert ($uri.IsLoopback) "BaseUrl must be loopback (got $BaseUrl)"
  Assert ($uri.Scheme -eq "http" -or $uri.Scheme -eq "https") "BaseUrl must use HTTP(S)"
} catch { $failures.Add("BaseUrl is not a valid URL: $BaseUrl") }

function Get-Api([string]$Path) {
  try { return Invoke-RestMethod -Uri ([Uri]::new($BaseUrl.TrimEnd("/") + $Path)) -Method Get -TimeoutSec $TimeoutSeconds }
  catch { $failures.Add("GET $Path failed: $($_.Exception.Message)"); return $null }
}

function Post-Api([string]$Path, $Body) {
  try {
    $json = $Body | ConvertTo-Json -Depth 10
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-WebRequest -UseBasicParsing -Uri ([Uri]::new($BaseUrl.TrimEnd("/") + $Path)) -Method Post -Body $bytes -ContentType "application/json" -TimeoutSec $TimeoutSeconds
  } catch {
    if ($_.Exception.Response) { return $_.Exception.Response }
    $failures.Add("POST $Path failed: $($_.Exception.Message)"); return $null
  }
}

$sample = @{
  path = "fixtures/sample.pdf"; sha256 = ("0" * 64); bytes = 1048576; pages = 2
}

$health = Get-Api "/api/health"
if ($null -ne $health) {
  Assert ($health.status -in @("ok", "warning", "error")) "health.status is invalid"
  Assert ($health.score -is [ValueType] -and [double]$health.score -ge 0 -and [double]$health.score -le 100) "health.score must be 0..100"
  Assert ($null -ne $health.findings -and @($health.findings).Count -gt 0) "health.findings must be non-empty"
  foreach ($finding in @($health.findings)) {
    Assert (-not [string]::IsNullOrWhiteSpace([string]$finding.id)) "finding.id is required"
    Assert ($finding.severity -in @("info", "warning", "error")) "finding.severity is invalid"
    Assert (-not [string]::IsNullOrWhiteSpace([string]$finding.message)) "finding.message is required"
  }
}

$planResponse = Post-Api "/api/plan" @{ input = $sample; goal = "compress and validate"; maxSteps = 8 }
if ($null -ne $planResponse) {
  $plan = $planResponse.Content | ConvertFrom-Json
  Assert ($plan.steps -and @($plan.steps).Count -gt 0) "plan.steps must be non-empty"
  Assert ([double]$plan.totalEstimate -gt 0) "plan.totalEstimate must be positive"
  Assert (@($plan.steps).Count -le 8) "plan exceeds maxSteps"
}

$unsafe = Post-Api "/api/plan" @{ input = @{ path = "../outside.pdf"; bytes = 1; pages = 1 }; goal = "inspect"; maxSteps = 8 }
if ($null -ne $unsafe) {
  Assert ([int]$unsafe.StatusCode -ge 400 -and [int]$unsafe.StatusCode -lt 500) "path traversal must be rejected (4xx)"
}

$oversized = Post-Api "/api/plan" @{ input = @{ path = "fixtures/large.pdf"; bytes = 10737418241; pages = 1 }; goal = "inspect"; maxSteps = 8 }
if ($null -ne $oversized) {
  Assert ([int]$oversized.StatusCode -ge 400 -and [int]$oversized.StatusCode -lt 500) "oversized input must be rejected (4xx)"
}

$contract = Get-Api "/api/ui-contract"
if ($null -ne $contract) {
  Assert ([string]$contract.version -match '^\d+') "ui contract version is required"
  foreach ($action in @("health", "plan", "run")) {
    Assert (@($contract.actions).name -contains $action) "ui contract missing action: $action"
  }
  foreach ($state in @("loading", "error", "success")) {
    Assert (@($contract.states) -contains $state) "ui contract missing state: $state"
  }
}

if ($failures.Count -eq 0) { Write-Output "Smoke checks passed"; exit 0 }
$failures | ForEach-Object { Write-Error $_ }
exit 1
