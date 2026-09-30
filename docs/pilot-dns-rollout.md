# Pilot DNS rollout readiness

Status, 2026-09-30: **The native Ace/Mako positive path, member restart and
workload-grant quarantine/restoration passed, plus bounded registry and primary-DNS
outage checks, replica restart with the primary absent, and passive Mako identity
renewal observations.**
The authority moved from fenced Malak to Ace with verified database and issuer
continuity; both installed clients authenticate to Ace with their retained
identities. Explicit DNS authorization, primary publication and matching
UDP/TCP queries on both hosts passed. Mako is admitted and retained its node and
key through Agent restart after grant removal. Exact-unit probes bracketed a
bounded wrong-unit no-identity observation. Native grant quarantine denied a
fresh updater request without changing intent state; restoring the same binding
allowed a fresh lease. Registry unavailability denied updates without changing
intent state; Mako retained DNS answers during the primary stop, and both
services recovered. Existing applications, device state
and the then-current boot selections were preserved through those earlier checks.
Software validation includes 135 migration tests with zero skips and the control-plane/DNS VMs.

Both controlled warm reboots passed: Ace then ran its persistent generation 12
with an explicit clock-wait unit and ordered authority startup; Mako runs its
guarded generation 15. Device and admitted identities, retained private state, fresh exact-unit probes,
existing applications and DNS passed post-boot checks. The pilot policy and
temporary workload registrations retain the original deadline,
`2026-10-03T02:06:35Z`; no extension is authorized or implemented. Broader native
credential-lifecycle checks and remaining outage/replication scenarios remain
open. The later attended workstation-power-off check passed within its recorded
bounds. Hardware/offline boot and rollback
qualification and public DNS deployment are separate tracks.
Full qualification remains false. The
later [Ace clean PoE cold-start](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-ace-cold-start-ordering-failure.json)
failed automatic startup because the imported-state mount preflight formed a
boot ordering cycle. Identity and state survived; affected services were
restored explicitly. Mako passed all 40 DNS samples, including 12 while Ace was
unavailable. The fix is now installed as generation 13, and the
[repeat attended clean PoE test](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-ace-clean-cold-start.json) passed automatic
startup without manual service starts. All 17 protected services, retained
identity/state, fresh exact-unit identity and DNS passed; PID1 reported no
ordering-cycle job deletion. Mako passed 73 DNS samples, including 55 while Ace
was unavailable. A separate tmpfiles missing-`sudo`-group warning remains;
its exit 65 is accepted by the installed unit. The
[initial native observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-ace-mako-lan-acceptance.json),
[grant quarantine observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-native-workload-quarantine.json)
and [bounded service-outage observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-native-service-outages.json)
record the dated results; [remaining native acceptance](#remaining-native-acceptance)
lists the unfinished work. Detailed preparation evidence follows.

The subsequent [replica restart observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-native-replica-restart.json)
records a new Mako DNS process serving its retained A/AAAA/SOA answers over UDP
and TCP while Ace's primary was stopped. Both hosts had independent restoration
guards, and both services recovered with unchanged credentials, applications,
device state and active revision-3 grant. This did not publish a new DNS update.
The [passive identity observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-native-identity-observations.json)
also confirms Mako's node renewed beyond its earlier expiry under the same
identity, with current cached trust and a fresh workload certificate after the
earlier one expired. Ace's exact-unit fresh fetch passed; that sampling interval
did not demonstrate Ace certificate rotation. Neither observation is Fleet
operational-credential renewal or a disconnected-workstation test.

The owner confirmed physical recovery access before the attended warm reboots.
The [persistence record](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/ace-mako-persistence.md)
separates the earlier encrypted rehearsals and boot-only installations from the
later [Mako](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-mako-warm-reboot.json)
and [Ace](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-ace-warm-reboot.json)
startup observations. Ace's generation 12 includes the upstream clock waiter;
actual monotonic timestamps verify its ordering before storage validation,
private PostgreSQL, import validation and Fleet startup. All four authority APIs
passed their post-boot checks. Mako's admitted-state guard started its retained Agent
without a new grant. During Ace's reboot, nine DNS query rounds on Mako passed
with fresh Ace-unavailable observations before and after each round; Mako's boot,
profiles and seven service identities stayed unchanged. This is bounded sampled
continuity, not continuous availability proof. The subsequent read-only
[connected sampler rehearsal](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-connected-collector-rehearsal.json) passed on both hosts with Malak
connected and no updater timer armed. Ace recorded its unchanged kernel-global
OOM-kill counter; Mako recorded unchanged per-cgroup OOM counters. No per-cgroup
OOM claim is made for Ace. The later
[attended workstation-power-off observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-30-attended-workstation-poweroff.json)
records the owner-reported 16:45–18:00Z power-off interval and network return
about two minutes after power-on. Both Pi samplers passed: installed-device
access, DNS and fresh exact-unit credentials beyond the longest prior workload
TTL remained available. A separately supervised updater restart produced a fresh
accepted lease after that TTL. This is an induced fresh update, not ordinary
six-hour renewal or same-process certificate rotation.

Malak returned on a new boot. Separate reconciliation verified its six retained
source fences, absent authority listeners and unset PID1 main-process execution
metadata. Root journal visibility was unavailable, so empty journals were not
used as proof. The original unchanged-workstation-boot verifier was preserved;
a separate supplement handles the owner-attested power-off and bounded network
return. The Pis stayed powered: this does not qualify Pi cold/offline boot, power
loss or rollback, and full qualification remains false.

Ace's [persistent identity pilot](persistent-identity-pilot.md) is installed in
`pilot.kaiba.pseudo.design`. That identity namespace does not itself establish a
DNS zone, an update endpoint, or permission to publish a device address. The
bounded LAN trial changed no public records, parent delegation or router resolver.
Public DNS deployment remains deferred.

## Accepted Ace/Mako deployment target

Malak is not a required product server. It was part of the first trial because
it held the authoritative pilot database, admission services and authenticated
evidence. Its retained source state is now fenced. The accepted target puts
runtime services on the two
existing Raspberry Pi hosts:

| Host | Target role | Runtime responsibility |
| --- | --- | --- |
| Ace (`192.168.8.214`) | Kaiba server | Existing SPIRE authority and local agent; fleet control plane and enrollment inventory; workload registry; DNS controller/publisher and writable primary |
| Mako (`192.168.8.247`) | Kaiba agent and DNS replica | Agent admitted to Ace's owner fleet, local workloads and a read-only replica with separate state and transfer credentials |
| Malak (`192.168.8.249`) | Operator workstation | Administration, provisioning and recovery; no dependency for ordinary fleet identity or DNS service |

The transfer includes the complete pilot control plane: its authoritative
database, signed records and evidence, issuer ledger and authority state,
trust/policy configuration, private runtime credentials and authenticated
service endpoints. Moving only the workload registry or station SPIRE Agent
would leave Malak in the authorization path. Preserve device/instance identities,
credential lineage and Ace's trust domain. Use an isolated PostgreSQL database
and roles on Ace while preserving Hydra. Prepare backup, destination readback,
one authoritative cutover and recovery checks; stale evidence and unavailable
authority must continue to deny authorization. The target policy verifier must
preserve the station's current storage and serving-window requirements.

The retained issuer scope hashes Reader configuration, including endpoint URLs,
file paths and certificate references. The source inventory confirms that the
issuer's canonical fleet callback uses `192.168.8.249:18444`. The prepared
issuer-only transport override dials Ace at `192.168.8.214` while retaining the
canonical URL, TLS name and scope inputs. A new transport leaf covers both
addresses under the existing transport CA and existing deadline; its private
key stays on Ace. Original configuration bytes and all original, active,
renewal-source and recovery-source scope rows remain preserved. Import must
verify scope equality; it must not rewrite scope rows to accept a host move.

Separate host compositions now run the replica on Mako; the first trial ran both
replica processes on Ace. Mako's admission, exact-unit identity, grant-free Agent
restart and actual replica queries passed after temporary activation. Native
grant quarantine/restoration also passed. Remaining acceptance covers membership
and credential lifecycle and remaining outage scenarios. The bounded attended
workstation-power-off check is complete. Two hosts on one LAN do not establish high availability or
qualify offline boot/rollback protection.

The new host profiles are disabled by default. Their disabled evaluations match
Ace's retained generation 10 and Mako's persistent closure exactly. Staging with
`enable = true` and `activate = false` selects an immutable deny guard and does
not autostart the new services. Active configuration requires the reviewed
policy guard and verified imported state. Ace's prepared
configuration keeps the imported issuer on loopback `18443`, places the DNS
controller on `18447` to avoid a collision, and uses separate registry `18446`,
fleet `18444` and private PostgreSQL socket `18445` interfaces.
The [host guide at `d97d72e`](https://github.com/PseudoDesign/nix-pseudo-design/blob/d97d72e03180d2ebf041e133bf9e4f380111023e/docs/ace-mako-pilot.md)
records the staged and active interfaces. Its
[composition receipt](https://github.com/PseudoDesign/nix-pseudo-design/blob/d97d72e03180d2ebf041e133bf9e4f380111023e/docs/observations/2026-09-29-ace-mako-composition.json)
records passing checks against the published dependency pins, including exact
disabled closure preservation. This is evaluation evidence, not host activation.

Native dormant staging passed on Mako at `2026-09-29T19:31:24Z` and Ace at
`2026-09-29T19:31:54Z`. Both hosts built the reviewed candidates natively with
Fleet `0bd55c5`, then applied them through `switch-to-configuration test` with
`enable = true`, `activate = false`. Selected existing application processes,
Ace's SPIRE processes, device state and directory, ownership, boot identity and
persistent system profiles were preserved. New pilot units were nonrunning
with no main process; imported authority state was absent. Both activations
reloaded DBus and the firewall; Ace also restarted tmpfiles setup and started
its boot automount/mount, `local-fs.target` and `systemd-timedated`. These checks
do not assert that every service or mount was unchanged. The
[sanitized host observation](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-lan-qualification/docs/observations/2026-09-29-ace-mako-dormant-staging.json)
records the temporary candidates and retained persistent baselines. Dormant
staging does not activate the authority or establish native end-to-end acceptance.

The application and migration qualification checks remain software evidence:

- The final two-host DNS VM passed eight groups: real cross-host AXFR/NOTIFY,
  credential-role separation, source restrictions, outage and journal restart,
  retained-key checks, and refusal to regenerate lost credentials beside
  surviving DNS state. This transport test does not exercise the SPIFFE
  application authorization path or qualify hardware.
- The imported Fleet control-plane VM passed eight groups using the four actual
  authority units and private PostgreSQL: missing-import denial, preserved active
  memberships and unrelated PostgreSQL, peer-role isolation, policy withdrawal,
  reviewed restart and deadline shutdown. Seven guard tests, six real PostgreSQL
  groups, module evaluation and all-system flake evaluation also passed. These
  fixtures contain synthetic state; no real device was migrated.
- The owner ran the frozen read-only inventory helper, and its private report
  was verified against the owner-provided SHA-256 digest. The helper has twelve
  passing tests. The inventory confirms the encrypted source mount, four
  authority roles, private PG18 cluster, two active pilot memberships, complete
  retained issuance/renewal history and unchanged serving deadline. It is a
  point-in-time inventory, not a coordinated backup.
- The exporter passed seventeen synthetic checks, including
  fence-before-stop ordering, a boot/process/deadline-bound PG-only permit,
  preservation after partial failure, refusal to overwrite prior attempts,
  full row-content drift detection and real age encryption/decryption with
  generated test keys. The importer passed a disposable PG18 logical
  dump/restore comparison using the same snapshot normalization. These are
  software checks; the subsequent native export/import result is recorded below.
- Transport signing passed sixteen focused tests; target-policy preparation
  passed eleven. They retain the source policy deadline and trust pins, verify the
  requested transport identity, and permit only the reviewed callback dial
  override. The complete migration Nix check passed **76 tests with zero skips**,
  including final import-receipt checks, real age archive/export-import coverage
  and disposable PG18 restore verification. Eight real PostgreSQL guard groups,
  issuer callback scope/history preservation and the control-plane VM also
  passed. Its follow-up readiness regression has nine checks: it deliberately
  holds one Reader authority unavailable, requires Fleet to deny access, then
  verifies authenticated readiness and unchanged memberships. These results
  are local software evidence, not live migration.

DNS CI also passed formatting/module checks, ARM package builds and VM topology
checks at `67574bb`. The Fleet and transfer-helper results cited above are
local validation; they do not imply a completed remote CI run for the new
transfer commit.

The migration must preserve one authoritative writer and the complete issuance
history. Ace now has a private age recipient key and transport CSR on its
existing encrypted root; only their public request material is used by source
preparation. The refreshed source request authorized Ace's new transport leaf
under the retained CA and unchanged deadline. Source preparation preserved the
serving leaf and services before the later export fence. Source operator credentials and transport/management CA
private keys remain on Malak. Operational issuer keys, Reader credentials,
signed records and full database histories are part of the encrypted transfer.
Source credential and record paths must be absolute; relative paths must not be
silently relocated during import. The staged host runtime uses
[Fleet `0bd55c5`](https://github.com/PseudoDesign/kaiba-fleet/tree/0bd55c576536c29825aada2f7ce6fa052a877402/nix/pilot-control-plane)
and [DNS `67574bb`](https://github.com/pd-codex/nixos-kaiba-network/blob/67574bb1fe88a60118c680d823ac2ddb7656975b/docs/lan-two-host.md).
The [published migration protocol](https://github.com/PseudoDesign/kaiba-fleet/blob/0bd55c576536c29825aada2f7ce6fa052a877402/deploy/pilot-migration/README.md)
records the implemented export/import, transport, target-policy and receipt
boundaries in [Fleet PR 30](https://github.com/PseudoDesign/kaiba-fleet/pull/30).

The subsequent [device endpoint helper](https://github.com/PseudoDesign/kaiba-fleet/blob/797a9e2b7de9f94ad5bd29ebe21420434cff2b7b/deploy/pilot-migration/device-endpoint.md)
changes only the retained Fleet URL after current authenticated admission on Ace.
It preserves credentials and history, keeps private backups on encrypted storage,
and publishes the replacement within the device's actual bind mount. Interrupted
writes retain evidence for read-only reconciliation. That change expanded the
migration check to **92 tests with zero skips**, including 16 endpoint cases; a
separate isolated user/mount-namespace regression passes against the real mount
boundary. Both native endpoint transfers subsequently passed on September 30
local time, after recovery and authority activation. Fresh installed Go client
`self` calls authenticated to Ace with the exact retained bindings and false
full-qualification status. Comparison against each private state backup
confirmed that only `config.fleet_url` changed.

The source export fenced Malak and encrypted both databases and selected files
for Ace. Verified import restored them into Ace's isolated PG18 cluster with OS
account ownership mapped by name. The exporter uses
native logical dumps with all writers stopped, verifies complete table-content
and schema/sequence snapshots, and retains the source fence after errors.
Neither export nor import activates destination authorities. Finalization and
separate temporary activation and both device endpoint transfers have passed.
The explicit DNS grant, publication and queries on the primary and actual Mako
replica have also passed, together with Mako admission and grant-free Agent
restart. The later attended workstation-power-off check also passed. Remaining
steps include broader native lifecycle and outage acceptance. An ambiguous operation
requires readback of the same intent; it never justifies restarting both writers
or initializing replacement issuer state.

Native preflight authenticated Ace but found Mako's installed operational
certificate expired. Mako's supported same-key recovery subsequently passed on
September 29 local time. The recovered credential is revision 2 with exactly
one successor issuance; the original identity, key and history are preserved.
Installed-key proof, fresh-process access and access after authority restart
passed. The result explicitly records full qualification as false.

Before export, the owner supplied a fresh
protected inventory, and its checksum and expected recovery changes were
verified. Recovery-aware export/import and target-policy verification now retain
the original policy, explicitly pin a completed-recovery proof, and reject
mismatched proof/schema before fencing or finalization writes. Before fencing,
the exporter also verifies the exact Ace/Mako memberships and compares all four
issuer scope pins with the recovery proof. The complete migration suite passes **135 tests with
zero skips**, including real age and
disposable PG18 checks. Ace's append-only preparation rebind passed nine native
fixture tests and actual host/key/storage checks, preserving its original keys
and receipt. That preparation did not import authority state.

Source preparation completed on September 29 local time, and its result was
verified. The completed recovery guard passed, private policy continuity was
recorded, and Ace's existing transport CSR was signed under the retained CA
without extending the deadline or changing source services. Its eleven synthetic
tests cover policy rejection, actual signing/readback, private output and
retained intent after failure. Ace's immutable target guard and active system
closure were then built natively. Build-time host checks passed,
including the expected denial when imported state is absent. Current and
persistent system profiles and existing service processes were preserved during
those checks. **The previously prepared
owner transport signing command is superseded and must not run against the old
inventory.**

On September 30 local time, the fenced encrypted source export succeeded and
the verified import on Ace established complete content, schema and sequence
equivalence for both databases. Finalization and subsequent temporary activation
passed. At that stage, Ace ran the activated profile on the same boot, preserving
its then-current persistent selection and existing Hydra, regular PostgreSQL
and SSH processes. The later boot-only installation is recorded above. The
promoted SPIRE server and agent are healthy. The target/import guards, isolated
PostgreSQL, four imported authority services, workload registry, DNS controller,
primary and publisher are active. Four Ace workload registrations bind exact
systemd units and users with the original deadline.

Authenticated native Reader resolution passed for both retained device records
with stable service invocations; independent active-binding checks matched the
devices. Malak's source fences remain loaded and match the sealed archive.
Both device endpoint cutovers are accepted following fresh installed-client
access to Ace and complete backup comparison proving only the Fleet URL changed.
The initial reviewed DNS grant was accepted; authenticated readback confirmed an
active revision-1 binding with `dns:update` permission. Ace's updater is healthy,
and its assigned address record is authoritative on both hosts. Twelve native
UDP/TCP queries matched, including matching serials; unsigned AXFR received an
explicit rejection. Desired, origin and observed publication generations agree.

Mako's native identity acceptance passed at `2026-09-30T05:17:27Z`: its admitted
node and key survived Agent restart after removal of the consumed grant. The
exact-unit probe succeeded before and after a same-user wrong-unit request
timed out after 5.057 seconds with no identity. This was a bounded
no-identity observation, not an explicit denial response. Its existing
applications, operational device state, current candidate, persistent baseline
and source fences were preserved, and its probe timer resumed. The native
positive path and member restart were accepted at that stage; later sections
record workstation-power-off acceptance. Broader lifecycle and outage checks
remain open. Startup from the subsequently
installed profiles passed in the later controlled warm-reboot observations.
Temporary activation does not establish full LAN or hardware/offline boot/rollback
qualification.

The subsequent native workload-grant check passed: the same binding moved from
active revision 1 to quarantined revision 2, then back to active revision 3.
A fresh request from the actual updater received HTTP 403 while the complete
intent tuple, including lease and `updated_at`, remained unchanged. Restoration
of the same binding allowed a fresh accepted lease. Both authoritative DNS
endpoints, Malak's source fence and original applications were preserved.
The current binding is active revision 3. This verifies fresh-request quarantine
enforcement and restoration; it does not establish reused-connection enforcement
or complete the broader credential lifecycle and outage campaign.

Two bounded native outage checks then passed and restored service. Pausing the
existing registry process caused a fresh actual updater request to receive
HTTP 503 `authorization_unavailable`, with all nine intent fields unchanged.
Resuming that same process produced a fresh authenticated registry response and
a newer accepted lease. Separately, stopping only `kaiba-lan-primary` left Mako
answering authoritative A, AAAA and SOA queries over UDP and TCP. After primary
restart, both endpoints matched and controller intent converged. The supervised
check units finished inactive with successful status; the binding remained
active revision 3, and source fencing, original applications and profiles were
preserved. These checks did not exercise SPIRE/database outages, a replica
restart while the primary was absent, or timed catch-up from a new publication.

## First LAN trial: topology and boundary

Keep `pilot.kaiba.pseudo.design` as the chosen namespace and exercise DNS through
direct queries to isolated LAN listeners. Do not change parent delegation,
public endpoint records or the router resolver. The current pilot database and
admission services stayed on Malak (`192.168.8.249`). The prepared local workload
registry would use their current state and authenticated authority records. A
station SPIRE Agent was to join Ace's owner authority through a source-restricted
LAN listener; the authority, local agent and probe identities remained stable.

Ace's candidate hosted the SPIFFE updater/controller, publisher and isolated primary plus
two read-only DNS replica processes. Explicit LAN-only configuration permits
private addresses for this qualification; the production default continues to
reject them. Separate local replica processes can test transfer and outage
handling, but do not establish independent failure domains or Internet DNS
availability. The actual current pilot instance and a separate operator grant
must authorize the updater; the probe installation label is not fleet admission.

The trial's native acceptance depended on a station deployment. The workstation
account cannot read the root-protected pilot configuration or run passwordless
sudo. The read-only [station preflight](../scripts/pilot-lan-preflight.py)
exports allowlisted public configuration and the existing Ace enrollment tuple,
without private keys, database credentials or database changes. Ace's candidate
was built, checked and test-activated. No owner installation receipt was available
when the trial expired, so station installation and end-to-end acceptance have
not been established.

## First-trial implementation and evidence

The initial software slice was published in draft PRs. Ace ran its candidate
under test activation; this did not establish a qualified or persistent LAN
deployment. The table preserves that first-trial scope and evidence; it is not
the complete current scope of the linked PRs.

| Repository and branch | Prepared change | Local validation |
| --- | --- | --- |
| [Fleet PR 30](https://github.com/PseudoDesign/kaiba-fleet/pull/30) | Explicit current-pilot inventory adapter; schema-qualified parent reads; separate workload tables and operator grant/readback client; identity-preserving server promotion; additive Ubuntu station review-packet renderer and bounded installer | Go race tests and real PostgreSQL role/mTLS checks; combined SPIRE/DNS application VM; 14-check persistence/promotion VM; 23 station preparation/installer tests and isolated PostgreSQL 18 validation |
| [DNS PR 4](https://github.com/pd-codex/nixos-kaiba-network/pull/4) | Opt-in isolated primary and two replica processes, runtime-generated persistent TSIG keys, narrow source firewall and explicit private-address allowance | 15-check DNS VM, module evaluation, formatting and workflow checks |
| [Host PR 15](https://github.com/PseudoDesign/nix-pseudo-design/pull/15) | Disabled-by-default Ace composition with exact peer addresses and SPIFFE identities | Native enabled candidate built and test-activated on Ace; protected boot/storage/existing service comparisons passed; booted and persistent generation 10 unchanged; disabled Ace and Mako closures unchanged |

Host PR 15 now also includes the Ace server and Mako member profiles, isolated
imported authority composition and real two-host DNS replica. Both hosts have
passed temporary active-profile acceptance as recorded in the
[current deployment status](#accepted-acemako-deployment-target) and subsequent
native observations above.

The station registry reads the existing `public.pilot_enrollments` through
`SELECT(id, data)` and `REFERENCES(id)` grants; it owns only a separate workload
schema. A decoy parent table in that schema cannot substitute for current
membership. Each authorization still checks the current authenticated pilot
evidence and expiry. The operator client sends one mutation and supports GET
reconciliation after an ambiguous response.

The station renderer prepares five additive systemd units and a review manifest.
It neither installs them nor changes the current serving window, database,
credentials or firewall. New services bind to the existing encrypted mount and
serving deadline. Protected station metadata and current admission must be
checked before producing the live packet.

The separate [station installer at Fleet `17b5a8c`](https://github.com/PseudoDesign/kaiba-fleet/blob/17b5a8ca7124a9eb6e5aa31c8fad91dba17818da/deploy/pilot-lan/README.md#explicit-installation-and-bounded-cleanup)
is published and passed 23 preparation/installer tests plus isolated PostgreSQL
18 validation. Before mutation it checks the immutable packet, current admission,
existing serving guards, peer authentication and exact database/socket privileges.
It creates only the reviewed bridge resources, arms deadline cleanup and supports
one explicit initial grant followed by authenticated readback. An ambiguous grant
is not retried. The existing UFW check required a narrow unit sandbox correction:
Unix, IPv4/IPv6 and netlink socket families, and write access only to the existing
root-owned `/run/ufw.lock`. The installer tests both immutable guards in that
sandbox before installing units; this does not change UFW policy.

The DNS VM tests the primary/replicas with the application services stopped.
The separate combined VM exercises the actual SPIFFE updater/controller and
registry against synthetic inventory. These complementary checks do not
establish the native LAN path through Ace's current pilot enrollment.

The prepared source revisions are Fleet
`66ee0d6aa6fa3747ad69566567f465af32c31580` and DNS
`2edf05378b3b2c88773dc95044408a50a20229fc`. The native Ace candidate built to
`/nix/store/ipk6rwq7h1rk4zpxyyym9s550f5i0ka7-nixos-system-ace-26.05.20260807.ee48b14`;
test activation reached its first probe at approximately `2026-09-29T08:18:42Z`.
The booted and
persistent systems remained at generation 10; no persistent switch of the LAN
candidate has been performed. The final published dependency lock evaluates to
the same candidate closure, and disabled
Ace and Mako evaluate unchanged. Final station registry/operator packages
passed locally. The station preparation refinement at Fleet
`869a8184c8a773f7a4d811ac2f74a7ba0c4ef49b` passed fourteen renderer tests.
It accepts an explicit maximum duration capped by current serving and credential
deadlines, and transfers only the newly created private review packet to its
named reviewer. The subsequent installer is pinned to published Fleet
`17b5a8ca7124a9eb6e5aa31c8fad91dba17818da`; that trial's runtime package and host
pins were `66ee0d6`. The new Ace/Mako preparation is a subsequent slice.

Native pre-station observation passed at `2026-09-29T08:22:35Z`: all fifteen
expected services were active, including Hydra, PostgreSQL and SSH; the identity
manifest, original agent alias, exact probe identity and public pilot enrollment
status were preserved. Four expiring registrations and the source-restricted
SPIRE listener at `192.168.8.214:8081` matched the reviewed configuration. The
controller had no accepted desired state and the primary and both replicas had
no assigned-device A/AAAA answers, as expected before the station grant. At
`2026-09-29T08:22:24Z`, the same updater user under an unregistered systemd unit
failed to obtain a workload identity. At `08:23:23Z`, an authenticated request
verified the exact controller SPIFFE identity and received HTTP 503 while the
station registry was unavailable; the real updater was then restored. These
checks do not prove station attestation, authorization, signed publication or
native outage recovery. Sanitized observations are tracked in
[Host PR 15](https://github.com/PseudoDesign/nix-pseudo-design/pull/15).

The owner ran the read-only station preflight at `2026-09-29T07:27:24Z`.
It confirmed the expected active Ace enrollment, current pilot policy and
Reader configuration; the observed credential expires `2026-10-03T02:06:35Z`.
This dated observation does not extend admission or the serving window. The
reviewed station packet was bound to cleanup at `2026-09-29T08:52:37Z`; its
prepared join grant expired at `2026-09-29T08:32:58Z`. Both are expired and cannot
be reused. No station installation receipt, initial grant/readback, signed
publication or native replica-query result was accepted for this trial.

Inspection at `2026-09-29T14:23Z` confirmed that the expiry timer had stopped all
seven new Ace DNS units. Guarded baseline restoration passed at `14:26:10Z`:
active, persistent and booted systems match retained generation 10, SPIRE listens
on loopback port 8081, and no trial DNS listeners remain. The original probe,
public enrollment and existing services were preserved. Authority and agent
state were retained. This was a manual configuration restore, not an automatic
Nix rollback or a hardware rollback test.

## Observed DNS and available hosts

Queries through `1.1.1.1`, followed by direct nonrecursive queries to
`pdns1.registrar-servers.com` at its observed address `156.154.132.100`, returned:

| Query | Observation |
| --- | --- |
| `pseudo.design NS` | `pdns1.registrar-servers.com` and `pdns2.registrar-servers.com` |
| `pseudo.design SOA` | `pdns1.registrar-servers.com`, serial `1779227272` |
| `pilot.kaiba.pseudo.design NS` | No delegation answer; the authoritative response contains the parent `pseudo.design` SOA |
| `pilot.kaiba.pseudo.design SOA` | No separate SOA answer; parent SOA returned |
| `*.pseudo.design A` | Authoritative answer `204.8.14.108` |
| `updates.pilot.kaiba.pseudo.design A` and `spire.pilot.kaiba.pseudo.design A` | Both resolve to `204.8.14.108`; an arbitrary unused name under the pilot namespace returns the same address |
| `updates.pilot.kaiba.pseudo.design AAAA` | No AAAA answer |

The wildcard explains why proposed endpoint names already resolve. These
answers are not evidence that SPIRE or the update controller is reachable at
those names. They are a dated observation, not an exported zone inventory.

The inspected
[`nix-pseudo-design` host configuration](https://github.com/PseudoDesign/nix-pseudo-design/tree/5ff9b5f3e161ba62f1e595338681fdaea3ff9dd6/hosts)
records the baseline for two existing deployment targets, before the LAN trial:

| Host | Baseline role and relevant boundary | DNS role |
| --- | --- | --- |
| Ace, reserved LAN address `192.168.8.214` | Standalone SPIRE, Hydra/PostgreSQL and existing pilot credentials; baseline SPIRE listens on loopback | First trial's local updater/controller/publisher, writable hidden origin and two replicas are stopped; baseline restored |
| Mako, reserved LAN address `192.168.8.247` | Public HTTP entry point, human identity, SSH CA, backups and existing applications | Read-only hidden origin P1 after service/resource review |

That inspected baseline has no authoritative DNS, publisher TSIG provisioning or
managed-secondary configuration; the current Ace/Mako composition is tracked
above.
Existing PostgreSQL for Hydra or human identity is not fleet enrollment
inventory. Ace and Mako share a
LAN and public entry point; using them together does not establish independent
public DNS availability.

The host's [LAN access record](https://github.com/PseudoDesign/nix-pseudo-design/blob/5ff9b5f3e161ba62f1e595338681fdaea3ff9dd6/docs/human-access.md)
reports that connections from inside the LAN to `204.8.14.108` time out. Router
overrides currently cover human-identity names. A DNS update endpoint needs its
own reviewed LAN route or split-DNS entry. Existing Mako HTTP reverse proxies
terminate TLS; updater-to-controller SPIFFE authentication instead needs an
end-to-end connection, such as a direct LAN route or reviewed TCP forwarding.

## Remaining native acceptance

Authority transfer, both device endpoint moves, the explicit DNS grant,
Mako admission with grant-free Agent restart and authoritative replica queries
are complete. Native workload-grant quarantine denial and exact restoration
and the bounded registry/primary-DNS outage checks also passed. Mako additionally
restarted its replica from retained state while the primary was stopped, and
passive sampling confirmed node renewal under its retained SPIFFE identity. The expired
station packet is historical evidence, not the next deployment step. Complete
the following within the unchanged `2026-10-03T02:06:35Z` deadline:

1. **Clean up the separate tmpfiles warning.** Generation 13 passed the repeat
   attended clean PoE test with LAN available, automatic service startup and no
   ordering-cycle job deletion. Resolve the missing `sudo` group referenced by
   `/etc/tmpfiles.d/sys-kernel-debug.conf`; retain the successful test and its
   accepted exit-65 warning separately from the failed generation-12 attempt.
2. **Credential lifecycle and remaining authorization boundaries.** Exercise
   membership revocation, instance replacement and renewal on the native
   deployment while preserving issuer scopes, identities and retained history.
   The completed workload-grant quarantine/restoration check does not substitute
   for these distinct lifecycle observations.
3. **Remaining outage and replication scenarios.** Exercise SPIRE and database
   outages and timed catch-up from new publication with keys, state and existing
   applications preserved. Registry pause/resume, primary stop/restart and replica
   restart while the primary is absent are complete within their recorded bounds.
4. **Longer unattended operation.** The owner-attested 75-minute Malak
   power-off, fresh workload identities beyond the longest TTL, installed-device
   access, DNS and one induced fresh update passed. Longer-duration operation
   and ordinary six-hour updater renewal remain separate observations; preserve
   source fences and the original policy deadline.

Controlled warm-reboot acceptance is complete for Ace generation 12 and Mako
generation 15, including admitted identity, retained state, automatic service
startup and DNS. Ace generation 13 additionally passed an attended clean
LAN-assisted cold-start. Offline boot and abrupt power-loss safety remain open.

Hardware qualification remains a separate campaign covering cold/offline boot,
clock continuity, rollback prevention and recovery. Public DNS deployment is
also separate: select real public authority endpoints and reviewed delegation
before checking independent recursive resolution and outside-LAN reachability.
No public records, parent delegation or router resolver changes are implied by
LAN acceptance.

The completed attended check used independent bounded samplers staged on
both Pis before Malak was powered off. The packet had first passed 68 focused
software tests and a connected rehearsal. The later traces retain credential,
installed-client, UDP/TCP DNS, lease and protected-state observations spanning
the owner-attested power-off interval. A separately scheduled one-use updater
restart supplied the post-TTL update. The changed workstation boot and delayed
network return were verified explicitly, with process-start metadata supporting
continued source fencing. These sampled results and the owner attestation do
not establish continuous availability at every instant or an autonomous monitor.

Outside the explicit LAN profile, the updater discovers publicly routable addresses on local interfaces; it does
not discover a router's WAN address. Private `192.168.8.x` addresses alone will
produce no endpoint. The observed wildcard address cannot be assumed to be
Ace's reachable application address. Select either a verified directly routed
address or an explicitly configured gateway/application route before enabling
updates. The test-only non-global-address override is not the public solution.

## Record and delegation options

**Keep the parent zone and delegate only the pilot child zone.** This matches
the existing publisher's RFC 2136/TSIG model: Ace P0, an explicitly selected P1,
and at least two real public-authority endpoints supplied by a selected
secondary service or independently deployed authorities. No such public
secondary endpoints have yet been selected. Namecheap documents
[subdomain delegation with NS host records](https://www.namecheap.com/support/knowledgebase/article.aspx/434/2237/how-do-i-set-up-host-records-for-a-domain/).
The review packet would contain:

| Location | Record or setting to review |
| --- | --- |
| Existing `pseudo.design` parent zone | NS records with relative host `pilot.kaiba`, pointing to the selected real public nameservers; preserve the apex nameservers and unrelated records |
| New pilot zone on P0 and its replicas | SOA and the same public NS set; glue only if the selected nameserver arrangement requires it |
| Pilot zone | Explicit endpoint records for `updates` and, only if a remote SPIRE service is later enabled, `spire`, with verified addresses/routes |
| Pilot zone | Publisher-managed `pi-<assigned-number>` A/AAAA records; the workload does not choose its own name |

Delegation removes reliance on the parent's wildcard beneath the child zone.
Prepare required endpoint records in the child before the delegation change.
Do not list the private P0/P1 addresses as public nameservers or invent public
addresses for these hosts.

**Keep records in the existing provider zone.** Static endpoint records can be
prepared there, but they do not exercise the Kaiba dynamic publisher. Automated
record updates would require a separate supported provider adapter; the current
publisher is not a Namecheap API client. Confirm the account's DNS product and
API eligibility first: Namecheap's [API FAQ](https://www.namecheap.com/support/knowledgebase/article.aspx/9739/63/api-faq/)
excludes PremiumDNS/FreeDNS management, and its
[`setHosts` operation](https://www.namecheap.com/support/api/methods/domains-dns/set-hosts/)
replaces the submitted host-record set. No provider API credentials or account
capabilities were inspected or inferred from DNS answers.

## Runtime credential interfaces and missing inputs

The existing modules already separate these interfaces:

- Registry: private `environmentFile` containing `KAIBA_DATABASE_URL`, the exact
  authority/tenant/security-domain policy, and explicit operator/controller IDs.
- Updater/controller: local Workload API sockets and exact expected service
  SPIFFE IDs. An SVID is not an operator admission grant.
- Publisher: `credentials.publisherTSIGSecret`, a runtime file containing the
  update secret. Knot consumes a separate runtime-format key include.
- Hidden origins/secondaries: separate update, origin-transfer and
  public-transfer keys, with `credentialUnits`/`provisioningUnits` ordering.

No secrets need to be supplied in chat or copied into source or the Nix store.
The remaining deployment inputs are:

1. The chosen public-authority arrangement and its real NS names/addresses and
   transfer support, or a deliberate decision to implement a provider adapter.
2. Access to review/apply the parent-zone record change and provision the
   selected provider/transfer credentials through private runtime files.
3. The permitted public application/update route and address policy for Ace,
   including the LAN route. `204.8.14.108` is observed existing infrastructure,
   not an approved new destination mapping.

The pilot admission adapter, explicit workload mapping and bounded LAN trial do
not depend on resolving those public-deployment inputs.
This rollout does not qualify boot integrity, hardware identity, offline time,
authority rollback protection, DNS redundancy or full production admission.
