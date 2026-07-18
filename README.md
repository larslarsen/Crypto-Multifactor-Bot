# Crypto Multifactor Bot

Cross-sectional cryptocurrency multifactor research program.

This repository currently holds the **Sprint 1 research specification package**
(located in [`crypto_multifactor_research_sprint_v1_1/`](crypto_multifactor_research_sprint_v1_1/README.md)).
The package supplies the research contracts that should precede architecture and
implementation: a research charter, falsifiable hypotheses, a legacy-repo audit,
point-in-time data / universe / validation contracts, canonical factor cards, a
transaction-cost and portfolio-construction protocol, a volume-bar replication
protocol, a literature synthesis, and preregistered experiments.

## Evidence status — READ THIS

Per the sprint README, the following holds and is **intentionally** so:

- **Raw observations and full prediction lineage are unavailable** in this
  public repository. Dataset counts and date spans are recorded as **author
  claims**, not verified results.
- **No historical performance claim is accepted as validated.**
- The **information-bar result is a replication candidate, not an established
  edge.**
- The **committed information-bar models are quarantined** from serving until
  causal-representation and parity tests pass.

### Audit interpretation (senior + junior review)

| Dimension | Status |
|---|---|
| Disclosure / internal consistency | Pass |
| Artifact reproducibility | Not established |
| Validation quality | Unresolved — evaluation defects identified (noncausal thresholding, train/test overlap, evaluator/trainer mismatch, cross-venue parity) |
| Serving readiness | Blocked, as intended |
| Evidence status | Quarantined hypothesis, not accepted alpha |

Documenting these caveats does **not** fix the underlying evaluation defects.
It means the repository is not misleading readers into treating the artifacts
as production-ready. Architecture and implementation should begin only after
the Tier-0 data acceptance gates pass (see `crypto_multifactor_research_sprint_v1_1/02_DATA_AUDIT_PLAN.md`).

## Layout

- `crypto_multifactor_research_sprint_v1_1/` — the full Sprint 1 specification package.
- `crypto_multifactor_research_sprint_v1_1/README.md` — detailed package README and recommended reading order.

## Legacy context

The research program treats `https://github.com/larslarsen/Trading-Bot` as an
evidence archive and a source of potentially reusable components — **not** as
the architecture or research design to preserve.
