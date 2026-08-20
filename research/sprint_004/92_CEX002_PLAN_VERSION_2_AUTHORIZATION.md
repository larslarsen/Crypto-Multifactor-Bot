# CEX-002 Plan Version 2 Authorization

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed commit: `956322457c11840d2a2344063e609dbe3991616a`

Reviewed execution record:
`research/sprint_004/91_CEX002_GATE1_CORRECTED_EXECUTION.md`

## Decision

**ACCEPT THE COMMAND RESULTS AND EXIT-1 STOP. AUTHORIZE ONE EXACT PLAN-VERSION
MIGRATION AND THE CORRECTED TWO-RUN EXECUTION.**

Hermes verified the accepted hashes; 148 focused CEX-002 tests, 11 atomic-download tests,
Ruff, repository control, and the committed whitespace check passed. The first real
invocation captured raw qualifier exit status 1 and correctly stopped before a second run
because the accepted production hash changed the immutable `code_config_digest`.

This is expected fail-closed behavior, not permission to discard the plan lock. Review 90
changed only the stable storage incident text and Coinalyze provider-symbol mapping.
Neither change selects samples, changes the inventory/universe, restores budget, or
changes retained evidence. Plan version 2 is therefore authorized to preserve the exact
version-1 plan, plan digest, retained snapshot, and budget snapshot and change only the
reviewed code/config identity.

## Record Correction

Record 91 incorrectly describes the lock as 100 entries plus four blocked entries with a
100-object retained snapshot. Direct read-only inspection of the exact locked file proves:

- file SHA-256: `45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf`;
- plan version: 1;
- plan digest: `d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`;
- history versions: `[0]`;
- entries: 146 (`reuse_retained=86`, `alias=14`, `blocked=46`);
- `plan.blocked`: 46;
- retained snapshot identities: 118;
- unique retained plan objects: 86;
- unique new objects and new download bytes: 0; and
- locked code/config digest:
  `9845375eb2a5f0f83917fc47fd2b25a5463c2ad9979ffb06f183d27f452fe663`.

The invocation did perform the listing/evidence computations needed to reach the plan
comparison; it stopped before plan execution, sample transfer, Coinalyze qualification,
storage/report construction, or report publication. These corrections supersede the
contrary counts and "before listing/membership" statement in record 91. They do not alter
Hermes's correct exit-1 stop.

## One-Time Migration

Jr Dev - Hermes may execute the following command once from repository root. This is the
entire plan-mutation authorization. No public relock flag, plan reselection, manual JSON
edit, deletion, rename, or reconstruction is authorized.

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
expected_new_code = "3323116bef5558eb2da57f67cb8edb15267cbb55f06ebe012383431a7f580148"
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
lock.lock_plan(
    plan=SamplePlan.from_dict(old_plan),
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
before any real run and leaves the atomic lock file at its last valid state.

## Corrected Execution

After the migration passes, run the qualifier twice against the same preserved store and
progress path. Write the first report to `/tmp/cex002_gate1_plan2_first.json` and the
second to `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`. Load `.env` only
into the environment. Capture and report the actual qualifier exit status immediately
after each invocation. Exit 1 stops. Exit 0 or 2 permits the second run; the two statuses
must agree.

After both runs, require
`drop_identity_volatility(first) == drop_identity_volatility(second)`. Record the exact
Coinalyze qualification/support result, membership classes, product matrix, plan/history
identities, ledger, listing/sample transfer counts, physical storage values, both raw exit
statuses, and report hashes in
`research/sprint_004/93_CEX002_GATE1_PLAN2_EXECUTION.md`.

Hermes may update only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/93_CEX002_GATE1_PLAN2_EXECUTION.md`; and
- `tickets/CEX-002.md`.

Hermes commits and pushes only those four paths, establishes `HEAD == origin/main`, sets
the next actor to the reviewer, and stops. It performs no source/test edit, acquisition,
Gate 2, catalog mutation, Nautilus integration, other-ticket work, or Harmonic Trader
work.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. This authorization does not accept the source
matrix, reclassify the 63 unresolved candidates, resolve liquidation coverage, restore
legacy budget, approve the approximately 8.47 TB storage shortfall, reduce the universe,
omit derivatives fields, or authorize a price-only substitute. Next ticket remains
`NONE`.
