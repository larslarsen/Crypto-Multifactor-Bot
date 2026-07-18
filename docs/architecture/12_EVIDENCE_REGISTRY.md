# 12 — Evidence Registry

## 1. Objective

The Evidence Registry is the institutional memory of the research program. It records what was hypothesized, why it was plausible, which evidence bears on it, what tests were run, and why a decision was made.

It is not a performance leaderboard and does not assign false precision to scientific judgment.

## 2. Core objects

### Hypothesis

A stable identity such as `H-001`. The identity never changes. Material edits create a new version.

Required content:

- falsifiable statement;
- economic mechanism;
- expected sign and scope;
- inputs and point-in-time assumptions;
- primary metric;
- rejection and advancement criteria;
- known confounders;
- preregistration timestamp.

### Evidence item

An immutable observation or source that can support, contradict, qualify, or remain neutral toward a hypothesis.

Evidence kinds:

- `LITERATURE_PUBLISHED`;
- `LITERATURE_WORKING`;
- `LEGACY_RESULT`;
- `EXPERIMENT_RESULT`;
- `DATA_AUDIT`;
- `THEORY`;
- `OPERATIONAL_OBSERVATION`.

### Evidence link

A registered relationship between one version of a hypothesis and one evidence item. It records direction, relevance, rationale, and integrity dimensions.

### Decision event

An append-only event establishing the current verdict or lifecycle state. Old events are never updated or deleted.

### Evidence snapshot

A generated, immutable summary of all evidence available as of a timestamp. Decisions refer to a snapshot hash so later evidence cannot retroactively change what a reviewer saw.

## 3. Verdicts

- `UNTESTED`: registered but no valid empirical test;
- `PRELIMINARY`: suggestive evidence, insufficient independent validation;
- `SUPPORTED`: preregistered evidence passes stated criteria;
- `REPLICATED`: supported by an independent pipeline, venue, period, or team as defined in the hypothesis;
- `NOT_REPLICATED`: a valid independent replication failed;
- `REJECTED`: evidence meets the preregistered rejection rule;
- `INCONCLUSIVE`: valid test lacks adequate power or yields unstable results;
- `DEFERRED`: blocked by data, cost, or priority constraints;
- `QUARANTINED`: evidence has a known integrity or lineage defect and cannot support promotion.

A hypothesis may be reopened by a new decision event, but the prior verdict remains visible.

## 4. Integrity dimensions

Each empirical evidence link records separately:

- point-in-time integrity;
- split/causal integrity;
- reproduction status;
- transaction-cost integrity;
- universe integrity;
- independence class;
- data availability and lineage.

These dimensions are categorical, not averaged into one score.

## 5. Decision rules

- Literature can motivate a hypothesis but cannot promote a trading artifact.
- A legacy result can prioritize replication but cannot establish `SUPPORTED`.
- Evidence with failed causal or point-in-time integrity is `QUARANTINED` for promotion purposes.
- `SUPPORTED` requires a preregistered experiment using immutable dataset IDs and accepted validation.
- `REPLICATED` requires the independence condition stated before the replication.
- Model promotion requires supported underlying hypotheses or an explicitly registered model-level hypothesis, plus serving parity and operational gates.
- A negative result is retained permanently.

## 6. Relationship to experiment tracking

The Evidence Registry does not replace experiment bundles. It points to them by fingerprint and records interpretation. Experiment tables answer “what ran?” The Evidence Registry answers “what did we learn and what decision followed?”

## 7. Initial hypotheses

The initial machine-readable registry is in `research/evidence/hypotheses.yaml`. Its statuses are deliberately conservative. No factor begins as supported.

## 8. Change control

- New hypothesis: add identity and version in one reviewed commit.
- Material hypothesis change: new version; never edit the historical version in place.
- New evidence: append evidence item and link.
- New verdict: append decision event referencing an evidence snapshot.
- Correction: append a correction/supersession event; never delete history.
