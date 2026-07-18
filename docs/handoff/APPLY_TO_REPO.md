# Apply this package to the repository

The package is structured as an additive overlay.

## Safe installation

From outside the repository:

```bash
unzip crypto_multifactor_implementation_handoff_v1.zip
cd /path/to/Crypto-Multifactor-Bot
rsync -av --ignore-existing \
  /path/to/crypto_multifactor_implementation_handoff_v1/repo_overlay/ ./
```

Then inspect collisions manually:

```bash
rsync -avni \
  /path/to/crypto_multifactor_implementation_handoff_v1/repo_overlay/ ./
```

Do not blindly overwrite an existing `pyproject.toml`, root `README.md`, CLI, or control schema. The overlay uses additive paths where practical. Merge the evidence CLI into the main CLI only after `CAT-001` passes.

## Recommended first commit

```bash
git add docs/architecture docs/adr docs/engineering research/evidence \
        schemas sql/migrations sql/views tickets prompts scripts tests

git commit -m "docs: add layer contracts and evidence registry design"
```

Keep reference Python modules in the same commit only if they fit the current package layout and tests pass.

## Verify

```bash
python scripts/validate_handoff_assets.py
python scripts/check_layer_imports.py --root src/cryptofactors
pytest -q
```

The repository remains research-only. Do not enable paper or live serving as part of this handoff.
