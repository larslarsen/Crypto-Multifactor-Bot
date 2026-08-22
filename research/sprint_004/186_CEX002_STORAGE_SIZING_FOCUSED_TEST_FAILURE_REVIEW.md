# CEX-002 Storage-Sizing Focused Test Failure Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `FAILED_TEST_SOURCE`; one mechanical Spark correction authorized  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; no sizing invocation occurred

## Reviewed execution

Hermes correctly integrated review 184 at commit
`e4ae0f8a47edc5ced4b7625e9547396fb5c4634f`, pushed it, and stopped on the first
nonzero command. `HEAD == origin/main` at that commit. Its exact six-path commit scope is
correct and excludes every unrelated dirty path.

The frozen sizing identities remain:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `e7127f9724ce046233979ec29d43035ff5358c213beee2b9cd22b0e841ee323a` |

The focused command exited status 1 after 3 seconds with 16 failures and 37 setup errors.
Hermes consequently ran no lint, control, sizing, network, or data-mutation command.
Receipt 180 and the sizing-envelope tree remain absent.

## Findings

### 1. High - the shared fixture calls a nonexistent `gzip.open` argument

At test line 196, `gzip.open(detail_path, "wb", compresslevel=9, mtime=0)` raises
`TypeError` because `gzip.open()` has no `mtime` parameter. This occurs before the shared
`accepted` fixture can yield and causes all 37 setup errors. Deterministic gzip output
must use `gzip.GzipFile(..., mtime=0)` instead.

### 2. High - the first direct test invalidates every imported exception assertion

At test lines 459-462, `importlib.reload(sizing)` mutates the module namespace and creates
a new `sizing.SizingError` class. The test module's earlier
`from ... import SizingError` binding still refers to the old class. Production helpers
then raise the new class, so every later `pytest.raises(SizingError)` fails to catch the
expected exception. This explains the reported corrupt-archive, rational/reserve, and
publication failures; their bodies already place the calls inside appropriate
`pytest.raises` contexts.

The literal-pin test must inspect `sizing` without reloading it. Pytest's `monkeypatch`
fixture already restores every constant changed by the shared fixture, so reload is both
unnecessary and destructive.

No production or CLI failure was reached or proved. Review 184's source acceptance remains
in force.

## Spark correction boundary

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized to edit
only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`:

1. replace the invalid deterministic gzip writer with `gzip.GzipFile` using
   `compresslevel=9` and `mtime=0`;
2. remove `importlib.reload(sizing)` and make the literal-pin assertions read the existing
   `sizing` module directly; and
3. preserve all test cases and exactly 44 `def test_` functions.

Spark changes no production/CLI byte, adds no test, alters no assertion semantics outside
those two mechanical fixes, runs no test, linter, control, Git, network, sizing, or data
command, edits no repository record, and returns the corrected test SHA-256. Stop for
reviewer source inspection.

Hermes is not yet authorized to restart. No sizing invocation, Gate-2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid-source, reduced-scope, or next-ticket work is authorized. Next ticket
remains `NONE`.
