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

The accepted [SPIFFE/SPIRE plan](docs/spiffe-spire-plan.md) defines standalone,
server and agent roles with separate optional provider enrollment. The native
Ace/Mako pilot now runs its authority and DNS primary on Ace, with Mako admitted
as an agent and read-only replica. Malak's source is fenced. Verified migration
preserved both databases, issuer history and device identities; both installed
clients now authenticate to Ace. Explicit DNS authorization, publication and
matching queries on both hosts passed. Mako retained its node and key through
Agent restart after grant removal; exact-unit probes bracketed a bounded
wrong-unit no-identity observation. Existing applications and the then-current
boot selections were preserved through those checks. Native grant quarantine and
restoration, plus bounded registry/primary-DNS outage checks, passed. Mako also restarted its replica and
served retained records while the primary was stopped. Passive identity checks
observed Mako node renewal and a fresh workload certificate after prior expiry.

The verified running profiles are now installed persistently as Ace generation
11 and Mako generation 15, with boot files checked against encrypted rehearsals
and prior recovery entries retained. Mako's admitted startup guard also passed
native activation. Neither host was rebooted; existing applications and device
state remain intact. The original pilot deadline is unchanged at
`2026-10-03T02:06:35Z`. Software validation includes 135 migration tests with zero
skips and the identity, control-plane and DNS VMs. Remaining native work covers
broader credential lifecycle, SPIRE/database outages, publication catch-up and
operation with Malak disconnected. Reboot and disconnection checks wait for
physical recovery access. Hardware/offline boot and rollback qualification,
product installation/UI, and public DNS remain separate. See the
[LAN rollout](docs/pilot-dns-rollout.md) for evidence and next steps.

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
