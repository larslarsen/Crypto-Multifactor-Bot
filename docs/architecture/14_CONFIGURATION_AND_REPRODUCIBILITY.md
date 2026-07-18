# 14 — Configuration and Reproducibility

## Configuration hierarchy

1. versioned defaults;
2. versioned environment profile;
3. explicit CLI configuration file;
4. narrowly permitted CLI overrides;
5. secrets supplied outside Git.

The fully resolved non-secret configuration is canonicalized and hashed for every build or experiment.

## Reproducibility identity

A research result is identified by the hash of:

- experiment registration;
- resolved configuration;
- code commit;
- dependency lock;
- input dataset IDs;
- universe version;
- factor/model versions;
- split definitions;
- cost policy;
- random seeds and deterministic settings.

## Randomness

- seeds are explicit and recorded;
- algorithms known to be nondeterministic are declared;
- parallelism settings are recorded;
- repeated runs with the same fingerprint may create attempts, never overwrite the prior attempt.

## Environment

The supported environment is Python 3.12 on a local machine. Containers are optional and not the source of truth. The dependency lock and platform summary are retained in experiment bundles.

## Paths

All data roots are configured. Manifests store normalized URIs plus hashes; code never depends on one developer's absolute path.
