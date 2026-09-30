# SPIFFE/SPIRE integration and autonomous Kaiba installations

Accepted direction: 2026-09-28. This document records the next implementation
steps; it does not establish production readiness or replace existing hardware
qualification evidence.

## Status and ownership

| Workstream | Status | Completion evidence |
| --- | --- | --- |
| Deployment roles and trust boundaries | Accepted design | This roadmap and the additive workload contract |
| Existing fleet enrollment | Software rehearsal implemented | Existing `kaiba-fleet` tests; production admission remains unavailable |
| SPIRE membership and identity contracts | Additive draft implemented | `WorkloadBinding` `0.5.0-draft.1`; pinned prototype corpus conformance; production adoption pending |
| Opt-in SPIRE identity foundation | Software prototype verified locally | Fleet module and synthetic mTLS service; unit/module and four-machine VM checks pass on 2026-09-29 |
| Real DNS and fleet inventory integration | Software integration verified locally | PostgreSQL-backed workload registry, explicit operator grants, and SPIFFE DNS updater/controller mode |
| Persistent identity pilot on Ace | Installed and verified, 2026-09-29 | `pilot.kaiba.pseudo.design`; exact-unit identity, wrong-unit denial, consumed-grant restart, controlled warm reboot and existing-service preservation; [rollout record](persistent-identity-pilot.md) |
| Current-pilot LAN integration | Native positive path, member restart, grant quarantine/restoration and bounded service outages passed | Authority migration and endpoint cutovers accepted; Mako admitted; grant-free Agent restart and both-host DNS queries pass; fresh updater denied while quarantined, same binding restored; registry pause/resume and primary stop/restart pass; temporary activations retain persistent baselines; Malak fenced; 135 migration checks pass; broader lifecycle/outage and full qualification remain open; [LAN rollout record](pilot-dns-rollout.md) |
| Offline hardware continuity | Unqualified; Ace identity smoke passed | Ace/Mako inventories and native ARM64 SPIRE behavior recorded; boot/rollback physical campaign remains open |
| Product installation and UI | Planned | Integrated enrollment, promotion, health, and recovery flows |
| Production autonomous operation | Gated | Physical end-to-end acceptance on a qualified profile |

VM success demonstrates software behavior. It cannot qualify physical rollback
protection, hardware key isolation, or autonomous production boot. Record
prototype results separately from hardware evidence as work advances.

The current LAN pilot policy and temporary workload registrations retain the
original deadline, `2026-10-03T02:06:35Z`. No extension is authorized or
implemented; temporary activation has not changed either persistent boot baseline.

