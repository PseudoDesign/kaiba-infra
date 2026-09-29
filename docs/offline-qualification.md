# Offline authority qualification matrix

Status: **not qualified**. This is an evidence plan for the hardware work in the
[SPIFFE/SPIRE roadmap](spiffe-spire-plan.md), not a test result or a provisioning
procedure. Hardware implementation and physical campaigns belong in
`kaiba-provisioning`.

The archived
[Pi production follow-on](https://github.com/PseudoDesign/kaiba-provisioning/blob/main/docs/archive/raspberry-pi-5-production-security-follow-on.md)
uses online freshness. The current first-fleet pilot separately allows offline
operation without requiring offline rollback prevention. This matrix qualifies
the new autonomous production profile; it does not retroactively change pilot
admission. A local SPIRE Server removes a network dependency for
credential issuance only after boot and protected authority state can be
trusted offline. Software tests do not establish that property.

## Candidate order and recorded profile

Evaluate native Raspberry Pi monotonic state first. If it cannot satisfy a
required property, evaluate a TPM 2.0 add-on. Neither candidate inherits a pass
from the other, and adding a TPM does not establish the Pi/TPM binding or the
boot enforcement path.

For each candidate, pin board model/revision, firmware and EEPROM configuration,
verifier and recovery artifacts, OS and security epochs, protected storage
layout, time source, and, when present, TPM model/firmware and binding policy.
Record the permitted attacker boundary and the reason each claimed security
property follows from the complete chain. Keep secrets and private customer
configuration out of public evidence.

Each observation must identify the exact profile, inputs and digests, initial
state, expected result, observed result, and independently retained evidence.
Interrupted operations require before/after state observations. A missing
observation is an open gate.

## Initial board inventory

Read-only inventories were collected on 2026-09-29 from
[Ace](https://github.com/PseudoDesign/kaiba-provisioning/blob/0d15634b5eefb4f63146e0e29182ebaf37369e9a/docs/observations/2026-09-29-ace-offline-inventory.md)
and [Mako](https://github.com/PseudoDesign/kaiba-provisioning/blob/0d15634b5eefb4f63146e0e29182ebaf37369e9a/docs/observations/2026-09-29-mako-offline-inventory.md).
Both report Pi 5 Model B Rev 1.1, writable encrypted roots, and currently
synchronized network time. No TPM device interface was observed, and the
signed-boot device-tree property was absent; neither absence establishes the
complete hardware or secure-boot posture.

Ace is the preferred first research target because it has newer observed
firmware and fewer observed services. Mako remains useful for later comparisons
with its existing workloads accounted for. These inventories pin starting
observations only. All qualification rows remain open, including offline time,
old signed boot paths, authority-state rollback, and recovery. The next
reversible identity smoke is recorded separately from a reviewed physical
boot/monotonic-state campaign.

The isolated Ace SPIRE 1.15.2 smoke subsequently passed native ARM64 credential
rotation, agent restart without the consumed bootstrap grant, and expiry denial
during an authority outage. Its private temporary state and processes were
removed. This supplies preliminary software evidence for the identity portion
of OFF-08, with network-synchronized time and no reboot; it does not close
OFF-08 or establish boot, hardware continuity, protected-state recovery, or
clock assurance. Runtime Nix packages remain ordinary unrooted store objects;
no system profile, persistent service, firmware, OTP or TPM policy was changed.

## Required observations

All rows are open. A candidate is qualified only when every applicable row has
complete evidence; justify any genuinely inapplicable mechanism-specific row.

| ID | Scenario | Required result |
| --- | --- | --- |
| OFF-01 | Approved cold boot without network access | Validate the complete boot chain, security floors, protected authority state, and time before applications start |
| OFF-02 | Older correctly signed EEPROM, verifier, OS, and recovery payloads | Reject every path below its applicable floor; no alternate boot path opens protected state |
| OFF-03 | Roll back the encrypted authority database or its backup | Detect stale memberships, permissions, trust keys, and consumed enrollment grants; never reinstate obsolete authority |
| OFF-04 | Interrupt a security-state commit at each durable boundary | Acknowledged changes remain effective; ambiguous state fails closed into bounded reconciliation or recovery |
| OFF-05 | Advance security state repeatedly | Demonstrate a sufficient lifetime transition budget and crash-safe authenticated commitments; ordinary credential renewal consumes no hardware counter transition |
| OFF-06 | Hardware and protected-storage mismatch | Refuse cloned or missing state, board/TPM substitution, TPM clear/removal, or unexplained continuity reset; do not create a fresh authority silently |
| OFF-07 | Clock rollback, invalid time, exhausted backup power, and extended power-off | Apply the qualified time policy; never disable certificate validity checks or revive expired authorization |
| OFF-08 | Local credential and trust-bundle renewal, expiry, and restart | Sustain autonomous local renewal with valid time, enforce expiry when renewal fails, and preserve identity and trust across qualified restarts |
| OFF-09 | Restore or recover after an interrupted update and obsolete backup | Recover without reducing floors or restoring revoked authority; meet the profile's explicit offline recovery promise |
| OFF-10 | Native OTP monotonic mechanism and lock enforcement | Prove irreversible transition behavior, safe partial programming, lock application on every boot, and protection against all authorized legacy boot paths |
| OFF-11 | TPM counter/state commitment and protected key release | Prove counter authorization, content binding, Pi/TPM association, and the boot policy that gates key release; demonstrate reset/replacement recovery |
| OFF-12 | Optional provider outage and owner-server outage | Preserve standalone local operation during provider failure; bound agent-only operation by its existing credentials and qualified restart behavior |

OFF-10 is specific to the native candidate; OFF-11 is specific to the TPM
candidate. OFF-06 must cover whichever hardware and storage binding the profile
actually promises. Software rehearsals may prepare scenarios, but rows covering
physical enforcement need physical evidence.

## Ordering, recovery, and decision

Enforce startup in this order: verified boot, hardware continuity and epoch
checks, protected-state validation/unlock, local Kaiba controller and SPIRE
Server, SPIRE Agent, then applications. Validate security-critical state
contents against hardware continuity; a matching counter value without a
content binding is insufficient.

Commit membership revocation, permission changes, trust-key changes, and other
security transitions durably before acknowledging success. Record how an
interrupted transition is reconciled and why neither an old disk snapshot nor
an old signed verifier can accept the previous state again.

Recovery must specify which data can be recovered, which secrets are lost,
which identity or enrollment instance must change, and what owner evidence is
required. An absent counter or stale backup is never automatic permission to
initialize a replacement fleet authority.

Publish one outcome for the pinned profile: **qualified native**, **qualified
TPM**, or **not qualified**, with references to every matrix result. Unknowns
keep the outcome not qualified. This matrix authorizes no OTP programming,
TPM clearing, signing, disk writes, or physical provisioning; those actions use
the provisioning repository's concrete reviewed campaign procedures.
