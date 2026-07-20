# REVIEW-0028 - BAR-001: CHANGES REQUIRED

**Ticket:** BAR-001 - Canonical bar publisher and daily reconciliation
**Status:** CHANGES_REQUIRED - RESOLVED (superseded by REVIEW-0042_BAR-001_ACCEPTED.md)
**Next required actor:** Sr Dev - Grok Build
**Date:** 2026-07-20

## Source discovery: production unpack bug in `_extract_verified_identity`

File: `src/cryptofactors/market/bars.py`
Line: `1425`

```python
nd_id, _nq, _ = _extract_verified_identity(
    manifest=nd.manifest, receipt=nd.receipt
)
```

`_extract_verified_identity` signature and return (line 284):

```python
def _extract_verified_identity(
    *,
    manifest: DatasetManifest | None,
    receipt: DatasetPublicationReceipt | None,
) -> tuple[str, QualityStatus, tuple[OutputFileSpec, ...], str]:
```

It returns **4** values: `(dataset_id, quality_status, verified_files, manifest_sha256)`.

Line 1425 tries to unpack into **3** targets. This raises `ValueError: too many values to unpack (expected 3)` at runtime when `native_daily` is supplied.

## Impact

- `publish_canonical_bars(..., native_daily=(...), ...)` is currently broken for any non-empty native daily input
- All Jr reconciliation tests that exercise `native_daily` hit this path
- End-to-end `DatasetPublisher.publish` path is blocked when the plan includes native daily dependencies

## Required source remediation

Fix line 1425 to unpack all four returned values, e.g.:

```python
nd_id, _nq, _files, _msha = _extract_verified_identity(
    manifest=nd.manifest, receipt=nd.receipt
)
```

Or replace the trailing underscore with `_` for the fourth value if the manifest sha is intentionally discarded here.

## Disposition

BAR-001 remains `IN_PROGRESS`. Jr integration is blocked until Sr Dev ships corrected source.
