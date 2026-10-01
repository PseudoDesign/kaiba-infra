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

## Current implementation checkpoint — October 1

The renewal components and provisioning consumer are merged: Fleet PR 31 at
`3d4f332dfef599063105c7ac9ec7d49e16314377` and provisioning PR 96 at
`5f40fbbf4dae1d9328ad440addfd65143e3ebd18`. Fleet PR 32 subsequently merged at
`424d147dba78fe2ff3eabf58dda98d9928824a5c`, exposing explicit deployment packages
from that provisioning revision. All six selected PR 32 CI jobs passed, including
native x86_64/ARM64, imported-control-plane and identity VM checks. A separate
local rehearsal passed fifteen publication, controller and trust scenarios with
the merged package combination. Historical fixture pins remain unchanged.

[Authority continuation PR 33](https://github.com/PseudoDesign/kaiba-fleet/pull/33)
merged at `f65d3950a35c48867bc146c66d12d2667380f588` after all six selected CI
jobs passed. It adds optional,
owner-pinned successor records and fresh local term checks before network
services start, with no Fleet API boot dependency. Eleven continuation boundary
tests, the original nine guard tests, module checks and nine isolated PostgreSQL
guard groups pass locally. The native rehearsal accepts the actual Go/SQL reader
output through the Python guard. Its separate database role is checked for exact
read access, including denial of inherited, PUBLIC, column, sequence and grant
option privileges.

[SPIRE expiry PR 34](https://github.com/PseudoDesign/kaiba-fleet/pull/34) merged
at `36ede3589a13785e030ec69a4fb09fc176476a8c`, also with all six selected CI
jobs passing. Its stock SPIRE fixture proves an upstream CA's absolute expiry
bounds the issuer chain and X.509 leaf, survives restart and unavailable upstream
certificate files, and denies issuance after actual expiry. JWT issuance is
explicitly disabled in this fixture. Registration expiry alone is not a signing
cap; this result does not qualify the live registration or bundle transition.

[Fleet PR 35](https://github.com/PseudoDesign/kaiba-fleet/pull/35) at `dbbcc3f`
and [provisioning PR 98](https://github.com/PseudoDesign/kaiba-provisioning/pull/98)
at `9ed2f75` remain drafts. They add root-owned observation consumption,
optional measured refresh before a controller tick, and authenticated inspection
of the protected client's effective installed trust. Existing status responses
and historical fixture pins remain unchanged. The root file boundary passed a
NixOS VM check as an unprivileged reader; Go race and module checks passed.
Seven local cross-process scenarios with actual mTLS and disposable PostgreSQL
verified trust reads before/after renewal and restart, wrong-principal denial,
and denial after membership/delegation revocation. Current CI is still pending;
the new optional native trust mode awaits a merged provisioning deployment pin.

PR 35 also adds the explicit native publication-store integration. The import
guard permits exactly the observation/admission publication directory under a
validated continuation, checks matching term/member scope and numeric ownership,
and preserves all other immutable file checks. Only the publisher writes; the
two record services gain group read access. Four boundary-test groups, the nine
original import tests, eleven continuation tests, Nix module evaluation and a
VM with actual root/publisher/reader ownership pass. No publication directory or
batch is initialized by enabling this option.

A separate read-only custody inventory is prepared for the owner/station
management certificates retained on fenced Malak. Five public-metadata tests and
thirteen existing read-only mapping/cleanup tests pass. The local recovery-slot
inspection still needs owner authentication. Service candidate certificates do
not establish the lifetime of owner administration or term reapproval access.

Fresh read-only checks at 18:54–18:58 UTC confirmed Mako's retained membership,
seven expected services and all twelve primary/replica DNS queries. Ace's
retained state, membership, workload and all twelve DNS queries also pass their
targeted checks. Its full host baseline does **not** pass: Hydra's queue runner
is inactive after a clean stop at 17:05 UTC. The source of that stop has not been
established; owner clarification is pending before restoration. No service was
changed during these checks. Malak's six source services remain fenced and
inactive, its authority listeners are absent, and its source mapping is closed.
The failed Ace baseline and an earlier inconclusive Mako sample are retained.

[Host PR 15](https://github.com/PseudoDesign/nix-pseudo-design/pull/15) at
`7fa6d53` now selects the merged Fleet packages and merged DNS interface
`e1f18fbc355b70b2d87245288d4ebb837434cbdd`. Host composition, member-guard and
retained-device checks pass; unchanged derivations were reused where applicable.
Hardware and regular service inputs are unchanged. These candidates have **not**
been installed: Ace generation 14 and Mako generation 15 remain the recorded
running deployment. No delegation, unattended timer or 24-hour observation is
active, and the original deadline remains in force.

Activation still requires the current certificate/configuration verifier and
reviewed operation producer, confined validity observation, SPIRE signing limits,
coordinated publication/trust installation and native restoration rehearsal.
Then run the actual Mako/Ace canaries, remaining fault acceptance and 24-hour
observation before final merged-revision deployment and closure. The successor
guard alone does not satisfy those gates.

The latest private checkpoint SHA-256 is
`fd319b9effda961f2db9cf78a75120ef9d698a1ec8d907e464ded9d999f91168`.
Its predecessors are
`b0c71b5f8b1f5cc32d7b151ac57fdcbb58a49ee8c4df3b774cdd4bb8143a02d4` and
`d75e52741fe90dd7d2c84229dea64d84ec4eefb82484f978df967db576e1ed7d`.
Failed local fixture and unauthenticated-fetch attempts are retained with their
corrections; none changed a live host.

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

Follow-up work is tracked separately in
[production installation, infra issue 7](https://github.com/PseudoDesign/kaiba-infra/issues/7)
and [production hardware qualification, provisioning issue 97](https://github.com/PseudoDesign/kaiba-provisioning/issues/97).
Neither issue moves a required LAN acceptance gate into a later milestone.

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
Measured-bound controller-plan generation is now implemented; its native validity
observer, host continuity, startup receipts and live activation remain open.

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
plan producer now checks authenticated new-record acceptance and consumes separately
observed trust, host-continuity and SPIRE registration bounds. Its native observer
and compatible host configuration,
management/worker credentials, coordinated CA/leaf rollout and activation remain
open. None of this publication code is enabled on the live pilot. Exact-head CI,
remaining native fault acceptance, the full twenty-four-hour observation and
reviewed merged deployment are still required.

### Measured plans and confined service credentials

Fleet revision `3a30d72fb0f32a61b0f8d50b80584f4b150b9d5d` adds versioned plan
preparation and exact pending-operation reconciliation. Plans retain the observed
trust, continuity and registration limits, source references, observation-age
limit, predecessor and operation ID. Lost-reply retries preserve the original
request and records. A shorter live limit blocks an unfinished operation without
silently shortening its authorization or issuing another credential.

The complete local packaged check passed, including five delegation, three
controller and five publication/plan scenarios,
trust-continuation checks and certificate preparation tests. Go race checks passed
for the pilot and publication packages. The plan fixture uses actual fixture
certificate dates but **synthetic** host and SPIRE-registration observations.
Production observer wiring and the versioned authority/member startup transitions
remain required. The workload registry's delegation-bound transition is implemented
in the checkpoint below; its live configuration and privileges remain to be deployed.
Do not enable timers with hand-written validity claims in place of those adapters.

Fresh read-only checks at **09:17–09:18Z** passed retained memberships, expected
services and twelve DNS queries per host. Mako's first baseline collection failed;
that attempt was retained, and a subsequent diagnostic collection passed. No
service, credential installation or deadline changed.

Eleven credential-preparation tests cover the five confined service profiles,
scope/expiry rejection, interrupted key/CSR/signing operations and lost-reply
reconciliation. Candidate preparation installs no certificate and activates no
delegation. Operational signing instructions and custody details remain in the
private handoff. The checkpoint SHA-256 is
`131c5be9897099b5f7fee688e7ab14f2f56464bd74ddf66081b5863ac8d0e8cf`.

Provisioning's documentation parent [PR 94](https://github.com/PseudoDesign/kaiba-provisioning/pull/94)
is reviewed and merged at `2fc247199f8b03cca85b7e3c20b24fc6197d6648`.
The physical-evidence parent [PR 95](https://github.com/PseudoDesign/kaiba-provisioning/pull/95)
now targets `main` and includes the previously tested CI isolation fix at
`b0ad66059e5211989328832667ccdbc8b80ce99a`; historical physical pins are unchanged.
Its new checks and Fleet's latest native/VM checks are still pending at this
checkpoint. Skipped hardware jobs are not passes. Remaining reviews, merged
deployment, native faults, retained-key canaries and the actual twenty-four-hour
observation still gate closure. No thirty-day term is active.

### Verified service candidates and workload continuity

All five confined renewal-service certificate candidates passed signature,
original-CSR, role, key and validity checks and are staged on their destination
hosts. They remain uninstalled. Read-only checks at **15:05–15:06Z** passed
retained memberships, expected services and all twelve DNS queries per host.
Mako's first collection failed and was retained; its subsequent diagnostic
collection passed. At **15:24Z**, Malak's six former authority units remained
inactive behind their loaded fences, with no authority listeners or source mapping.

Fleet revision `e6c0e415562b67bc241f4e1d05711cee8ec0e015` adds the explicit
workload continuity transition. It pins the original bindings and the approved
delegation, reads current authority under the lifecycle lock on every request,
and accepts only matching delegated renewal successors after policy refresh.
A recovered original binding can be pinned; a later recovery cannot inherit that
permission. Revocation and unavailable authority deny access on retained TLS
connections without reverting to the original policy. Existing DNS grants stay
intact, and short authorization results are clipped to current validity bounds.

The full pilot Go race suite and the registry race suite against disposable
PostgreSQL passed. The packaged registry check also passed, including renewed
policy access, revocation over the same TLS connection, outage/recovery, expiry
clipping, read-only SQL privileges and rejection of writable-schema authority
decoys. CI now runs the PostgreSQL check on native x86_64 and ARM64; checks for
this revision are pending. The preceding Fleet revision passed all its native
and VM CI. Provisioning PR 95's selected checks passed; its skipped hardware and
older-image jobs remain explicitly unqualified.

The private checkpoint SHA-256 is `cd7d2aa110c3ca3ca3b2a9b56134a3b867a8a79f97951c60e9cdb56383fd501d`.
Native validity observation, authority/member startup transitions and coordinated
host/trust installation still gate activation. No thirty-day delegation or
unattended observation has started. The original deadline and
`full_qualification: false` remain unchanged. Remaining reviews, merged deployment,
native faults, canary renewals and the actual twenty-four-hour run still gate
LAN milestone closure.

### Authenticated term reader and prepared member continuation

Fleet revision `a2a69985e17d41e2b04c6dcc70af89d074eae44c` adds a restricted
host-term read. It checks the latest delegation and retained membership under
the renewal/cutover lock. Only that enrollment's worker reader may use it;
revocation, expiry, changed identity/key/issuer/permissions and unavailable
authority deny startup permission. The CLI independently validates the exact
contract and pinned term. Offline contract verification reports a non-current
result and cannot satisfy the startup guard.

Host revision `9833cf765e8726d5eefed0d71386a3d1ada0055e` adds an optional Mako
continuation receipt and reader configuration with immutable hashes. The
original receipt, admitted SPIFFE node and cached keys remain intact. Activation
must predate the original cutoff; the new term must last exactly thirty days;
the authenticated read must be fresh; and the cached node certificate cannot
outlast the term. The option defaults to disabled and is not installed live.

Local validation passed: pilot Go race tests, 22 member-guard tests, the two-host
Nix module check and the packaged renewal rehearsal (five delegation, four
controller and five publication scenarios, plus trust/certificate checks).
The real local PostgreSQL/TLS fixture exercised the new reader after same-key
cutover and restarts, then proved outage and revoked-membership denial. An
initial test fixture used unsupported nanosecond timestamps; that failed attempt
was retained and the corrected microsecond fixture passed. At this checkpoint,
the new Fleet revision passed native x86_64/ARM64, imported-control-plane,
identity, renderer and historical-campaign CI. The preceding `e6c0e4`
revision passed all six checks. Synthetic tests do not establish native rollout
or unattended acceptance.

Read-only captures at **16:04Z** passed Ace's 17 services, Mako's seven services,
retained memberships and twelve DNS queries on each host. At **16:06Z**, Malak's
six former authority units were inactive with PID zero and loaded fence checks;
authority listeners and the source mapping were absent. Private fence files were
not reopened. No live services, keys, credential installations or deadlines were
changed. The private checkpoint SHA-256 is
`974554ee9c48a084864df99be90db68ff794538cedb6d4350cdc72d76509d4b8`.

Provisioning PR 95's source review and 20 inventory/observer plus seven disk-guard
tests passed. Its README conflict with the merged documentation parent was
resolved at `208bd60fab6395eea73ea30e4638db67ba844d14`, retaining the observations
and clarifying the later physical campaign. All selected fresh checks passed,
including native ARM64. It merged at `abd1d963cebb6e1926a414aef78ed754ac887a2e`;
immutable physical-image and Fleet pins are unchanged. The workflow skipped the
older-verifier-image and hardware jobs according to its selection policy; these
are not additional hardware passes.

The next activation gates remain Ace's versioned authority transition, the
native confined validity observer and coordinated SPIRE issuance limits.
SPIRE documents registration `entryExpiry` as
[data cleanup, not a security boundary](https://spiffe.io/docs/latest/deploying/spire_server/).
Its timestamp alone cannot qualify a validity observation: certificate lifetimes
and issuance must also be bounded by the applicable authorization and term.
Then complete coordinated trust/host installation, Mako/Ace canaries, remaining
native faults, the full twenty-four-hour observation and reviewed merged
revision deployment. The current cutoff remains **October 2 at 10:06 p.m. EDT**;
no thirty-day delegation or unattended observation is active.

### Reviewed parents merged; local authority startup read prepared

[Fleet PR 30](https://github.com/PseudoDesign/kaiba-fleet/pull/30) merged at
`45db927823cf819c02387b3a6c1df67a5433b6a2` after source review and all five selected
native/VM/renderer checks passed. The exact-head local review replay passed pilot,
workload registry/operator and wire race tests, 23 LAN tests, and 132 migration
tests. Three migration tests were skipped locally because that invocation lacked
the isolated PostgreSQL/age setup; the packaged CI supplies those dependencies.
The renewal child now targets `main`. Its squash-history conflict resolution
verified that merged main was byte-identical to the child's existing parent,
then preserved the validated renewal tree.

Provisioning PR 96 now also targets `main`. Revision
`0cf14a1` rechecks clock certainty, forward time, the owner packet and the current
credential interval after the authenticated authority read and immediately before
saving trust continuation. The protected-client and publication race suites pass,
including clock loss, rollback and approval/credential expiry during that read.
Failed attempts do not change retained state. Fresh CI remains the merge gate.

Fleet revision `5d1a3996ad2f27708dd36a1f9e9eeddbbe920861` adds
`kaiba-pilot-authority-term` for Ace's post-database, pre-API startup phase. It
requires the exact local peer socket and uses a read-only READ COMMITTED
transaction under the lifecycle lock. It reads schema-qualified authority tables,
checks the latest pinned delegation and every retained membership, and reports
only sanitized scope/expiry data. It performs no migrations or initialization and
cannot use TCP, passwords, fallback connections or cached authority state.

The pilot race suite and packaged renewal rehearsal pass. The latter exercises a
SELECT-only reader role, successful reads with Fleet stopped, database outage and
recovery, retained-key cutover, member/delegation revocation and stale search-path
decoys. The packaged result is
`/nix/store/d309ha6b4w92is8sir2kdawyxym9ad15-kaiba-pilot-renewal-delegation`.
It includes five delegation, five controller and five publication scenarios,
plus trust/certificate checks. The earlier build that omitted an untracked source
file is retained as a failed attempt; the corrected candidate passed. ARM64/VM CI
for the new revision is pending.

The local reader does not itself implement the versioned authority transition or
SPIRE issuance guard. Upstream SPIRE 1.15.2
[workload signing](https://github.com/spiffe/spire/blob/v1.15.2/pkg/server/api/svid/v1/service.go)
passes the registration's requested TTL to the CA; its
[credential composer interface](https://github.com/spiffe/spire/blob/v1.15.2/pkg/server/plugin/credentialcomposer/credentialcomposer.go)
does not expose X.509 validity fields. Therefore registration cleanup or a
composer attribute alone is insufficient to enforce an absolute term cutoff.
Qualify the actual signing lifetime and shutdown enforcement before activation.

No live host, deadline, private key or credential installation changed during
these reviews. Ace generation 14 and Mako generation 15 remain the deployed
baseline. The authority transition, confined validity observer, coordinated trust
installation, canaries, native fault acceptance, twenty-four-hour unattended run
and final merged-revision deployment remain open. No term is active and
`full_qualification` remains false.

Read-only SPIRE inventory at **16:42Z** found nine registrations: five expire
at the existing pilot cutoff, while the Ace probe and Ace/Mako/Malak aliases
have no entry expiry. The installed agent and default X.509 TTLs are one hour.
The explicit continuity operation must bound the intended Ace/Mako registration
set and preserve Malak's exclusion; it must not automatically carry the old
Malak alias into the new term. No registration was changed by this inventory.
The first inventory parser expected an object where Nix serialized a singleton
list; the corrected read retained that actual shape and collected public settings
only. Registration expiry remains a cleanup measure, not the signing cutoff.

The private parent-merge/implementation checkpoint SHA-256 is
`6435efeeae4ee0a6af818c09df38dec7ff231ab977542d0fc764dd030c98b783`.

### Host-foundation review and merge

[Host PR 14](https://github.com/PseudoDesign/nix-pseudo-design/pull/14) merged at
`d5ccc0fc8e6a97f15c81633297523f0d89931d9f`. Review found and corrected the
activation helper's use of `systemctl is-active` with several unit names, which
succeeds if any one is active. It now checks each service and automount
individually. ShellCheck, Bash syntax and three isolated health-check scenarios
passed without invoking live service actions. Nix reproduced the exact recorded
generation-10 closure, `ylpbjk8jzr195l7yn7f713sgjfimicbs`, so the helper correction
does not change that system composition. This repository exposes no PR CI for
this head; the recorded native installation and reproduced closure are the
evidence, not a missing-CI pass.

Host PR 15 now targets `main` at
`a785a9ba9757dd2737646df3bdc37e757d8998c4`. The merge verified the parent changed
only that helper, then preserved the LAN child's existing configuration and
prepared member guard. No host was deployed or restarted. Provisioning
`0cf14a19674b1b5a6a544ffde91988c7e9e6db84` has passed all selected fresh checks,
including native ARM64 operator packages and x86 core checks. Fleet `5d1a399`
has passed both native architectures, imported-control-plane, renderer and
historical-campaign checks; the identity VM was still running at this update.
Renewal and host deployment gates above remain open.
