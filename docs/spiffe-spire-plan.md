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
| Real DNS and fleet inventory integration | Planned | Authenticated current registry integration and DNS updater/controller acceptance |
| Offline hardware continuity | Unqualified | Pinned hardware/firmware profile and complete physical evidence |
| Product installation and UI | Planned | Integrated enrollment, promotion, health, and recovery flows |
| Production autonomous operation | Gated | Physical end-to-end acceptance on a qualified profile |

VM success demonstrates software behavior. It cannot qualify physical rollback
protection, hardware key isolation, or autonomous production boot. Record
prototype results separately from hardware evidence as work advances.

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
