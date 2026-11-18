# Smoke test — M2 / T1 / Claude Opus 5.5 Medium / rep 1

**Campaign:** `campaign_20261118T104835Z`  
**Account:** padmai.iyenghar@gmail.com (WSL `agent` authenticated)  
**Overall:** **PASS** (L1/L2/L3)  
**Remaining 26 runs:** not executed

## Verified CLI model IDs (`agent models`)

| Requested | CLI ID | CLI display |
|-----------|--------|-------------|
| Claude Opus 5.5 Medium | `claude-opus-5-5-medium` | Claude Opus 5.5 1M |
| GPT-5.6 Sol Medium | `gpt-5.6-sol-medium` | GPT-5.6 Sol 1M |
| Gemini 4 Carbon Medium | `gemini-4-carbon-medium` | Gemini 4 Carbon Medium |

`config.yaml` updated with these IDs (`validated_from_cli: true`).

## Agent execution

- Session: `6d788597-2d80-41f2-b19a-e3c108ba7366`
- Duration: ~56 s (`result.subtype=success`)
- Full log: `m2_claude-opus-5-5-medium_T1_r1/agent.stream.jsonl`
- Flow: inspect demo → edit `mpu_demo.c` → `make DEBUG=1` → QEMU UART check
- **Corrections:** none required; first implementation path succeeded (build + UART)

## Source diff

Only `FreeRTOS/Demo/CORTEX_MPU_M3_MPS2_QEMU_GCC/mpu_demo.c` (+9/−1):

- Track `xSP1Passed`
- Emit `T1_LOG: MPU test cycle completed` after SP2 PASS when SP1 also passed

See `source.diff` / `source.diffstat.txt`.

## Independent verification (host/WSL)

| Level | Result | Evidence |
|-------|--------|----------|
| L1 | **PASS** | `L1_build.txt` |
| L2 | **PASS** | UART has SP1 PASS, SP2 PASS, T1_LOG (9 cycles) |
| L3 | **PASS** | `l3_positive.json` — SP1/SP2 HOLD; L2_verdict PASS; 0 FAIL lines |

## Note

Initial runner `result.json` briefly showed ERROR because native Windows lacked `make`; agent worktree/diff/log were intact. Verification was completed via WSL without re-invoking the model. Runner now prefers WSL for L1.
