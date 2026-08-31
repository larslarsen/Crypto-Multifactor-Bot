# ADR 0031 - Post-Plan Revision Authority and Bounded ZIP Validation

- **Status:** Accepted
- **Date:** 2026-08-31
- **Amends:** ADR-0029 acquisition authority, archive validation, and terminal completion;
  ADR-0030 plan-generation replacement
- **Evidence:** `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`
  and `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`

## Context

The corrected Gate-2 generation reached the end of its frozen plan. Its authenticated head is
run-7 receipt `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`.
It contains 737,119 plan rows, 1,632,378 attempts, 685,642 completions, 736,347 Binance
sidecars, 202 typed unsupported Coinalyze gaps, seven sealed runs, 569 settled Coinalyze
charges, zero open charges, and zero unfinished runs.

Every required source family except two is complete. The exact unresolved set is:

- 50,921 `daily/metrics` objects whose current official archive bodies disagree with the
  frozen listing size and/or checksum version while their current official checksum sidecars
  are retained; and
- 354 `daily/bookTicker` cost-sample objects whose compressed bodies match the frozen listed
  size and current official checksum, but whose safe central-directory metadata declares more
  than the acquisition source's global 64 MiB uncompressed-work ceiling.

The metrics set is a provider revision after the listing snapshot, not authority to mutate the
installed plan. The book-ticker set is not a provider integrity failure. The accepted body was
discarded only because a fixed internal work limit was crossed before CRC completion.

The 64 MiB constant has no release-specific empirical authority. Read-only central-directory
inspection of the 555 completed peers proves all are ordinary single-member ZIPs. Their
compressed-to-uncompressed ratios range through 8.145989, and the largest valid uncompressed
peer is 67,095,645 bytes—only 13,219 bytes below the 67,108,864-byte cutoff. The 354 failed
objects have frozen compressed sizes from 8,932,817 through 200,457,493 bytes and total
8,661,432,243 bytes. The observed cliff is therefore the validator's constant, not a natural
archive boundary.

Changing the acquisition source changes its hash. The active SQLite authority and every
historical run receipt bind the accepted old source identity. Rewriting that authority in
place would make old receipts appear to have been created by code that did not create them.
Rewriting 50,921 immutable plan facts or silently accepting live provider metadata would also
break ADR-0029.

## Decision

### 1. Close and preserve the current generation

Receipt `8875338d...f7ab` is the terminal head of Gate-2 generation 0. No further `acquire`,
`plan`, replay, or `verify` command may run against that active generation under its current
source. Its 51,275 unresolved identities remain pending; they are not converted to gaps or
accepted as coverage.

Generation 0 remains the authority for every sealed attempt, completion, sidecar, charge,
transition, run, and receipt it owns. No row, receipt, content object, sidecar, WAL/SHM file, or
plan fact may be rewritten, deleted, relabeled, or migrated in place.

### 2. Produce a separate immutable revision candidate first

Before any state transition or raw acquisition, a standalone planner must create one exact
post-plan revision candidate. It operates outside the active `gate2` tree and performs no raw
object download.

The planner must:

1. hold the accepted acquisition lock nonblocking and prove no live writer;
2. open the generation-0 SQLite database read-only, immediately set `query_only=ON`, and bind
   the exact schema, plan identity, authority/code hashes, run-7 head, counts, zero-open-run,
   zero-open-charge, and foreign-key/integrity facts;
3. derive the pending set from exact plan/completion/gap joins and require exactly 50,921
   metrics-revision identities plus 354 book-ticker ZIP-work identities and no other pending
   Binance or Coinalyze identity;
4. rehash and parse each retained sidecar through held no-follow roots, requiring exact
   provider/key/basename identity and one current SHA-256;
5. paginate current official Binance archive listings for only the affected exact family
   prefixes, retain every request-keyed response content-addressably, and require every pending
   raw key and sidecar key exactly once without expanding economic scope;
6. bind each row's old plan size/facts, terminal error class, current listing size/metadata,
   retained sidecar content identity, and current provider checksum;
7. separately classify metrics rows as provider-revision candidates and book-ticker rows as
   unchanged-version ZIP-work candidates; a book candidate must retain the same listed size and
   provider checksum proved by generation 0;
8. report exact old/current/delta byte equations, family and message counts, listing-page
   identities, current maximum object size, and a fresh capacity projection without claiming
   acquisition or acceptance; and
9. publish a canonical compressed row manifest plus compact receipt under schema
   `cex002_gate2_revision_candidate_v1`, with deterministic semantic identity independent of
   retrieval timestamps.

Listing retrieval is bounded and resumable. A request-keyed checkpoint may reuse only a page
whose exact request identity and retained bytes rehash. An interruption may leave private
partials, but never a candidate row based on an incomplete or unauthenticated page. Resume
fetches only missing pages. No caller-selected family, key, symbol, or date filter exists.

