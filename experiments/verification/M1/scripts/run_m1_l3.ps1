# Build and run independent M1 L3 range-check tests (host gcc / Windows).
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
$L3 = Join-Path $Root "experiments\verification\M1\l3"
$Results = Join-Path $Root "experiments\verification\M1\results"
$Log = Join-Path $Results "l3_range_test.log"
$Json = Join-Path $Results "l3_summary.json"
New-Item -ItemType Directory -Force -Path (Join-Path $L3 "build"), $Results | Out-Null

Push-Location $L3
try {
    gcc -std=c11 -Wall -Wextra -Werror -O0 -g -I. `
        l3_range_test.c range_check_under_test.c `
        -o build\l3_range_test.exe
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $env:M1_L3_LOG = $Log
    & .\build\l3_range_test.exe
    $testExit = $LASTEXITCODE
}
finally {
    Pop-Location
}

$py = @"
import json, re
from pathlib import Path
log = Path(r'$($Log.Replace('\','\\'))').read_text(encoding='utf-8', errors='replace')
summary = {'P1': {}, 'P2': {}, 'ALL': {}, 'oracle_pos': None, 'oracle_neg': None, 'cases': []}
for line in log.splitlines():
    m = re.match(r'(P1|P2|CTRL) name=(\S+) rx=(\d+) exp=(\d+).*=> (PASS|FAIL)', line)
    if m:
        summary['cases'].append({'property': m.group(1), 'name': m.group(2), 'rx': int(m.group(3)), 'exp': int(m.group(4)), 'result': m.group(5)})
    m = re.match(r'SUMMARY (P1|P2|ALL) pass=(\d+) fail=(\d+) total=(\d+)', line)
    if m:
        summary[m.group(1)] = {'pass': int(m.group(2)), 'fail': int(m.group(3)), 'total': int(m.group(4)), 'verdict': 'PASS' if int(m.group(3)) == 0 else 'FAIL'}
    m = re.match(r'ORACLE_(POS|NEG) (PASS|FAIL)', line)
    if m:
        summary['oracle_pos' if m.group(1) == 'POS' else 'oracle_neg'] = m.group(2)
Path(r'$($Json.Replace('\','\\'))').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: summary[k] for k in ('P1','P2','ALL','oracle_pos','oracle_neg')}, indent=2))
"@
python -c $py
Write-Host "log: $Log"
exit $testExit
