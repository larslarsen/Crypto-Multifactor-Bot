# CEX-002 Claude Storage-Sizing Residual Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `REJECTED`; one narrow Sr Dev residual correction authorized  
**Gate 1:** Remains accepted  
**Gate 2:** Not accepted; sizing execution and bulk acquisition remain unauthorized

## Reviewed drop

The reviewer inspected Claude's review-182 correction at these uncommitted identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `73b3e97c2f553ed147a1dcd6c54171fe6e9a1f294667dbb90ae5255269c562e0` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `2695ef73cc3c3438a3efc797706ff5038dde1701081d88cea8050f32d5a8b436` |

The test path contains 36 `def test_` functions. Scope remains correct. The reviewer used
static source/test inspection and read-only accepted-artifact and filesystem inspection.
The reviewer ran no test, linter, control, sizing, network, acquisition, or data-mutation
command.

This correction successfully separates the 73 consumable acquisition-credit objects from
the 96 coefficient samples and places that reconciliation before envelope publication. It
also corrects production largest-partition fan-out, integer epoch conversion, projected
catalog receipt count, exact fixed-point receipt length, and whole-file envelope copying.
Four blocking residuals remain.

## Findings

### 1. Critical - Coinalyze retained credit is still synthetic rather than exact

The accepted retained liquidation evidence is one 40,826-byte response whose single query
contains both `BTCUSDT_PERP.A` and `ETHUSDT_PERP.A`. The accepted future-market inventory
is one retained 1,449,633-byte response. `project_coinalyze()` omits the inventory bytes
from both gross and retained raw, claims two retained liquidation receipts because the
response contains two symbols, and derives retained bytes as retained points times a
projected point charge plus two copies of the full two-symbol framing charge
(`binance_usdm_harmonic_sizing.py:1910-1956`). That is neither retained response identity
nor its exact byte size.

The test at lines 1241-1262 enshrines the same error by requiring retained receipt count to
equal retained symbol count. It checks only an internally constructed subtraction, not the
accepted one-request/two-symbol evidence shape required by review 182.

Keep the conservative 569 one-symbol liquidation gross projection, but report its parts
without changing evidence identity. Gross required raw includes the exact inventory
receipt plus projected liquidation receipts. Retained coverage includes exactly one
inventory receipt at 1,449,633 bytes and exactly one liquidation receipt at 40,826 bytes;
the latter covers two symbols and only its proved unique in-lifecycle daily points. Parse
and validate point timestamps, uniqueness, symbol, query interval, lifecycle, and cutoff
before credit. Then derive new raw from gross minus those exact reusable bytes. Report
receipt count, covered-symbol count, point count, and byte count as separate fields.

### 2. Critical - changed-capacity rerun still collides and prior validation is partial

`revalidate_prior_receipt()` compares the prior `total_future_storage_bytes` with the
newly measured expected total (`binance_usdm_harmonic_sizing.py:2024-2071`). That total
contains the newly derived one-fifth reserve. The current destination has 165,667,520,512
available bytes, above the 80 GiB reserve-floor threshold. The test at lines 1095-1114
changes available space by 1,000,000 bytes, so it changes the reserve and total, causes
revalidation to return `None`, and then collides with the already occupied fixed receipt.
The claimed identical rerun cannot pass on this filesystem.

The validator also does not validate or compare `cohort`, `measurements`, `filesystem`,
`blockers`, `storage_preflight_state`, `authorization`, or the receipt's declared byte
length. Canonical JSON alone is not an immutable identity: an altered mapping can be
canonically reserialized. Such a prior can retain a forged capacity state while passing
the current partial checks.

Separate stable current reproof from volatile sizing-time observations. Re-prove all
current authority, code, cohort, measurement/envelope, projection, and count identities;
then validate every stored prior field and all internal equations, including exact
canonical length, filesystem device/pre/post/evidence values, frozen reserve, capacity
sum, blockers, state, and authorization. Do not compare a newly observed free-space value
or newly derived reserve with the already frozen valid receipt. Return the exact prior
only after both checks pass. Add changed-space tests above the 80 GiB threshold and
parameterized tampering tests for every previously omitted section.

### 3. High - an older partition assertion contradicts corrected production

Production now correctly selects one logical file before fan-out at lines 1386-1406, and
the new test at lines 1270-1316 expects that behavior. The older test at line 821 still
requires `ceil_div(...) * 2` for `largest_partition_bytes`. For its fixture, production
returns 750 and the assertion requires 1,500. Correct the stale assertion to the one-file
value while preserving multiplicity in projected total and partition count.

### 4. High - publication no-follow checks remain vulnerable to path races

Publication checks path components with `Path.is_symlink()` and later reopens them by
pathname (`binance_usdm_harmonic_sizing.py:2082-2195`). A parent can change after the
check; the existing-envelope path hashes by ordinary pathname after its check; and prior
receipt revalidation uses `is_file()` plus `read_bytes()` with no no-follow descriptor.
The new tests cover only pre-existing symlinks and regular pre-existing targets. They do
not exercise a symlink swap or an actual collision race.

Anchor publication and prior-receipt reads to no-follow directory/file descriptors so the
validated directory is the directory used for temporary creation, link, comparison,
fsync, and cleanup. Hash existing envelope targets through `O_NOFOLLOW`; translate a
racing symlink into `SizingError`; and never follow the fixed receipt during revalidation.
Add injected symlink-swap and identical/nonidentical racing-target tests, and verify file
plus directory fsync and temporary cleanup on every branch.

## Decision and correction boundary

The drop is rejected. Sr Dev - Claude Build using Claude Opus 5 is authorized only for a
narrow correction of these four findings in the same three untracked paths. Preserve all
accepted review-181 and review-182 corrections. Do not redesign the sizing policy, reduce
coverage, change the fixed target, or weaken tests.

Claude runs no test, linter, control, Git, network, sizing, acquisition, or data command;
edits no record, data, or path outside the exact three-path drop; returns the three exact
SHA-256 hashes and test-function count; and stops for reviewer inspection.

Hermes remains unauthorized. No integration, sizing execution, Gate 2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized.