The first slice adds a separate Go identity module, a Workload API probe and
synthetic mTLS service, owner/provider SPIRE isolation, and versioned workload
binding validation in `kaiba-fleet`. Its test corpus is pinned to the additive
contract draft; the existing pilot protocols retain their current pins and
checks. The [prototype guide](https://github.com/PseudoDesign/kaiba-fleet/blob/codex/spiffe-spire-prototype/docs/spiffe-prototype.md)
records the interfaces and validation status. Local validation on 2026-09-29
passed both fleet and isolated identity Go tests, all 104 companion contract
tests, Nix unit/module checks, and the four-machine VM topology. The VM result
is synthetic and explicitly marks hardware as unqualified. This slice has no
real DNS integration, authenticated production registry, or complete fleet
installer. The linked branches and contract draft are under review; no remote
CI result is claimed here.

The next integration slice now supplies a real `kaiba-workload-registry` backed
by the existing fleet PostgreSQL inventory, plus opt-in SPIFFE transport in the
DNS updater and controller. An exact operator identity grants a workload one
stable numeric DNS assignment; each protected request checks current instance,
permission, configured authority/tenant/security scope, and inventory policy.
The logical fleet ID remains distinct from the assigned DNS number. The
[authorization contract](https://github.com/pd-codex/kaiba-contracts/pull/14),
[DNS integration](https://github.com/pd-codex/nixos-kaiba-network/pull/3), and
[live fleet integration](https://github.com/PseudoDesign/kaiba-fleet/pull/28)
record these interfaces. Contract tests, DNS Go/Nix checks, and 14 PostgreSQL
registry tests with the Go race detector pass locally. The combined
SPIRE/PostgreSQL/DNS VM passes, including actual publication, quarantine on a
reused connection, updater denial during database outage, and replaced-instance
denial. The DNS compatibility seven-VM suite and ARM64 package build also pass
in remote CI. This service reads the original `enrollments` lifecycle and
does not silently migrate `pilot_enrollments` or enable production admission.

The [hardware inventory draft](https://github.com/PseudoDesign/kaiba-provisioning/pull/95)
records read-only observations from Ace and Mako. Both report Pi 5 Model B
Rev 1.1; Ace has newer observed bootloader firmware and is the selected first
research host. The inventory's small service sample was incomplete: Ace runs
Hydra and PostgreSQL, which subsequent work must preserve. Its SSH key was
verified against the owner's supplied fingerprint. Neither board's
secure boot, offline rollback prevention, TPM suitability, or offline time
continuity is established. No firmware, OTP, disk, service or boot configuration
was changed by these checks.

A subsequent isolated SPIRE 1.15.2 smoke on Ace passed real Workload API SVID
rotation in one process, agent restart after deleting its consumed grant, and
expiry denial during an authority outage with the agent still running. The
nonroot runner used temporary private state and loopback networking, then
confirmed process/state cleanup. Signed runtime packages were added to the
Nix store without activating a system profile or installing persistent
services. This demonstrates native ARM64 identity behavior; it does not deploy
the complete DNS stack or qualify any offline boot/rollback gate. The hardware
draft retains the pinned runner and sanitized observations.

The owner has now selected `pilot.kaiba.pseudo.design` and authorized a
[persistent identity pilot on Ace](persistent-identity-pilot.md). Guarded native
test activation, explicit initialization and persistent switch passed, followed
by fresh SSH access and a successful probe at `2026-09-29T06:09:10Z`. This slice
runs a loopback SPIRE authority, local agent, durable bootstrap guard, and dedicated
systemd-unit probe. Ace obtained its intended identity, denied the same user
under the wrong unit, and restarted the server and agent with the consumed
grant absent while preserving the authority, node and registration. Existing
public enrollment status remained unchanged; Hydra and PostgreSQL stayed
healthy, and there were no failed units. The
[fleet pilot](https://github.com/PseudoDesign/kaiba-fleet/pull/29) also passed ten
synthetic VM groups covering initialization, live-source rotation, reboot,
state-loss denial, SQLite restart and guarded bundle restoration. Kernel,
initrd/modules, fstab/crypttab and existing service definitions matched the
pre-change system; the previous generation is retained, and Mako's evaluated
configuration is unchanged. Ace subsequently passed a controlled online warm
reboot at `2026-09-29T06:44:11Z`, preserving its authority, exact probe identity
and existing public enrollment. Cold/offline boot remains unqualified. This
initial phase did not connect real fleet admission or DNS publication. Separate
`spire.pilot.kaiba.pseudo.design` and `updates.pilot.kaiba.pseudo.design` endpoint
names are design choices; this phase creates no corresponding DNS records.
The owner selected LAN qualification first. The prepared software slice adds an
explicit current-pilot admission adapter, operator readback/client, preserved
authority promotion and isolated primary/replicas. The promotion VM passes
fourteen checks and the focused DNS VM passes fifteen; a separate combined VM
exercises the SPIFFE application path against synthetic inventory. The published
bounded station installer passed 23 preparation/installer tests and isolated
PostgreSQL 18 validation. Ace's candidate reached its first probe at approximately
`2026-09-29T08:18:42Z`, with its booted and persistent generation unchanged.
Pre-station checks passed at `08:22:35Z`: identity, enrollment and existing
services were preserved, and the same updater user under a wrong systemd unit
was denied identity. An exact-controller-identity request returned HTTP 503 with
the registry unavailable, and the real updater was restored. The trial expired
at `08:52:37Z` without an accepted station installation receipt or native
end-to-end result. Its seven new DNS units stopped, and guarded restoration of
Ace's retained baseline passed at `14:26:10Z` with identity, enrollment and
existing services preserved. The owner accepted Ace as Kaiba
server, Mako as agent and a real LAN replica, and Malak as operator only. It
requires transferring the complete pilot control plane and qualifying normal
operation with Malak disconnected. Disabled host profiles are authored and their
disabled closures match the persistent Ace/Mako baselines; enabled staging selects
an immutable deny guard and leaves new services stopped. Both hosts passed native
builds and temporary dormant test activation at `19:31Z`, preserving selected
application processes, device state and ownership, boot identity and persistent
profiles. Ace's existing SPIRE processes were preserved; no authority state was
imported or activated. The rollout record distinguishes these checks from the
observed activation changes to DBus, firewall and Ace's mounts/setup services.
The final two-host DNS VM passed eight groups. The imported Fleet control-plane
VM passes nine checks, including startup denial and authenticated readiness.
Fleet also passed
seven guard tests, six real PostgreSQL groups and module/all-system evaluation.
Import must preserve the Reader paths and
endpoints covered by the retained issuer scope, rather than rewriting scope rows
to accept a mismatch. The owner ran the frozen read-only migration inventory
helper, which passed twelve tests, and the private report's digest is verified.
Ace's encryption recipient and transport CSR are prepared. The source fence
and encrypted export helper passed seventeen synthetic tests; the importer passed
a disposable PG18 dump/restore comparison. The complete migration Nix check
passed 76 tests with zero skips; the changes are published at
[Fleet `0bd55c5`](https://github.com/PseudoDesign/kaiba-fleet/tree/0bd55c576536c29825aada2f7ce6fa052a877402/deploy/pilot-migration).
The subsequent [device endpoint helper](https://github.com/PseudoDesign/kaiba-fleet/blob/797a9e2b7de9f94ad5bd29ebe21420434cff2b7b/deploy/pilot-migration/device-endpoint.md)
extends that suite to 92 passing checks and has a separate passing real
bind-mount regression. It preserves credentials and history while changing only
the Fleet URL after authenticated target admission. Both native endpoint moves
were subsequently accepted on September 30 local time, with fresh installed-client
access to Ace and complete private backup comparison confirming only that URL changed.
The reviewed issuer-only callback
dial override preserves the canonical source URL, TLS name and all four scope
pins while reaching Ace. Following the expired-credential finding, Mako's same-key
recovery passed on September 29 local time: credential revision 2 with exactly
one successor issuance, preserved identity/key/history, installed-key proof,
fresh-process access and access after authority restart. Full qualification
remains false. The refreshed
source inventory is verified, and Ace's preparation is rebound while preserving
its original keys and receipt. Recovery-aware migration helpers pass 135 checks
with zero skips, including exact membership and issuer-scope continuity before fencing.
Source preparation passed on September 29 local time: the completed recovery
guard passed, policy continuity was recorded, and Ace's transport certificate
was signed with the existing deadline and source services preserved. Ace's
immutable target guard and active system closure passed native build checks.
Native host checks passed, including denial without imported state; current and
persistent profiles and existing service processes were preserved during these
build checks. On September 30 local time, Malak's fenced encrypted export
succeeded. Import on Ace verified complete content, schema and sequence
equivalence for both databases, and finalization passed. Ace then passed temporary
activation on the same boot while preserving its persistent baseline and existing
Hydra, regular PostgreSQL and SSH processes. Promoted SPIRE and imported
authorities are healthy; the DNS controller, primary and publisher are active.
Four workload registrations bind exact units
and users with the original deadline. Authenticated Reader resolution and
independent active-binding checks passed for both retained devices. Malak's
source fences remain verified. Both device endpoint cutovers to Ace are accepted
with their exact retained bindings and false full-qualification status. The
explicit DNS grant is accepted; Ace's updater is healthy and its assigned record
is authoritative on both hosts. Mako's SPIRE admission and restart after consumed
grant removal passed with its node and key preserved. Exact-unit probes succeeded
before and after a bounded same-user wrong-unit no-identity
observation; that observation was not an explicit denial response. Matching
UDP/TCP queries, unsigned AXFR rejection and agreement of desired/origin/observed
publication state passed. Existing applications, device state and persistent
baselines remain preserved. The
[sanitized native observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-ace-mako-lan-acceptance.json)
records this bounded acceptance. The old owner signing command remains superseded.
A subsequent native grant check denied a fresh actual updater request with
HTTP 403 while quarantined and left its complete intent tuple unchanged.
Restoration of the same binding allowed a fresh lease; its current state is
active revision 3. DNS endpoints, source fencing and existing applications were
preserved. The [additive grant observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-native-workload-quarantine.json)
records this check; it does not claim enforcement on a reused TLS connection.
The [bounded service-outage observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-native-service-outages.json)
adds registry pause/resume and primary stop/restart acceptance. The actual updater
received HTTP 503 while the registry was paused without changing intent state;
the same process recovered with authenticated authorization and a newer lease.
Mako retained DNS answers while the primary was stopped, and endpoints and intent
converged after restart. Active grant revision 3, source fences, applications and
profiles were preserved. SPIRE/database outages, replica restart without a
primary, and timed catch-up from new publication remain untested natively.
Broader native lifecycle checks, remaining outages, operation with Malak
disconnected, persistent profiles/reboot and hardware qualification remain
pending. The
[DNS rollout record](pilot-dns-rollout.md) describes the selected topology and
public-delegation boundaries. Persistent identity service acceptance and physical
offline qualification remain separate evidence tracks.

Shared interfaces belong in
[`kaiba-contracts`](https://github.com/pd-codex/kaiba-contracts). Extend the existing
[`kaiba-fleet`](https://github.com/PseudoDesign/kaiba-fleet) service for reusable
fleet identity and NixOS presets. This refines the initially proposed new
`kaiba-runtime` repository: fleet already owns Go/PostgreSQL enrollment,
inventory, credential lifecycle, and software rehearsals, so reuse that
boundary. `kaiba-provisioning` owns boot, provisioning, and hardware
qualification; `nixos-kaiba-network` owns DNS integration; `kaiba-ui` owns
product flows. `kaiba-infra` continues to own CI, builders, caches, and
deployment infrastructure. Its [CI milestones](ci-design.md) remain in effect.

## Deployment and trust model

Standalone Kaiba is a complete, owner-controlled, one-device fleet. The server
role expands that fleet; an agent joins it. SPIFFE provides workload identity
and credential interfaces, and SPIRE issues and rotates credentials. Kaiba
retains ownership, admission, authorization, boot policy, and recovery. This
uses the upstream [SPIRE server-and-agent model](https://spiffe.io/docs/latest/spire-about/spire-concepts/).

| Installation preset | Components | Authority dependency |
| --- | --- | --- |
| Standalone | Local Kaiba controller, SPIRE Server, SPIRE Agent, applications | Local authority; autonomous production operation requires offline qualification |
| Server | Standalone components plus remote enrollment and fleet management | Hosts the owner's fleet authority |
| Agent | Kaiba device services, SPIRE Agent, applications | Joins the owner's authority and needs it for renewal |

Each newly initialized owner installation receives a unique, persistent trust
domain. Members join that domain. Promoting standalone to server preserves its
domain, identities, and data. Local discovery and management must work without
provider DNS. Agent-only devices can use still-valid credentials during an
authority outage, but cannot renew them indefinitely; cold-boot and restart
behavior must be measured separately from continued operation.

Configuration exposes three independent decisions: deployment role, owner-fleet
membership, and optional `kaiba.network` enrollment. Health reports separate
boot assurance, local identity health, and provider connectivity. A local
identity success must not imply qualified boot or working public DNS.

### Optional provider relationship

An opted-in device runs a second SPIRE Agent for `kaiba.network`, with separate
state, Workload API socket, bootstrap credentials, and trust bundles. The first
provider capability is DNS updates for that device's assigned names. Local
credentials do not authorize provider operations, and provider credentials do
not grant local administration.

Exercise this dual-agent topology in the prototype. Provider outage, expiry,
or unenrollment must leave local operation intact. Do not grant an owner's
SPIRE Server `kaiba.network` signing authority: upstream
[nested SPIRE](https://spiffe.io/docs/latest/architecture/nested/readme/) delegates
issuance within a shared trust domain. Federation and remote administration are
deferred.

## Identity and contract changes

- Bind workload identities to the trust domain, device enrollment instance,
  and service. Keep the logical inventory identity stable across replacement,
  but assign a new instance so old credentials cannot become active again.
  The additive [WorkloadBinding draft](https://github.com/pd-codex/kaiba-contracts/blob/8ef002018b6b042451e6724ac63659e294656570/contracts/workload-binding.md)
  defines the exact URI grammar. Production consumer mapping and adoption remain
  required.
- Keep admission in Kaiba. Owner-authorized enrollment binds provisioning
  evidence, bootstrap identity, and inventory before creating narrowly scoped
  SPIRE registrations. Initial enrollment uses short-lived, single-use grants
  over an authenticated channel with pinned server trust. Expired or uncertain
  enrollment enters recovery; it does not silently issue another grant.
- Authorize the active device instance and permitted workload on each request,
  including requests on existing connections. Quarantine and retirement must
  take effect without waiting for certificate expiry. SPIRE issuance alone is
  not a membership or permission decision.
- Retain issuance audit records, but replace manual activation of every rotated
  operational certificate serial with authorization of the enrolled instance
  and workload. Define the migration in the shared lifecycle contract before
  production consumers change their behavior. Keep the current exact-tuple
  enrollment and pilot protocols unchanged until this versioned migration is
  explicitly adopted.
- Integrate the Workload API using [go-spiffe](https://github.com/spiffe/go-spiffe)
  for renewable credentials, trust bundles, and explicit peer authorization.
  Start with the DNS updater/controller. Preserve their HTTP behavior and
  assigned DNS names, mapping instance/workload identity to the existing logical
  device record. File credentials remain only in explicitly selected
  compatibility or test configurations; never use them as an automatic fallback.
- Add authority profiles: standalone and server installations may hold their
  own CA signing keys; agent-only devices do not. Keep CA, bootstrap, storage, and
  workload keys separate. Standard workload credentials can expose private
  keys to the workload process and must not be described as non-exportable or
  proof of hardware attestation.

These are explicit changes relative to the proposed
[provisioning identity lifecycle](https://github.com/PseudoDesign/kaiba-provisioning/blob/main/docs/device-identity.md),
archived [station activation model](https://github.com/PseudoDesign/kaiba-provisioning/blob/main/docs/archive/provisioning-station-production.md),
and [DNS identity lifecycle](https://github.com/pd-codex/nixos-kaiba-network/blob/main/docs/device-identity.md).
The identity references retain the prohibition on device-resident CA keys and
exact certificate-instance authorization; the archived station model describes
the earlier activation design. Production adoption must reconcile the new
authority-role profiles with current lifecycle contracts while leaving archived
assumptions identified as historical. This roadmap does not silently relax
existing implementations or station authority boundaries. The implemented
[fleet enrollment rehearsal](https://github.com/PseudoDesign/kaiba-fleet/blob/main/docs/enrollment.md)
and [pilot lifecycle](https://github.com/PseudoDesign/kaiba-fleet/blob/main/docs/pilot-lifecycle.md)
retain their current exact-tuple checks during the prototype. Preserve the DNS
API and publication semantics
documented in the [pilot architecture](https://github.com/pd-codex/nixos-kaiba-network/blob/main/docs/architecture.md).

## Offline boot and hardware qualification

The archived [Pi production follow-on](https://github.com/PseudoDesign/kaiba-provisioning/blob/main/docs/archive/raspberry-pi-5-production-security-follow-on.md)
requires fresh online release authorization and does not establish offline
anti-rollback. The selected first-fleet pilot permits offline operation without
requiring offline rollback prevention, as recorded in the
[delivery scope](https://github.com/PseudoDesign/kaiba-provisioning/blob/main/docs/delivery-scope.md).
The autonomous production profile proposed here is a separate qualification
track. Preserve current pilot admission and development gates; neither is
silently upgraded by the SPIRE prototype or this stronger follow-on.

Protect three independent rollback boundaries: verifier version, OS security
epoch, and security-critical authority state. Restoring an encrypted database
must not restore revoked memberships, obsolete permissions, or removed trust
keys. Encryption alone does not provide continuity.

### Candidate 1: native Raspberry Pi

Investigate customer OTP bits as a finite monotonic epoch source enforced by
the stable verifier. Raspberry Pi documents irreversible programming and Pi 5
customer OTP locks that need to be applied each boot; these are candidate
building blocks, not a demonstrated rollback mechanism. See the official
[customer OTP documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#write-and-read-customer-otp-values).

Qualification must prove that older signed EEPROM, verifiers, and recovery
images cannot bypass the floor, that interrupted programming has a safe
outcome, and that the finite transition budget covers the intended device
lifetime. Include how authority-state commitments advance without exhausting
that budget.

### Candidate 2: TPM 2.0 add-on

If native Pi fails a required property, qualify TPM counters, authenticated
state commitments, and protected key release. Prove the binding between the
specific Pi and TPM and the complete boot enforcement path. Removal, clearing,
replacement, or missing state must enter recovery rather than initialize a new
authority automatically. A TPM's presence alone is not qualifying evidence.

### Required behavior for either candidate

- Commit security changes durably before acknowledging them. Bind hardware
  continuity to authenticated state contents. Ordinary certificate renewal must
  not require a hardware counter increment.
- Order startup as verified boot, hardware continuity and epoch checks,
  protected-state validation/unlock, local controller and SPIRE Server, SPIRE
  Agent, then applications.
- Qualify offline timekeeping, certificate expiry, and restart behavior.
  Uncertain or rolled-back time must not disable certificate validation.
- Preserve recovery without lowering security floors. An obsolete backup
  cannot automatically become the current authority.

Publish a pinned board, firmware, verifier, and optional TPM profile with a
result of **qualified native**, **qualified TPM**, or **not qualified**. Missing
evidence keeps autonomous production deployment gated; it does not select a
weaker fallback. Hardware qualification includes physical observation and
separately authorized irreversible operations, not just software tests.
Use the [offline qualification matrix](offline-qualification.md) to record
the required evidence and candidate outcome.

## Delivery sequence and acceptance

1. **Contracts and architecture decision.** Record roles, trust domains, URI
   naming, enrollment states, authorization, health interfaces, and hardware
   acceptance criteria. Reconcile the existing lifecycle and activation
   documents with the shared contracts.
2. **VM integration.** Build standalone, server/member, and optional-provider
   topologies in the `kaiba-fleet` prototype. Exercise real SPIRE credentials and
   DNS updates, rotation, denial, and outages. Make checks available to CI.
3. **Hardware qualification, in parallel.** Implement and test the native
   candidate first, then the TPM candidate if required. Keep physical evidence
   and unresolved qualification gates separate from VM results.
4. **Product integration.** Connect actual enrollment and health APIs to the
   UI. Add installation presets, standalone-to-server promotion, recovery, and
   operational diagnostics.
5. **Production acceptance.** Complete provisioning, enrollment, cold boot,
   local operation, and optional DNS enrollment on qualified physical hardware.

The acceptance suite must cover:

- Standalone cold boot without network access and local renewal through
  multiple credential rotations, including restart behavior.
- Promotion to server without changing the trust domain, followed by admission
  of an approved member.
- Provider outage, expired credentials, and unenrollment with continued local
  operation; owner-server outage with an explicit member renewal limit.
- Denial of wrong workloads, replayed enrollment grants, retired instances,
  and locally issued attempts to impersonate provider identities.
- Credential and trust-bundle rotation without service restarts, plus
  quarantine enforcement on existing connections.
- Rejection or safe recovery for old signed boot images, restored authority
  databases, interrupted updates, hardware resets/replacement, and clock
  failures, without restoring obsolete authority.
- Recovery without cloud access wherever the qualified profile promises
  autonomous operation.

Initial defaults are NixOS/systemd, X.509 workload credentials, one authority
per owner installation, and DNS updates as the first provider capability. HA,
federation, remote administration, and moving an initialized standalone
installation into another owner's fleet are deferred. That last operation
changes trust domains and requires its own explicit migration workflow.
