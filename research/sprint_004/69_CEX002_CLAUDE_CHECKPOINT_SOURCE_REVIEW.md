# CEX-002 Claude Checkpoint-Correction Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP FOR ONE RESIDUAL INTEGRITY DEFECT**

## Reviewed identities

Committed control-plane base:
`HEAD == origin/main == b484d2f9f56ef408df2dcf8f17169011368b85fb`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `8b0dc4a327413a7ecf94b80f28139c11eb67a88eb1d16473cb41704db31abef1` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `596e1af1738b5badf59f2c46dc1271c0a84428f73747a11e53f07232476dd960` |

Focused Ruff and in-memory compilation pass. Reviewer direct probes confirm that the
review-68 cross-request page substitution, provider-checksum substitution, malformed
checkpoint, and unique-object budget failures now fail closed or reconcile exactly. The
retry journal, single retry owner, and injected abort/resume test source are present. No
pytest or network command was run by the reviewer.

## Residual blocking finding

The completed-sample resume path still accepts a sample using only the sample checkpoint
and retained raw object. It proves that `sha256`, `provider_checksum`, and the rehashed raw
bytes agree, but it neither requires nor rehashes the retained provider-checksum sidecar.
Network-acquired sample checkpoints do not record the sidecar's content-addressed path or
blob digest at all.

A reviewer direct probe completed a sample with an in-memory source, confirmed that no
provider sidecar existed in the store, and reran successfully with
`reused_samples > 0`. This violates review 68's explicit requirement that raw digest,
provider checksum, rehashed retained sidecar, sidecar content address, object identity,
and retained raw bytes agree **before reuse or recovery**.

The recovery path correctly rehashes an available sidecar, but after it writes a sample
checkpoint, later resume no longer re-proves that sidecar. A checkpoint alone cannot be
promoted to provider authority.

## Surgical correction authorization

Sr Dev — Claude Build using Claude Opus 5 is authorized to edit only the same three
reviewed paths. Preserve every accepted review-68 correction and make only this change:

1. Persist every checksum sidecar atomically and content-addressably, including the
   in-memory/test-index path, before a sample checkpoint can become complete.
2. Store the checksum sidecar's cache-local content path and blob SHA-256 in every sample
   checkpoint, whether the sidecar was newly fetched or recovered.
3. On every completed-sample resume and retained recovery, rehash the sidecar, require its
   path to equal its cache-local content address, parse exactly one provider checksum and
   filename identity, require that filename to equal the sampled object's basename, and
   require the provider checksum to equal both the checkpoint/raw digest and the rehashed
   retained raw object.
4. Treat a missing, malformed, substituted, relocated, or tampered sidecar as
   `ResumeIntegrityError`; never silently redownload or reuse the sample.
5. Add focused deterministic test source proving that completed-sample resume fails closed
   for a missing sidecar and for a sidecar whose checkpoint path/digest/filename/content is
   substituted, while an intact sidecar resumes without a sample or sidecar network fetch.

The six retained real samples and 263 listing/checksum blobs must remain untouched. Claude
performs no pytest, network run, integration, repository-record edit, Git operation,
commit, push, purchase, Gate 2 work, or model work. It stops for fresh reviewer source
inspection with exact hashes.

## Reviewer publication policy applied

At the owner's request, repository governance now permits the reviewer to commit and push
small reviewer-authored governance/review publications directly. That exception is
confined to enumerated record paths and never includes developer source/test integration,
test execution, acceptance commands, or data mutation. Hermes retains those duties.

This review, the matching current-task/ticket edits, `AGENTS.md`, and
`docs/engineering/DEVELOPMENT_ROLES.md` are the exact reviewer-publication set. The
rejected three-path source/test drop and all unrelated dirty paths are excluded. Once this
record is on `origin/main`, the Claude authorization above is active without an ephemeral
prompt.

## Gate decision

Gate 1 remains `IN_PROGRESS`. Jr integration and real-source execution remain
unauthorized. Gate 2 and harmonic-model development remain unauthorized. There is no
partial PASS.
