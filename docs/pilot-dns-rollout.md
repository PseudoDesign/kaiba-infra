# Pilot DNS rollout readiness

Status, 2026-09-29: **The owner accepted the Ace/Mako deployment target.
Software and host-composition validation passed, and the changes are published
in draft PRs. The protected source inventory is now verified and transfer
helpers are published with passing local checks. Both hosts passed temporary
dormant staging; their persistent boot profiles remain unchanged. No state
export, cutover or native end-to-end acceptance has occurred. Mako's expired
operational credential requires supported recovery before export/cutover;
Malak continues serving.**
Ace's [persistent identity pilot](persistent-identity-pilot.md) is installed in
`pilot.kaiba.pseudo.design`. That identity namespace does not itself establish a
DNS zone, an update endpoint, or permission to publish a device address. The
bounded LAN trial changed no public records, parent delegation or router resolver.
Public DNS deployment remains deferred.

## Accepted Ace/Mako deployment target

Malak is not a required product server. It was part of the first trial because
it currently holds the authoritative pilot database, admission services and
authenticated evidence. The accepted target puts runtime services on the two
existing Raspberry Pi hosts:

| Host | Target role | Runtime responsibility |
| --- | --- | --- |
| Ace (`192.168.8.214`) | Kaiba server | Existing SPIRE authority and local agent; fleet control plane and enrollment inventory; workload registry; DNS controller/publisher and writable primary |
| Mako (`192.168.8.247`) | Kaiba agent and DNS replica | Agent admitted to Ace's owner fleet, local workloads and a read-only replica with separate state and transfer credentials |
| Malak (`192.168.8.249`) | Operator workstation | Administration, provisioning and recovery; no dependency for ordinary fleet identity or DNS service |

This requires transferring the complete pilot control plane: its authoritative
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

Separate host compositions and a two-host replica module are now authored;
the first trial's profile ran both replica processes on Ace. Native acceptance must exercise
authorization, credential renewal, restart and signed DNS publication with Malak
disconnected, plus queries and outage recovery on Mako's actual replica. No
migration or Mako agent startup/admission has been performed. Two hosts on one
LAN do not establish high availability or qualify offline boot/rollback protection.

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
  software checks; neither helper has exported or imported live pilot state.
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
preparation. The source's fleet transport leaf covers Malak, so a refreshed
source request must authorize the new leaf under the retained CA before
transfer. Source operator credentials and transport/management CA
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
writes retain evidence for read-only reconciliation. The complete migration
check now passes **92 tests with zero skips**, including 16 endpoint cases; a
separate isolated user/mount-namespace regression passes against the real mount
boundary. This helper has not run on either device. Recovery and authority
activation precede its use, followed by a fresh installed-client identity check.

After the recovery prerequisite below, the remaining owner operations are
concrete and separate: refresh and inspect the source-bound transport request
and signer; fence Malak persistently and export both databases
and selected files into a recipient-encrypted archive; authenticate the source
ciphertext/manifest digests before private handoff; import into Ace's unused
isolated PG18 cluster and remap OS account ownership by name. The exporter uses
native logical dumps with all writers stopped, verifies complete table-content
and schema/sequence snapshots, and retains the source fence after errors.
Neither export nor import activates destination authorities. Target policy and
import receipt verification precede the separate activation, followed by native
renewal/restart/DNS acceptance with Malak disconnected. An ambiguous operation
requires readback of the same intent; it never justifies restarting both writers
or initializing replacement issuer state.

