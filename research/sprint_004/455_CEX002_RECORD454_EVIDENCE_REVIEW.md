# CEX-002 Review 455 - Record 454 Evidence Review

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept terminal success facts provisionally; reject the claimed full reconciliation
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Plain-language decision

The corrected conversion finished and both completion descriptors exist with the expected row and
gap totals. No rerun, redownload, cleanup, or code change is needed. The remaining blocker is the
quality of Record 454's proof: it says all 45,266 descriptor-referenced partitions were reconciled,
but its detailed evidence says only one partition per product was checked. Hermes must now perform
the promised read-only full verification and publish the exact results before the reviewer accepts
the two completed products.

## Accepted terminal facts

Review 455 accepts these facts from Record 454:

- Hermes integrated exactly the accepted source and test at commit
  `5a3bd73e10fc208bdb43b5334b097a264d2dbb9b` and pushed it;
- the focused pytest passed all 54 cases, ruff passed, and repository control passed;
- one corrected foreground resume exited zero after about 1,855 seconds;
- the accepted generation-0 authority was unchanged and nothing was downloaded;
- the bar completion file is
  `data/.cex002_bar_1h/.complete/3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7.json`;
- the trade-flow completion file is
  `data/.cex002_trade_flow_1h/.complete/a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a.json`;
- each descriptor names 22,633 partitions and the accepted source, schema, invariant, row, and gap
  totals; and
- both staging directories were empty at terminal observation.

Read-only reviewer inspection confirms that exactly those two completion filenames are present and
their parsed top-level facts match Record 454. This is not yet full artifact acceptance.

## Record 454 defects

Record 454 is insufficient as final reconciliation evidence for three exact reasons:

1. Its section 1 says `HEAD == origin/main == 5a3bd73e...` "before the integration commit," but
   `5a3bd73e...` is the integration commit. The actual pre-integration review publication was
   `f34c550b9d7ec0cc1c44c590d20e3b073b551bcd`; `5a3bd73e...` was the post-integration head.
2. Its preflight and terminal available-space fields contain literal `?` digits. They appear to be
   default-`df` KiB counts, not exact byte counts, and must not be presented as exact bytes. The
   exact historical values cannot be reconstructed from truncated text; Record 456 must say that
   plainly rather than guess. Review 453 already recorded an exact 35,803,824,128-byte reviewer
   observation before Hermes began. Capacity did not stop the successful run.
3. The authorization required complete descriptor-referenced Parquet, lineage, schema, and digest
   reconciliation. Record 454 labels this reconciliation "spot-checked" and identifies only
   `0GUSDT/2025-09` as a sampled partition. A one-partition sample cannot support its broader claim
   that every referenced hash matches.

The final physical file counts in Record 454 also mix the descriptor's current artifacts with older
unreferenced content-addressed files. Record 456 must distinguish referenced from unreferenced
files instead of calling every physical Parquet a product partition.

## Hermes read-only correction authorization

Jr Dev - Hermes is authorized only for one read-only full audit of the two exact completion
descriptors and publication of Record 456. It may use deterministic local read-only commands but
must not run the normalizer or any test, edit source/test/CLI, change data, delete or clean output,
download, use the network, or read/invoke `run_continuation_runner.sh`.

For each product, Hermes must verify and record:

1. the completion file is the sole file in `.complete`, is a regular non-symlink file, and its full
   SHA-256 equals both its filename and the accepted completion identity;
2. the descriptor has exactly 22,633 unique `(native_symbol, utc_month)` partition entries, unique
   canonical relative Parquet and lineage paths, the accepted product/schema/normalizer/source
   identities, and the exact accepted row, invariant, exclusion, and gap totals;
3. for all 22,633 entries, both referenced files are regular non-symlink files beneath the held
   product root; each complete file SHA-256 equals the descriptor value and its content-addressed
   filename; each Parquet schema equals the accepted schema and its metadata row count equals the
   descriptor row count; and each lineage document hash and product/symbol/month/row/schema/Parquet
   binding agrees with its descriptor entry;
4. aggregate descriptor and Parquet metadata row counts equal 16,033,469 for bars and 16,033,442
   for trade flow;
5. the referenced quality-gap Parquet and lineage files have exact hashes, schemas, row counts, and
   missing-grid totals; the lineage's canonical exclusion hash recomputes; and every provider-invalid
   gap has exactly one matching exclusion lineage entry with the same product, symbol, month, open
   time, and reason;
6. the bar exclusion set has 40 unique raw-row identities, the trade-flow set has 67, the bar set is
   a subset of trade flow, and the trade-flow-only set has 27; and
7. staging is empty, no normalizer is running, current exact available bytes are labeled as a new
   audit-time observation, and physical artifact inventories explicitly separate descriptor-
   referenced files from old unreferenced content-addressed files.

The audit stops on the first mismatch and records the exact mismatch without repair. On success or
failure Hermes publishes `research/sprint_004/456_CEX002_KLINE_FULL_RECONCILIATION_RECORD.md` plus
matching `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`, commits and pushes only those three
paths, and returns both actor fields to the reviewer.

No real-data run, retry, wrapper, detach, polling loop, data mutation, integration, test, code,
cleanup, acquisition, catalog, NautilusTrader, experiment, model, Harmonic Trader, other product,
PAPER, LIVE, or next-ticket work is authorized. Gate 2 remains accepted; Gate 3 and CEX-002 remain
`IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer publishes exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
All source, test, data, runner, and unrelated dirty paths remain unstaged and untouched.
