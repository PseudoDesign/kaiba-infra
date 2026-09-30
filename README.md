# Kaiba infrastructure

This repository owns the development infrastructure for Kaiba: build scheduling,
builders, caches, and eventually the Git forge. Application repositories expose
Nix `checks` and `packages`; this repository decides which revisions and jobs to
build and where to run them. Device protocol and state contracts remain in
`kaiba-contracts`.

## First milestone: inspect ARM64 work

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

## Next steps: owner-controlled identity and deployment roles

The accepted [SPIFFE/SPIRE integration plan](docs/spiffe-spire-plan.md) defines
standalone, server, and agent installations, with optional `kaiba.network`
enrollment kept separate from the owner's local fleet. The additive workload
contract and opt-in identity foundation are implemented and passed local unit,
module, and four-machine VM checks on 2026-09-29. Real DNS and fleet inventory
integration has passed software checks. Ace's first bounded LAN trial passed
pre-station checks, expired, and was restored to its retained baseline.
The [accepted deployment target](docs/pilot-dns-rollout.md#accepted-acemako-deployment-target)
uses Ace as the Kaiba server, Mako as an agent and DNS replica, and Malak as an
operator workstation. Both hosts passed temporary dormant staging with selected
existing services and device state preserved; their persistent boot profiles
remain unchanged and the new pilot units remain stopped. The two-host DNS
and imported Fleet control-plane VMs passed. The pre-recovery source inventory
was verified, and encrypted transfer preparation and source-fencing helpers
are published with 92 passing local migration checks, including device endpoint
transfer; a separate real bind-mount regression also passes. Mako's same-key
credential recovery passed on September 29 local time: revision 2, exactly one
successor, installed-key proof, fresh-process access and access after authority
restart. This is pilot recovery evidence, not full qualification. Malak remains
the serving authority. Next, refresh the protected source inventory and
source-bound transport/policy packets before transferring the complete control
plane to Ace. Mako's SPIRE admission, native end-to-end LAN acceptance and offline
boot/rollback qualification remain outstanding; no state export or cutover has
occurred.

This is a product roadmap, not a production-readiness claim. Extend the existing
[`kaiba-fleet`](https://github.com/PseudoDesign/kaiba-fleet) service for runtime
identity and role presets; shared contracts belong in
[`kaiba-contracts`](https://github.com/pd-codex/kaiba-contracts). This repository
retains CI and deployment infrastructure ownership, including the existing
ARM64 selection milestone above.

## Ownership

| Repository | Owns |
| --- | --- |
| Kaiba project repos | Flake outputs, tests, application packages and modules |
| `kaiba-infra` | CI policy, job inventory, scheduling, builder and cache configuration |
| `nix-pseudo-design` | Existing personal host configurations until deliberately migrated |
| `kaiba-contracts` | Product and device state contracts |
| `kaiba-fleet` | Inventory and enrollment; planned owner-fleet identity integration and NixOS presets |
| `kaiba-provisioning` | Provisioning, verified boot, and hardware security qualification |
| `nixos-kaiba-network` | Optional provider DNS service and updater integration |
| `kaiba-ui` | Enrollment, role selection, and health interfaces |

No hostname, signing key, SSH credential, or production service is configured
here yet. Host modules should be introduced alongside concrete hardware and
recovery procedures.