Native device preflight found a prerequisite before those source mutations:
Ace successfully authenticated to the current `/pilot/self` endpoint and its
credential remains valid until October 3. Mako's request failed with
`invalid_certificate`; its installed operational certificate expired at
`2026-09-28T08:03:32Z`, although the local enrollment phase still says `verified`.
That phase is not proof of current credential validity. The supported recovery
path must preserve the existing identity and reconcile current source authority
state before export/cutover and the complete two-host acceptance. This requires
an explicit Mako recovery packet, additive Fleet and issuer grants, and an
updated source serving guard. After successful recovery and current `/pilot/self`
readback, take a fresh protected inventory and regenerate the source-bound
transport and target-policy packets. **The previously prepared owner transport
signing command is superseded and must not run against the old inventory.** No
replacement identity or re-enrollment is assumed. Malak's source authority
remains running; no recovery grant, source fence or export has been applied by
the migration helpers.

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

The software slice is published in draft PRs. Ace ran its candidate under test
activation; this did not establish a qualified or persistent LAN deployment. Its
review boundaries are:

| Repository and branch | Prepared change | Local validation |
| --- | --- | --- |
| [Fleet PR 30](https://github.com/PseudoDesign/kaiba-fleet/pull/30) | Explicit current-pilot inventory adapter; schema-qualified parent reads; separate workload tables and operator grant/readback client; identity-preserving server promotion; additive Ubuntu station review-packet renderer and bounded installer | Go race tests and real PostgreSQL role/mTLS checks; combined SPIRE/DNS application VM; 14-check persistence/promotion VM; 23 station preparation/installer tests and isolated PostgreSQL 18 validation |
| [DNS PR 4](https://github.com/pd-codex/nixos-kaiba-network/pull/4) | Opt-in isolated primary and two replica processes, runtime-generated persistent TSIG keys, narrow source firewall and explicit private-address allowance | 15-check DNS VM, module evaluation, formatting and workflow checks |
| [Host PR 15](https://github.com/PseudoDesign/nix-pseudo-design/pull/15) | Disabled-by-default Ace composition with exact peer addresses and SPIFFE identities | Native enabled candidate built and test-activated on Ace; protected boot/storage/existing service comparisons passed; booted and persistent generation 10 unchanged; disabled Ace and Mako closures unchanged |

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
managed-secondary configuration; the new Ace composition is tracked above.
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

## Acceptance deferred from the first trial

These checks remain outstanding. The expired station packet and its topology
are historical preparation; the accepted Ace/Mako deployment needs a fresh
composition and current-admission checks.

1. **Activate current pilot admission.** The previously installed
   [workload registry](https://github.com/PseudoDesign/kaiba-fleet/blob/c7d13f8ecd3e8d98108a2c6eb4787c550405e7c2/docs/spiffe-live-dns.md)
   reads the original `enrollments` lifecycle, while Ace's real pilot membership
   uses `pilot_enrollments`. The prepared explicit adapter verifies current
   pilot policy, immutable evidence, active credential and instance, including
   expiry, recovery and authority outages. Do not manufacture rehearsal
   `enrollments` rows. Bind the DNS workload to the actual enrollment through an
   operator-reviewed mapping; `ace-pilot-20260929` is presently the identity
   probe's instance, not an existing DNS admission decision.
2. **Accept the target host composition.** The first trial pinned tested DNS
   packages/modules and exact identities. A future persistent switch requires
   complete native acceptance. Preserve the authority and probe, retain isolated
   desired state and runtime credentials, and complete the control-plane
   transfer before removing Malak from the runtime path.
3. **Qualify a fresh LAN arrangement.** The first trial used Ace's loopback primary
   at port `15352`, LAN replicas at `15353`/`15354`, local controller at `18443`,
   and a planned Malak registry at `18446`; Mako's replica was not deployed.
   Review the proposed numeric DNS assignment
   `001` against current admission. Generate dedicated credentials through runtime
   provisioning; integration-test TSIG fixtures are not deployment credentials.
4. **Validate before considering delegation.** Query the prepared authorities directly,
   verify current-admission denial and outage behavior, restart persistence,
   publisher updates and both observers. Public rollout is a later decision;
   once selected, review the exact parent-zone
   record change. After publication, verify through an independent recursive
   resolver and an outside-LAN client; LAN success alone does not prove public
   reachability.

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
