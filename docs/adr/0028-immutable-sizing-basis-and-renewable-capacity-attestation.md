# ADR 0028 - Immutable Sizing Basis and Renewable Capacity Attestation

- **Status:** Accepted
- **Date:** 2026-08-23
- **Amends:** ADR-0027 section 6
- **Evidence:** `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`,
  `research/sprint_004/277_CEX002_V3_ORDERING_INTEGRATION_AND_EXECUTION.md`, and
  `research/sprint_004/278_CEX002_V3_BLOCKED_MEASUREMENT_AND_CAPACITY_ATTESTATION_ARCHITECTURE.md`

## Context

The accepted v3 sizing execution produced immutable receipt 258 at SHA-256
`3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`.
Its five observation-independent components total 139,577,980,018 bytes. With the frozen
29,690,701,415-byte reserve derived from its filesystem observation, its complete future
requirement is 169,268,681,433 bytes against 148,382,449,709 post-publication available
bytes. The receipt is validly blocked.

V3 idempotence deliberately freezes observation-time filesystem, reserve, blocker, and
state facts. A later run re-proves and returns receipt 258 even if free space changes. This
is correct for immutable measurement evidence but means storage cleanup cannot be proved
by rerunning the v3 receipt target. Overwriting or deleting receipt 258 would destroy the
accepted audit trail; regenerating all 153 typed witnesses would add cost without changing
the stable storage basis.

## Decision

### 1. Receipt 258 is the immutable sizing basis

Receipt 258 and every v3 envelope remain immutable. The accepted basis is bound by exact
receipt SHA-256, byte length, schema, policy identity, code identity, destination, device,
five stable capacity components, reserve rule, and capacity equation. No attestation may
change, omit, or recompute a stable component from another source.

The stable basis excludes only `operating_reserve_bytes` and
`total_future_storage_bytes`, because those are derived from a specific free-space
observation. The accepted stable sum is exactly 139,577,980,018 bytes.

### 2. Capacity observations are separate immutable attestations

After storage changes, a capacity-attestation command reads and revalidates exact receipt
258, measures the same destination device, derives the operating reserve from current
pre-write availability using the unchanged rule `max(16 GiB, ceil(available / 5))`, and
publishes a small immutable attestation. It computes:

```text
current total requirement = accepted stable basis + current operating reserve
sufficient iff current total requirement <= post-attestation available bytes
```

The attestation binds the v3 receipt identity, stable-projection identity, destination and
device, attestation source/CLI identity, measurement time, pre-write and post-publication
availability, its own exact byte length, reserve, total, state, blockers, and a statement
that it authorizes no acquisition and accepts no gate.

### 3. Publication is append-only and transactional

Each reviewer-authorized observation has an explicit new output path. Publication refuses
an existing file or symlink, uses same-directory no-follow temporary creation, exact
self-length accounting, flush/fsync, atomic no-replace publication, and directory fsync.
No mutable `latest` pointer is authoritative. A failed or blocked attestation remains
immutable evidence; a later observation uses a new path.

The command has no network, credential, coefficient, reserve, component, device, or state
override. The store, accepted v3 receipt, and output path are the only locations; the
reviewer fixes them for each invocation. It never reads or writes v1/v2/v3 envelopes and
never rewrites receipt 258.

### 4. Gate boundary

A sufficient attestation is measurement evidence only. Gate 2 remains blocked until the
reviewer accepts an exact sufficient attestation and separately authorizes acquisition.
A stale or blocked attestation cannot be combined with a later `df` observation. The
active other-project download must finish before the capacity observation intended for
Gate-2 review.

## Consequences

- The full universe, products, raw projection, normalized bound, manifests, temporary
  bound, and reserve rule remain unchanged.
- Storage cleanup can be measured without deleting accepted evidence or rerunning 153
  Parquet witnesses.
- Every capacity observation is durable, self-contained, and reviewable.
- At the receipt-258 observation, at least 26,107,789,655 additional free bytes were
  required because freeing space also increases the one-fifth operating reserve.
- Storage deletion or movement remains an owner-authorized data action; no cleanup is
  authorized by this ADR.
