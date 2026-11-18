# M1 verification workspace (range checking)

Baseline + independent L3 for `prvCheckReceivedValueWithinExpectedRange()` in QueueSet.c.

- [BASELINE.md](BASELINE.md) — properties, boundaries, QEMU results  
- [L3-verification.md](L3-verification.md) — host L3 P1/P2 results, assert handling, limitations  
- [build_commands.md](build_commands.md) — exact build/run commands  
- `l3/` — independent host harness (does not compile or edit QueueSet.c)  
- `results/` — UART log, symbols, boundary oracle JSON, L3 log/summary  
- `scripts/run_m1_baseline.sh` — end-to-end baseline runner  
- `scripts/run_m1_l3.ps1` / `run_m1_l3.sh` — host L3 build + run  

No T1/T2/T3 pilots. Does not modify QueueSet.c or M2 artifacts.
