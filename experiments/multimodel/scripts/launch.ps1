# Launch DSN2027 M2 multi-model matrix (Windows host -> WSL agent).
param(
    [switch]$DryRun,
    [switch]$SampleWorktreeOnly,
    [switch]$RefreshModels,
    [int]$Limit = 0,
    [string]$Config = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $Root

python -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    python -m pip install --user pyyaml
}

$argsList = @("experiments\multimodel\scripts\run_matrix.py")
if ($Config) { $argsList += @("--config", $Config) }
if ($DryRun) { $argsList += "--dry-run" }
if ($SampleWorktreeOnly) { $argsList += "--sample-worktree-only" }
if ($RefreshModels) { $argsList += "--refresh-models" }
if ($Limit -gt 0) { $argsList += @("--limit", "$Limit") }

python @argsList
