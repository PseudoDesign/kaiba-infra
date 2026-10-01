# Finish and ship the LAN installation

Owner-approved implementation scope: 2026-09-30. Target domain:
`pilot.kaiba.pseudo.design`. Ace owns authority and primary DNS; Mako retains
its admitted identity and replica; Malak is an operator workstation with its
former authority fenced. This milestone is **in progress**, not closed.

## Deadline and deployment gates

The existing deadline remains **2026-10-03T02:06:35Z** (October 2, 10:06 p.m.
EDT). Do not edit it in place. Activate an explicit validated successor or
preserve state and allow access to expire. If implementation misses the
pre-deadline checkpoint, any bridge must be separately reviewed and use the
existing renewal protocol; approval of the overall plan is not evidence that
a bridge was issued.

The read-only expiry inventory on 2026-10-01 found installed issuer, management
and transport CAs expiring October 24 and reader certificates expiring October
10. These cannot support a new thirty-day term. Explicit trust/credential
rollover, preserving device keys, original grants and issuance/recovery history,
is a prerequisite to term activation. No term has been activated.

## Implementation and acceptance sequence

1. Complete an expiry inventory on both devices and a pre-deadline checkpoint.
   Implement the additive renewal-delegation contract, owner create/read/revoke
   APIs, restricted automation principal and issuer verification. Pin exact
   enrollment instances, keys, scope and accepted evidence gaps. A term is
   exactly thirty days; individual authorizations are at most seven days.
2. Implement a durable Ace controller and protected workers on both devices.
   Check every five minutes; start below the smaller of 48 hours or half the
   issued lifetime. Keep one unfinished operation per predecessor. Reconcile
   lost responses with its original ID; ambiguous issuance or cutover blocks
   progress. Refresh evidence within existing freshness rules. Changed evidence
   or exceptions requires owner review. No workstation dependency or automatic
   replacement identity is allowed.
3. Add a versioned host continuity transition, preserving migration proofs and
   appending successor records. Coordinate authority guards, admitted-startup
   receipts, admission records and SPIRE registration expiration. Expose term
   and credential expiry, renewal state and blocked reason in CLI/systemd health;
   warn locally at seven days, 24 hours and six hours before term end.
4. Rehearse disposable-member revocation, replacement denial, permission changes
   on retained TLS connections, continuing-consumer workload rotation, bounded
   SPIRE/private-database outages, and publication/removal replica convergence
   within 60 seconds. Live faults need watchdog restoration and bounded windows.
   Preserve real memberships, Hydra and regular PostgreSQL. Exercise lost replies,
   restart, revocation during renewal, duplicate execution, stale records and
   term expiry in automated fixtures; preserve failed attempt evidence.
5. Capture fresh baselines and verify a stopped-writer encrypted backup of the
   real authority, issuer history and policy. Deploy compatible readers, guards
   and disabled components first. Activate the exact approved delegation only
   after trust and acceptance gates pass. Renew Mako first, then Ace, using
   retained keys and initial 24-hour canary credentials. Prove successor access,
   predecessor denial, stable identity and complete history before enabling
   unattended renewal. Subsequent credentials may last up to seven days, clipped
   by every applicable bound.
6. Observe **24 actual hours** with no induced updater restarts or shortened DNS
   intervals. Require an unattended operational renewal on each device, at least
   two ordinary six-hour DNS lease renewals, fresh workload credentials, healthy
   access and matching primary/replica DNS. Ambiguous operations, unexpected
   identity changes or new service failures fail acceptance. Verify persistent
   configuration and supported restarts with recovery access available.
7. Review and merge parent PRs before children: contracts and DNS interfaces,
   then Fleet, then provisioning consumers and host configurations. Preserve
   immutable historical test pins; update deployable pins to reviewed merged
   revisions, rebuild and deploy those exact closures. Repeat original-storage,
   retained-key, service/credential/updater, twelve DNS-query and source-fence
   acceptance. Record deployed revisions and close only after every gate passes.

Required checks include contract conformance, renewal state machines,
authorization, real PostgreSQL, Go race, Nix modules, VMs and native ARM64.
Missing CI is not a pass. Record skipped checks and their reasons.

## Evidence and handoff

The [bounded physical campaign](offline-qualification.md) is complete. Original
encrypted storage is restored; Ace generation 14 and Mako generation 15 passed
the recorded return checks. No additional drive swaps or destructive power
tests are planned. This does not establish hardware rollback protection,
secure boot, autonomous offline operation or full production qualification.

Keep raw credentials, rows and backups private. Publish sanitized outcomes and
evidence hashes. The handoff must include the deployed revision manifest,
delegation expiry and owner reapproval procedure, acceptance report, private
backup locations and follow-up issues for production installation and hardware
qualification. Public DNS and product installation/UI remain separate milestones.
Keep `full_qualification: false` throughout this LAN milestone.

## Implementation checkpoint, 2026-10-01

The contracts stack is merged through
[PR 15](https://github.com/pd-codex/kaiba-contracts/pull/15), revision
`8bf0dc6822805b151ad29c459896f85119f87e0b`; 124 contract tests pass locally.
The DNS stack is merged through
[PR 4](https://github.com/pd-codex/nixos-kaiba-network/pull/4), revision
`e1f18fbc355b70b2d87245288d4ebb837434cbdd`. Its exact PR head passed unit,
module, native ARM64 package and DNS VM checks. These are reviewed dependency
revisions, not a claim that the live deployment has changed.

[Fleet PR 31](https://github.com/PseudoDesign/kaiba-fleet/pull/31) implements owner
create/read/revoke APIs, restricted delegation routes, independent issuer checks,
exact durable grants, a durable controller and protected workers. Same-key issuer
CA continuation preserves original scope records and grants through an append-only
transition. Revision `7b0ce6a510ec69be6700ab89397d9a5bf92c5403` passed native x86_64,
ARM64, imported-control-plane and identity VM CI. The local authenticated fresh
observation renderer and its unit/race tests are implemented; durable publication,
host continuity, startup receipts and live activation remain open.

[Provisioning PR 96](https://github.com/PseudoDesign/kaiba-provisioning/pull/96)
adds explicit protected-client trust continuation without replacing device keys.
Its native ARM64 checks passed. Its first x86 workflow failed fetching the private
historical Fleet dependency. The full historical campaign check is being moved
to Fleet's private CI without changing the physical campaign pins or giving
public PRs a private-repository credential. Require that separate result; a green
public workflow is not evidence that the private integration ran.

Malak's retained CA container was locked after reboot. The first custody inventory
stopped on the unavailable mount; the separate read-only inspection then stopped
before unlock on a token/keyslot assumption. The owner-provided nonsecret header
projection confirmed recorded token `1` points to slot `2`, with PIN and touch
required. The corrected inspection validates that actual association; seven
policy/cleanup tests pass. Read-only custody inspection still needs the owner's
local authentication. No source authority was activated, no live credential or
deadline was changed, and no thirty-day term or unattended observation has started.

Set the pre-deadline decision checkpoint at **2026-10-02T14:00:00Z** (October 2,
10 a.m. EDT), leaving twelve hours before the original deadline. At that point,
record whether a qualified successor can activate or a separately reviewed
existing-protocol bridge is needed. Preserve the stopped state/expiry boundary if
neither is ready. The twenty-four-hour acceptance requirement is not shortened.
