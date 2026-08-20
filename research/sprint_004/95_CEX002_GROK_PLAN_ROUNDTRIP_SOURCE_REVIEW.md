# CEX-002 Grok Plan Round-Trip Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Base commit: `25cf91520d10854357eb580531df40f7fe8b7bfe`

## Decision

**ACCEPT THE TWO-PATH SOURCE DROP FOR INTEGRATION AND REAUTHORIZE THE EXACT PLAN-2
MIGRATION AFTER FOCUSED COMMANDS PASS.**

Accepted identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `733e7589b705d9b584269e3e8df06fdade19d98b6f18e3d5b65760009eeb87d3` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `a8e41aae63d800bdca76f6b1321e3c51fb47211e7c5a2a3692e1089f50021a6d` |

This is source acceptance, not Gate 1 data acceptance. The reviewer has not executed tests,
acceptance commands, a plan migration, or a real source run.

## Inspection

`SamplePlan.to_dict()` now replaces each entry's internal tuple-valued `products` with a
JSON-native list. `SamplePlan.from_dict()` still restores an internal tuple. No selection,
validation, plan-content, membership, budget, ledger, storage, Coinalyze, checkpoint, or
transfer logic changed.

The new focused test includes a multi-product download entry and blocked-plan evidence.
It requires list-shaped serialized products, JSON-native stability, exact persisted-plan
round trip, unchanged plan-content digest, retained internal tuple type, and plan
validation. The accumulated source remains present at 3,845 lines and 140 unique test
functions.

Because JSON serializes a tuple and list identically, the existing version-1 plan digest
remains `d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`.
The accepted source hash changes only the plan code/config digest to
`0ca6e4f1d0bbdb58e21c1b374a9616ab13593584c8006ceedbf56c3de9220a99`.

## Integration Commands

At the owner's standing direction, the reviewer may integrate the accepted two-path drop
with this review. Jr Dev - Hermes then verifies both accepted hashes,
`HEAD == origin/main`, and the unchanged version-1 lock SHA-256
`45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf`.

Hermes runs in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Any failure stops before plan mutation. Do not substitute `-k` or edit source/test/data.

## One-Time Plan-2 Migration

If all five commands pass, Hermes executes this block once from repository root:

```bash
.venv/bin/python - <<'PY'
import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    PlanInputs,
    SamplePlan,
    SamplePlanLock,
    plan_code_config_digest,
)

path = Path("data/cex002_qualify/cex002_sample_plan_lock.json")
expected_file = "45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf"
expected_plan = "d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1"
expected_old_code = "9845375eb2a5f0f83917fc47fd2b25a5463c2ad9979ffb06f183d27f452fe663"
expected_new_code = "0ca6e4f1d0bbdb58e21c1b374a9616ab13593584c8006ceedbf56c3de9220a99"
assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_file
lock = SamplePlanLock.load(path)
assert lock is not None
assert lock.plan_version == 1
assert lock.plan_digest == expected_plan
assert [row.get("plan_version") for row in lock.history] == [0]
assert lock.inputs["code_config_digest"] == expected_old_code
assert len(lock.plan["entries"]) == 146
assert len(lock.plan["blocked"]) == 46
assert len(lock.retained_snapshot) == 118
assert lock.plan["unique_retained_objects"] == 86
assert lock.plan["unique_new_objects"] == 0
assert lock.plan["new_download_bytes"] == 0
old_inputs = copy.deepcopy(lock.inputs)
old_plan = copy.deepcopy(lock.plan)
old_snapshot = copy.deepcopy(lock.retained_snapshot)
old_budget = copy.deepcopy(lock.budget_snapshot)
new_code = plan_code_config_digest(
    budget_bytes=int(old_budget["budget_bytes"]),
    max_object_bytes=int(old_budget["max_object_bytes"]),
)
assert new_code == expected_new_code
new_input_values = dict(old_inputs)
new_input_values["code_config_digest"] = new_code
new_inputs = PlanInputs(**new_input_values)
assert new_inputs.differences(old_inputs) == ("code_config_digest",)
round_trip = SamplePlan.from_dict(old_plan)
assert round_trip.to_dict() == old_plan
lock.lock_plan(
    plan=round_trip,
    inputs=new_inputs,
    locked_at=datetime.now(timezone.utc).isoformat(),
    retained_snapshot=old_snapshot,
    budget_snapshot=old_budget,
)
assert lock.plan_version == 2
assert lock.plan_digest == expected_plan
assert lock.plan == old_plan
assert lock.retained_snapshot == old_snapshot
assert lock.budget_snapshot == old_budget
assert [row.get("plan_version") for row in lock.history] == [0, 1]
assert lock.history[-1]["inputs"] == old_inputs
assert lock.history[-1]["plan"] == old_plan
assert lock.history[-1]["plan_digest"] == expected_plan
lock.flush()
reloaded = SamplePlanLock.load(path)
assert reloaded is not None
assert reloaded.plan_version == 2
assert reloaded.plan_digest == expected_plan
assert reloaded.plan == old_plan
assert reloaded.retained_snapshot == old_snapshot
assert reloaded.budget_snapshot == old_budget
assert reloaded.inputs == new_inputs.to_dict()
assert [row.get("plan_version") for row in reloaded.history] == [0, 1]
print("CEX-002 plan version 2 authorization: PASS")
print("plan_digest=" + reloaded.plan_digest)
print("code_config_digest=" + reloaded.inputs["code_config_digest"])
print("lock_sha256=" + hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

Every assertion must pass. Record the emitted post-migration lock SHA-256. A failure stops
before any real run. No public relock flag, plan reselection, manual JSON edit, deletion,
rename, replacement, or reconstruction is authorized.

## Corrected Execution

After migration passes, run the qualifier twice against the same preserved store and
progress path. Write the first report to `/tmp/cex002_gate1_plan2_roundtrip_first.json`
and the second to `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`. Load
`.env` only into the environment. Capture the actual qualifier exit status immediately
after each invocation. Exit 1 stops. Exit 0 or 2 permits the second run; both statuses
must agree.

After both runs, require
`drop_identity_volatility(first) == drop_identity_volatility(second)`. Record the exact
Coinalyze qualification/support result, membership classes, product matrix, plan/history
identities, ledger, listing/sample transfer counts, physical storage values, raw exit
statuses, and report hashes in
`research/sprint_004/96_CEX002_GATE1_PLAN2_EXECUTION.md`.

Hermes may update only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/96_CEX002_GATE1_PLAN2_EXECUTION.md`; and
- `tickets/CEX-002.md`.

Hermes commits and pushes only those four paths, establishes `HEAD == origin/main`, sets
the next actor to the reviewer, and stops. It performs no source/test edit, acquisition,
Gate 2, catalog mutation, Nautilus integration, other-ticket work, or Harmonic Trader
work.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. This authorization does not accept the source
matrix, reclassify unresolved candidates, resolve liquidation coverage, restore legacy
budget, approve the storage shortfall, reduce the universe, omit derivatives fields, or
authorize a price-only substitute. Next ticket remains `NONE`.
