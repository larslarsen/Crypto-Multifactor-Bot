# Evidence status model

## Lifecycle

- `DRAFT`
- `REGISTERED`
- `ACTIVE`
- `DEFERRED`
- `CLOSED`

## Verdict

- `UNTESTED`
- `PRELIMINARY`
- `SUPPORTED`
- `REPLICATED`
- `NOT_REPLICATED`
- `REJECTED`
- `INCONCLUSIVE`
- `QUARANTINED`

Lifecycle and verdict are separate. For example, an active replication may have lifecycle `ACTIVE` while the current verdict remains `PRELIMINARY`.