The candidate is evidence for a later reviewer decision. It is not authority to modify the
active plan, retire generation 0, download raw objects, or accept a revision.

### 3. Replace the global ZIP ceiling with two bounded work controls

Future corrected acquisition uses the actual checksum-verified compressed file size and the
central directory's exact sum of member `file_size` values. Before member decompression, require:

```text
relative_ceiling = compressed_bytes * 16
work_ceiling = min(4 GiB, max(64 MiB, relative_ceiling))
declared_uncompressed_bytes <= work_ceiling
```

The factor 16 is greater than 1.96 times the maximum 8.145989 ratio observed across all 555
completed book-ticker peers. The 4 GiB absolute ceiling bounds any single CRC-validation job,
while the ratio bound prevents a large compressed object from receiving an unbounded expansion
allowance. The 64 MiB floor preserves the existing absolute bound for small ordinary ZIPs.

This is a streaming validation-work allowance, not normalized storage sizing and not permission
to extract archives. The existing 256-member maximum, unsafe/backslash/drive/traversal path
refusal, duplicate-member refusal, non-regular/symlink refusal, non-empty requirement,
compression-method handling, CRC proof, private-file cleanup, listed compressed-size check, and
provider-checksum proof remain mandatory.

The candidate receipt binds this exact policy and reports the per-object work ceiling from the
current listed compressed size. A later acquisition source must test the lower/equal/upper
boundaries, ratio and absolute clamps, malformed central-directory sizes, member count, and CRC
failure without allocating or extracting the declared expansion.

### 4. Use a linked replacement generation; never rewrite code authority

After the revision candidate, corrected source/tests, transition tool, and storage projection
are separately accepted, generation 0 will be preserved by one reviewed same-device atomic
rename to:

`data/cex002_qualify/gate2_generations/8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`

The destination must be absent and no-replace. The transition inventory binds every file type,
device, size, and hash required to re-prove the old state. Interruption before the rename leaves
generation 0 active; interruption after it leaves the active name absent. Neither condition
permits a second uncontrolled rename or partial new plan.

A new active generation is then built from an absent `gate2` path. It has:

- a new policy/source identity and new semantic plan identity;
- the same separately reported economic-scope identity and exact 737,119 logical rows;
- one immutable generation link binding the complete generation-0 authority, plan receipt,
  run-7 head, transition inventory, revision candidate, and ADR/review identities;
- inherited completion/sidecar facts which reference the preserved generation-0 content roots
  through explicit generation IDs and held no-follow descriptors rather than copying bytes,
  creating 1.4 million hard links, or pretending the bytes were acquired again;
- exact revision-overlay facts for only the 50,921 metrics identities; and
- the revised ZIP work policy for only validation behavior, without changing any book-ticker
  economic key or current provider checksum.

Historical receipts remain validated against their historical code identity. New receipts are
validated against the new generation's code identity. The generation link joins the chains; no
receipt claims a code hash retroactively.

### 5. Revised provider facts are fixed before resumed raw acquisition

The new plan may use only current sizes and sidecar checksums from the accepted revision
candidate. It cannot discover, select, or silently install another live revision while
acquiring. If a provider key, listing size, or checksum changes again, acquisition stops on a
new typed revision conflict for reviewer disposition.

Terminal reconciliation separately reports original generation-0 planned bytes, accepted
revision bytes, signed deltas, inherited physical bytes, new physical bytes, and unique
cross-generation content. Positive revision deltas and remaining book-ticker bytes are included
in a fresh same-device capacity attestation before transition or acquisition.

### 6. Completion remains gated

After a linked replacement plan is accepted, a later bounded acquisition may fetch only the
51,275 still-pending raw identities. A successful second replay must make zero network requests.
Only then may the offline verifier stream and reconcile both generations and publish a terminal
manifest/receipt.

Gate 2 remains `IN_PROGRESS` until all 736,347 Binance identities are checksum-verified under
their exact accepted generation facts or have a separately reviewer-accepted honest source
outcome, all 570 Coinalyze receipts and 202 typed gaps reconcile, both generations authenticate,
and the replay and terminal verifier pass. This ADR does not authorize normalization or a later
gate.

## Consequences

- The valid 685,642 completions and all settled Coinalyze evidence remain reusable without
  weakening or rewriting their authority.
- Provider revisions become explicit versioned facts rather than mutable plan edits.
- Legitimate large cost-sample ZIPs can be validated under a measured, finite streaming-work
  bound while ZIP-bomb defenses remain fail closed.
- A listing-only candidate round and a later generation transition add review steps, but avoid
  redownloading completed coverage or accepting unverifiable live drift.
- No current data is deleted, no paid source is introduced, and next-ticket/model work remains
  unauthorized.
