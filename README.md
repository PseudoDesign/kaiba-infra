# Kaiba infrastructure

This repository owns the development infrastructure for Kaiba: build scheduling,
builders, caches, and eventually the Git forge. Application repositories expose
Nix `checks` and `packages`; this repository decides which revisions and jobs to
build and where to run them. Device protocol and state contracts remain in
`kaiba-contracts`.

## Hydra on Ace

The flake exports Nix-packaged Python tests, an ARM64 `hydraJobs` output,
NixOS modules for Hydra, Mako's HTTPS proxy and backup receiver, and native
qualification/integration tests. See [the deployment runbook](docs/hydra-on-ace.md)
for deployment, staged jobset setup, backups and recovery.

```sh
nix build --no-link .#checks.x86_64-linux.selector
python3 ci/setup_hydra.py  # preview; provisioning starts disabled
```

`kaiba-provisioning` imports the locked inventory policy to expose the ten ARM64
derivations to Hydra. Hydra evaluates each repository's `main` directly; GitHub
Actions remains the PR gate during rollout.

## Selector prototype

The current `kaiba-provisioning` workflow runs ten large ARM64 checks in one
serial step. `ci/select_jobs.py` is the first piece of the planned selector. It
compares **evaluated derivation paths** for a fixed job inventory at the base
and proposed revisions. It emits JSON listing jobs to build and why. It does
not replace or modify the current GitHub Actions workflow yet.

```sh
python3 -m unittest discover -s tests
python3 ci/select_jobs.py \
  --inventory ci/provisioning-arm64.json \
  --base examples/base.json --head examples/head.json
```

The example selects the single check whose derivation differs. Add
`--changed-path .github/workflows/ci.yml` to demonstrate a conservative full
selection after a workflow change. The manifests contain synthetic derivation
paths for demonstration; they are not evaluated repository revisions.

See [the CI design](docs/ci-design.md) for the evaluation boundary, rollout
order, and prerequisites before using selection in a required check.

## Ownership

| Repository | Owns |
| --- | --- |
| Kaiba project repos | Flake outputs, tests, application packages and modules |
| `kaiba-infra` | CI policy, job inventory, scheduling, builder and cache configuration |
| `nix-pseudo-design` | Existing personal host configurations until deliberately migrated |
| `kaiba-contracts` | Product and device state contracts |

Host-specific addresses and module composition live in `nix-pseudo-design`.
Private keys and administrator credentials remain outside Git and the Nix store.
