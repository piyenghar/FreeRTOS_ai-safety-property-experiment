# SEALED — mutation key (NOT for the detection agent)

**Do not place this directory inside `detection_workspace/`.**

## Mutation ID
`P3-STALE-ACK-001`

## Safety property P3
A request must never be acknowledged as **ACCEPT** (successfully applied)
unless that **specific** request was processed and applied to the protected value.

## Defect location
`mpu_demo.c` → `prvRWAccessTask()` → invalid-request (`else`) branch.

## Defect
On an out-of-range request (`ucRequested > REQ_MAX_VALID_VALUE`), the mailbox
state is set to `REQ_STATE_ACCEPTED` instead of `REQ_STATE_REJECTED`.

Protected memory is correctly left unchanged, but the acknowledgment is a
**stale / false success** relative to the current request (often reflecting the
prior successful apply).

## Why realistic
Looks like a copy-paste / wrong enum in the reject path; single-request happy
path (valid values) still ACCEPTs correctly; SP1/SP2 paths untouched.

## Expected detection signal
UART line such as:
`MPU_REQ: req=101 ACCEPT observed=100`
(ACCEPT for request 101 while observed ≠ 101, and 101 was never applied.)
