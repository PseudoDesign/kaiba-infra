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

Fleet's parent stack is reviewed and merged in dependency order:

| Change | Merged revision |
| --- | --- |
| [SPIRE foundation, PR 27](https://github.com/PseudoDesign/kaiba-fleet/pull/27) | `cb1598744703883acea0843e43253a4e28743cf7` |
| [Live workload registry, PR 28](https://github.com/PseudoDesign/kaiba-fleet/pull/28) | `f7f230771f4ad2e21fc4fab276430591db22c753` |
| [Persistent identity pilot, PR 29](https://github.com/PseudoDesign/kaiba-fleet/pull/29) | `e7070111863e7660e965d7ef4ad811015e8bf8de` |

Each exact PR head passed native x86_64/ARM64 enrollment and its applicable
identity/DNS/persistent-pilot VM workflow. The remaining LAN integration PR 30
now targets `main`; renewal PR 31 remains its child. Deployment still uses the
recorded earlier closures until all deployment gates pass.

[Fleet PR 31](https://github.com/PseudoDesign/kaiba-fleet/pull/31) implements owner
create/read/revoke APIs, restricted delegation routes, independent issuer checks,
exact durable grants, a durable controller and protected workers. Same-key issuer
CA continuation preserves original scope records and grants through an append-only
transition. Revision `6f9a6c4419a0b9a0cf462539eeec4cf21d3cc726` passed native x86_64,
ARM64, imported-control-plane and identity VM CI. The local authenticated fresh
observation renderer and append-only publication path are implemented and tested.
Measured-bound controller-plan generation, host continuity, startup receipts and
live activation remain open.

[Provisioning PR 96](https://github.com/PseudoDesign/kaiba-provisioning/pull/96)
adds explicit protected-client trust continuation without replacing device keys.
Its x86 and native ARM64 checks passed. Its first x86 workflow failed fetching the
private historical Fleet dependency. The full historical campaign check now runs
and passes in Fleet's private CI without changing physical campaign pins or giving
public PRs a private-repository credential. Require that separate result; a green
public workflow alone is not evidence that the private integration ran.

Malak's retained CA custody inventory completed at **2026-10-01T04:49:23Z**
using the existing recovery slot. Both management and transport certificates
matched their expected fingerprints; adjacent keys were regular, single-link,
root-owned 0600 files. The read-only mapping closed and all source services
remained inactive. Keys were not opened by the inventory. The preceding token
inspection failures are retained; no token reset or reenrollment was performed.

Candidate-only CA continuation tooling now matches each retained key to its CA,
locks key memory before reading it, records durable signing intents, and validates
successors using the production Go certificate verifier. Eleven candidate/custody-owner
tests and thirteen source custody tests pass locally. Packaged delegation/controller/trust
checks, including the original eight signing fixtures, pass at
`/nix/store/mvbrp0qkm5d2avcn3c4gjgif221h96aa-kaiba-pilot-renewal-delegation`.
The source preparation packet proposes CA expiry `2026-11-08T00:00:00Z`; packet
SHA-256 is `6c68821d438a6c1732fa6dbb987abf4ff37881682b4a6489228573d295fcf554`.
The source packet completed at **2026-10-01T05:01:00Z**, preparing management and
transport candidates on Malak. Its read-only source mapping closed and source
services stayed fenced. Ace prepared its issuer candidate at **05:06:34Z** after
eight native ARM64 candidate tests passed. All three candidates retain their
original public keys and expire **2026-11-08T00:00:00Z**. They remain uninstalled.

| CA role | Candidate certificate SHA-256 (DER) |
| --- | --- |
| Management | `9ca29292727434255339b29185a15343b823414075e76aea71c9de27bb52a372` |
| Transport | `67d38f19e4a308b6305c9d5b6e79d9349b0eba90da5d3f7abe6c3a7b6f436379` |
| Issuer | `1182d5b2915b3a223eda4e473c415ee787cfe6951c57df6526eed7d9ec5cc2cd` |

Candidate preparation does not activate a term, extend access, or replace private
keys. Coordinated trust installation, leaf continuation, host continuity and the
stopped-writer backup were deployment prerequisites; the backup is now verified below. The operator handoff copies
only the two public source CA certificates after checking these exact fingerprints;
the signing keys remain on their custody hosts.

The separated historical NVMe campaign check now passes in private Fleet CI, and
provisioning's x86 and native ARM64 checks pass. The service-owner support at Fleet
revision `46c2dda5bb83a6ac239033a48402b6a4fd4745e7` passed native x86_64/ARM64,
imported-control-plane, identity, renderer and historical NVMe CI. No live
credential/deadline was changed, and no
thirty-day term or unattended observation has started.

### Trust staging and service-certificate checkpoint

The public CA handoff passed exact fingerprint checks. All three public candidates
are staged on Ace and Mako, still uninstalled. The original migration manifest and
deadline remain unchanged. The new trust-staging guard accepts a pinned owner
receipt only under that original deadline and retains the exact replaced artifacts
in its checked archive. It cannot activate the thirty-day term.

Validation passed: 147 packaged migration tests without skips, nine guard tests,
Nix module evaluation and 27 native ARM64 staging/policy tests. The imported
control-plane VM passed with retained memberships across restart, archive-tamper
denial, recovery after archive restoration and original-deadline enforcement.
The VM result is `/nix/store/c8v0hwg0klki2vggg25815p39pfc1g9b-vm-test-run-kaiba-imported-pilot-control-plane`.
Its first attempt exposed asynchronous dependent-unit shutdown in the test
orchestration; that failed attempt remains recorded. The successful rehearsal
explicitly stops and checks every pilot unit. Live stopped-writer procedures must
do the same rather than treating target shutdown as proof that all writers stopped.

Ace prepared six public CSRs using its retained service keys. Independent checks
on Malak verified their signatures and exact original certificate fields before
accessing any CA key. Ten signing/reconciliation tests passed both locally and
natively on ARM64. The source signing packet requests uninstalled leaf candidates
expiring `2026-11-07T00:00:00Z`, bounded by the continued CAs. Packet SHA-256:
`3eb0a0a7a5a354caa4c11bfe892d5f7e90786f64df0d78a9aa1610b6a752f2f1`.
The local recovery-passphrase ceremony completed at **2026-10-01T07:39:28Z**.
All six receipts match the exact plans, retained keys and unchanged identity
fields. The source mapping closed and source services stayed fenced. Its private
result SHA-256 is
`99b228c924c6d39b3a4af1f5305eec5eac05ca539b0cbc11445891efb224352b`.

The owner completed a separate private handoff of only the public candidate
certificates. Ace independently checked them against its live predecessors and
staged them at **07:45:02Z**. All four authority services remained active and
existing certificates/configurations were unchanged. No private keys were opened
by handoff or staging. Thirteen local leaf-candidate tests now include incomplete
handoff, changed-history, appended-content and expiry rejection. Candidate
preparation and staging do not install certificates, replace keys, or activate
renewal. Existing service certificates and private keys remain on Ace.

These staging and candidate changes are pushed as Fleet revision
`588cf5ad83e0c17bbe4f47ff9b0f4f4772a88f37`; native x86_64/ARM64,
imported-control-plane, identity, renderer and historical NVMe CI all passed.
Packaged delegation/controller and certificate checks passed at
`/nix/store/342j5fyc3y60ngnrhfcmqg0fwm2b5swn-kaiba-pilot-renewal-delegation`.
The private checkpoint digest is
`b0719e7e64a71a05265cc59a2e960af9816b8244cd625c29b2487cdc0486c515`.

Fresh pre-continuity baselines at **07:55Z** passed on Ace and Mako: retained
device-state and membership hashes, original encrypted storage, expected services,
synchronized time, fresh workload credentials and all twelve DNS queries from
each host. Malak's six loaded source fences still match the accepted post-reboot
definitions, with no authority listeners. No live trust or deadline changed.

The cold-backup helper covers `/srv/kaiba-pilot`, including the private
Fleet/issuer PostgreSQL cluster and policy/issuance history. It uses the running
pilot's PostgreSQL 18 tools, not the host-default PostgreSQL 17 tool. It encrypts
to Ace's retained migration recipient and verifies full local decryption against
file bytes, owners and permissions. Separate SPIRE state and Malak's fenced CA
container are outside this backup operation and remain unchanged.

The first isolated backup VM rehearsal passed decryption/readback, retained
memberships, watchdog restoration and preservation of unrelated PostgreSQL. A
later exact-wrapper rehearsal refused a guard unit that finished shutdown in
`failed` state with no process; restoration succeeded and the failed attempt was
retained. The corrected predicate accepts only inactive/failed units with PID
zero, rejects running/transitional states, and passed its native ARM64 regression.
The final wrapper VM passed in 375.67 seconds, including restoration of a service
with DNS primary's guard dependency. Its immutable result is
`/nix/store/ki864knwsck3407qax95km5dk7srz6pa-vm-test-run-kaiba-imported-pilot-control-plane`.
Four cold-backup and six operation tests also passed natively on ARM64.

The real stopped-writer backup completed at **2026-10-01T08:28:49Z**. All 1,864
files passed full authenticated decryption and comparison of bytes, ownership and
permissions. Cipher SHA-256:
`37b98b25f4101052478ba186f3bec011c03aa933ae6ba8c24873634478243989`.
The archive and retained age recovery key remain private on Ace; their exact
locations are in the private operation receipt. This same-disk backup supports
maintenance rollback; it does not demonstrate disk-loss recovery or a restored
SQL instance.

Post-backup acceptance at **08:29Z** passed retained Ace/Mako device state and
membership, expected services, fresh workload credentials and all twelve DNS
queries from each host. Hydra, regular PostgreSQL and both SPIRE services retained
their process IDs and invocation IDs. Ace's original authority services and DNS
primary resumed, then the independent restoration timer was disarmed. Original
system/configuration pins and the access deadline stayed unchanged. This backup
is not the separate database-only outage acceptance test. No trust continuation,
delegation activation or unattended observation has started.

Set the pre-deadline decision checkpoint at **2026-10-02T14:00:00Z** (October 2,
10 a.m. EDT), leaving twelve hours before the original deadline. At that point,
record whether a qualified successor can activate or a separately reviewed
existing-protocol bridge is needed. Preserve the stopped state/expiry boundary if
neither is ready. The twenty-four-hour acceptance requirement is not shortened.

### Durable publication checkpoint

Fleet revision `3986be1a5e62e584e9aff98b792fc8cdcc25aaa6` and provisioning revision
`4da4de1c5895ac99e93aefb8bc036449f82a58bd` add a confined publication command and
compatible readers. Each predecessor operation retains its original observation,
records and evidence in an immutable journal. One atomic append exposes the
complete batch to both readers without restarting services or changing original
selections. Reader grants pin exact principals, enrollment instances and the
thirty-day delegation interval.

Go race tests passed for publication, renewal and observation-reader packages.
The packaged cross-repository check passed at
`/nix/store/fn6068wqmy4jms7khkmhypdwp4y7jm1h-kaiba-pilot-renewal-delegation`:
five delegation, three controller, four publication and five trust-continuation
scenarios, plus certificate preparation tests. Publication used real mTLS and
disposable PostgreSQL with a synthetic observer. It verified new-record reads on
a retained TLS connection, unchanged reader processes, original record availability,
retry reconciliation, changed-observation and revocation denial, and unchanged
disposable memberships. It does not qualify hardware observation or unattended
live renewal. The compatible consumer has a separate test dependency pin;
historical enrollment and physical-campaign pins are unchanged.

The publication receipt deliberately does not authorize renewal. The controller's
plan producer still needs authenticated new-record acceptance and measured trust,
host-continuity and SPIRE registration bounds. Compatible host configuration,
management/worker credentials, coordinated CA/leaf rollout and activation remain
open. None of this publication code is enabled on the live pilot. Exact-head CI,
remaining native fault acceptance, the full twenty-four-hour observation and
reviewed merged deployment are still required.
