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

## Human passkey access

The flake also exports Keycloak, SSH certificate issuer, host trust, and encrypted
backup modules, plus the Linux `kaiba-login` package. See the
[human access runbook](docs/human-access.md) for deployment, initial owner
enrollment, workstation login, revocation, and recovery. Human credentials remain
separate from pilot device identities and automation credentials.

## Selector prototype

`ci/select_jobs.py` compares **evaluated derivation paths** for a fixed job inventory at the base
and proposed revisions. It emits JSON listing jobs to build and why. It does
not schedule Hydra builds. Provisioning's GitHub Actions workflow now uses
derivation-based selection independently of this Hydra rollout.

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

Both controlled warm reboots passed: Ace then ran generation 12 with
ordered clock-dependent startup, and Mako runs guarded generation 15. The later
owner-attested 75-minute Malak power-off passed bounded device-access, DNS and
post-TTL identity checks, plus one induced fresh update. Changed workstation boot
and network return were verified separately; source authorities remain fenced.
The original deadline is `2026-10-03T02:06:35Z`. The latest local migration suite
passes 155 tests with zero skips; prior identity, control-plane and DNS VM
evidence is recorded in the closeout report.
Broader credential lifecycle, SPIRE/database outages, publication catch-up and
longer unattended operation remain open. Hardware/offline boot and rollback
qualification, product installation/UI and public DNS remain separate; full
qualification remains false. The bounded physical campaign subsequently passed, and original encrypted
storage was restored on Ace generation 14. See the [LAN closeout implementation](docs/lan-closeout.md)
and [LAN rollout](docs/pilot-dns-rollout.md).

Reviewed merged runtimes are temporarily active on Ace and Mako; persistent boot
profiles remain unchanged. Renewal preparation and the separate SPIRE backup are
in draft PRs. GitHub billing/spending capacity currently prevents their CI jobs
from executing. A thirty-day delegation and unattended renewal are not active;
complete the reviewed trust/authority transition before the existing deadline.

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
| `kaiba-infra` | CI policy, job inventory, builders, caches, and human access infrastructure |
| `nix-pseudo-design` | Existing personal host configurations until deliberately migrated |
| `kaiba-contracts` | Product and device state contracts |
| `kaiba-fleet` | Inventory and enrollment; planned owner-fleet identity integration and NixOS presets |
| `kaiba-provisioning` | Provisioning, verified boot, and hardware security qualification |
| `nixos-kaiba-network` | Optional provider DNS service and updater integration |
| `kaiba-ui` | Enrollment, role selection, and health interfaces |

Host-specific addresses and module composition live in `nix-pseudo-design`.
Private keys and administrator credentials remain outside Git and the Nix store.
