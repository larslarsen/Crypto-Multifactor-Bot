# CEX-002 first corrected real acquisition execution

## Authorization and identity

- Review: 342
- Ticket: CEX-002
- Repository commit before execution: `0a6401041af3ca36b6c3264d1aa7e12dae1cb5f7`
- Plan receipt: `data/cex002_qualify/gate2/plan_receipts/c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167.json`
- Plan receipt SHA-256: `c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167`
- Plan identity: `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22`
- Policy identity: `adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2`
- Holdout boundary: `c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2`
- Acquisition source SHA-256: `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`
- Acquisition CLI SHA-256: `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`

## Exact execution

The one authorized bounded full-plan acquisition was executed from the repository root:

```text
start_epoch=$(date +%s.%N); start_utc=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ); ( set -a; . ./.env || exit 5; set +a; test -n "${COINALYZE_API_KEY:-}" || exit 5; export PYTHONDONTWRITEBYTECODE=1; exec timeout --signal=TERM --kill-after=5m 6h .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py acquire --store-root data/cex002_qualify --max-wall-seconds 21000 ); status=$?; end_epoch=$(date +%s.%N); end_utc=$(date -u +%Y-%m-%dT%H:%M:%S.%NZ); elapsed=$(awk -v a="$start_epoch" -v b="$end_epoch" 'BEGIN{printf "%.3f", b-a}'); printf '\nTIMING start=%s end=%s elapsed_seconds=%s exit=%s\n' "$start_utc" "$end_utc" "$elapsed" "$status"; exit "$status"
```

The wrapper's complete captured output was:

```text
command=acquire exit=2 stop=max_wall_seconds

TIMING start=2026-08-28T04:22:17.133426573Z end=2026-08-28T10:16:34.174694366Z elapsed_seconds=21257.042 exit=2
```

Captured child stdout and stderr were empty. Exit 2 is the Review-342 accepted bounded stop (`max_wall_seconds`). No acquisition, replay, or verify command was run again.

## Pre-run capacity evidence

The pre-run ADR-0028 equation was:

```text
stable=139577980018 + reserve=49342982554 = required=188920962572
available=246714912768
headroom=57793950196
```

The receipt's pre-capacity state remained `sufficient`; post-capacity state was also `sufficient` with `available_bytes=248854040576` and `needed_bytes=189348788134`.

## Read-only reconciliation

Reconciliation inspected the store filesystem and opened `file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately setting `PRAGMA query_only=ON` and observing `query_only=1`.

Canonical run receipt:

- Path: `data/cex002_qualify/gate2/run_receipts/06d9a053d444b073bc6da29edb92006f99eef1ab029cd74270716aaff8872574.json`
- SHA-256: `06d9a053d444b073bc6da29edb92006f99eef1ab029cd74270716aaff8872574`
- Run ID: `05afb0f2eb4ab34d86563ed554b6136bafe983edb847426f17ab8253fb4f76bf`
- Started: `2026-08-28T04:25:21.068418+00:00`
- Ended: `2026-08-28T10:16:24.223488+00:00`
- Stop reason: `max_wall_seconds`
- Predecessor: `c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167`
- Prefix digest: `e23e497ce2fb9c3c09dce1c2510edf27ff91614f85c3dd6886eb703e260c1915`
- Semantic state digest: `bc7cc1430a1dd398003b6c3137b28291be5856df307d46d4707ac68c49b94bc2`

Reconciled counters:

```text
plan_entries=737119
attempts=27125
network_calls=27125
error_count=5425
completed=73
sidecar_facts=73
terminal_gaps=202
gap_delta=0
coinalyze_charged=0
open_coinalyze_charges=0
charge_transitions=0
byte_delta=5225416
```

The run seal and seal head both point to the canonical receipt, with high-water marks `attempt_hi=27125`, `completion_hi=73`, `sidecar_hi=73`, `charge_hi=0`, `transition_hi=0`, `run_hi=1`, and `seal_hi=0`. The receipt publication row points to the same receipt hash and body. The Coinalyze ledger reports `charged=0`; the 202 terminal gaps are typed `unsupported_mapping`. No secret value appeared in the captured output or inspected receipt/error facts.

The store contained 146 content objects totaling 5,232,324 bytes, two run-receipt files totaling 5,798 bytes, and one plan receipt of 5,007 bytes. The canonical receipt reports retained-credit adoption of 73 objects and 5,225,416 bytes, with 68 selected retained keys, 5 retained cost keys, and 0 unverified objects. The reconciled store device is `dev:64513`.

## Outcome

Review 342's single bounded acquisition completed with accepted exit 2. This record contains the execution and read-only reconciliation evidence. No verify, replay, second acquisition, repair, or retired-tree access was performed.
