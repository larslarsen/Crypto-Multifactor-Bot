# ADR 0039 — CEX-002 clean Nautilus consumer verification

Status: Accepted
Ticket: CEX-002
Reviewer: Lead Quantitative Finance Researcher/Engineer
Extends: ADR-0037 preparation/consumer-proof boundary; ADR-0038 schema registries

## Decision

Add an external research checker for the accepted prepared candidate. Use a fresh
NautilusTrader catalog and genuine registered custom-data write/query operations
to round-trip every logical table row. A lossless registered row envelope preserves
all original typed fields, nulls, exact decimals and timestamps. Reading the source
with Arrow alone, storing only an input digest/path, or transporting an opaque
whole-file object does not establish catalog readback of the rows.

Also round-trip the bar product's OHLC/base-volume projection as native Nautilus Bar
objects. Preserve the full bar row in the lossless custom envelope; native Bar does
not contain every lineage, volume or source field. Projection conversion must be
exact and fail on unrepresentable values, never round or impute them. A transport
identifier derived from the venue-native symbol does not create a canonical mapping.

Nautilus initialization clocks may use the actual recorded checker observation time.
For non-temporal custom components, a required envelope clock may likewise identify
the actual validation observation. Mark these clocks as validation transport only;
they are not source events, historical availability or trading inputs. Native bars
use their actual source close_time for ts_event with exact millisecond-to-nanosecond
conversion. Original times and unknown source availability remain unchanged in the
lossless payload, schema and proof. Never copy event time into unknown availability.
The checker is an offline data validation tool and exposes no strategy-ready API.

Process bounded batches and compare values returned through Nautilus, reassembling
source order with explicit authenticated row ordinals where catalog ordering differs.
Reject missing, duplicate, substituted or changed returned rows. The strict v1 proof
and its existing canonical typed-row digest remain unchanged. Codecs may share pure
canonical token encoding; source and returned bytes must originate from separate
source-read and Nautilus-readback paths. Metadata retains byte identity and zero rows.

Keep scratch catalogs within a separate, fresh owned root and a 256 MiB disk cap.
Successful batches may remove only their own authenticated scratch files after
readback. Failure preserves bounded partial output. Final proof publication is
content-addressed, no-clobber and atomic under the existing bundle .proofs namespace;
no successful proof is exposed until every required component passes. Account for
scratch, staged proof and final metadata without double-counting a rename or silently
omitting an external proof copy. Keep the release budget and operating reserve fixed.

This decision changes no accepted product, source authority, catalog schema, economic
meaning, proof schema, digest contract or resolver visibility. It authorizes no
consumer execution, catalog admission, strategy, backtest or model by itself.
