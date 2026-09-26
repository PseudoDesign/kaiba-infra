# CI and build farm design

## Existing workload

`PseudoDesign/kaiba-provisioning` has an ARM64 lane on `ubuntu-24.04-arm`.
Its `Build large ARM64 checks without build contention` step serially builds
the ten checks recorded in `ci/provisioning-arm64.json`. The workflow comments
state that hosted ARM64 runners lack KVM for the AArch64 VM tests, so those
tests fall back to emulation. Other ARM64 checks, packages, and artifacts run
in separate steps; this inventory deliberately covers only the large bundle.

## Selection contract

For each inventoried flake attribute, evaluate its `.drvPath` at the merge base
and the proposed revision, on the same platform with the same evaluator and
locked inputs. Record maps of attribute name to derivation path, for example:

```json
{"checks.aarch64-linux.provisioning-vm": "/nix/store/00000000000000000000000000000000-provisioning-vm.drv"}
```

Feed both maps into `ci/select_jobs.py`. A changed path selects its job; an
identical path can be omitted. An absent path, invalid manifest, failed
evaluation, changed inventory, or changed shared CI/Nix configuration must
select **all** jobs. The orchestration layer must treat a selector failure as
full selection, never as an empty matrix.

The selector accepts changed paths from the Git diff. The default policy
selects all for `flake.nix`, `flake.lock`, `nix/**`, `lib/**`, `modules/**`,
`tests/lib/**`, `.github/workflows/**`, and changes to the selector or
inventory. Expand these triggers for shared source paths discovered in the
project. A derivation path comparison is useful only if every test input is
tracked by Nix; impure tests, undeclared files, and tests of external state
must be scheduled separately. Also audit source filtering: if every check
copies the whole repository into its derivation, a small change may change
every derivation path. That is correct but will not save build time.

`select_jobs.py` is intentionally a pure policy core. The future evaluator
adapter will obtain the two revisions and produce complete manifests. Keep
evaluation failures visible in its logs. Never infer a cache hit or successful
test merely from an unchanged derivation path: a selected check still needs a
successful build, and an omitted check needs a trusted, recorded base result.

## Scheduling boundary

1. A repo's flake exposes checks and packages by platform.
2. This repo inventories which outputs are CI gates and evaluates two revisions.
3. Selection emits one named job per affected output, plus full-selection
   reasons when policy requires it.
4. The scheduler sends native x86 or ARM64 builds to eligible builders and
   records each result separately.
5. The binary cache serves signed outputs after successful builds. Cache
   signing keys stay outside the repository and Nix store.

Hydra can own Nix job evaluation and build scheduling later. Forgejo Actions
can handle general PR automation and report status. Nix distributed builds
can be used with the existing forge before either service migrates. Hydra's
normal reuse of identical derivations may ultimately make an explicit
base/head selector unnecessary for some jobs; measure that before wiring the
selector into Hydra.

## Rollout

1. Measure individual check durations and verify the current ARM64 inventory.
2. Evaluate base/head manifests in shadow mode, retaining the full existing
   ARM64 gate; inspect selections over representative PRs.
3. Verify source dependency closure and trusted base results. Then move the
   large bundle to separately reported jobs with concurrency limited to one.
4. Add a native ARM64 builder with working hardware virtualization if the VM
   tests require it; prove the virtualization capability with a VM smoke test.
5. Introduce a signed binary cache, then consider Hydra and the forge migration.

Do not deploy a live CI or cache service from this repository until host
identity, storage, backup, access, and key handling are specified.
