# Pilot DNS rollout readiness

Status as of 2026-09-29 08:23 UTC: **Ace LAN candidate test-activated;
pre-station checks passed; station installation and end-to-end acceptance pending**.
Ace's [persistent identity pilot](persistent-identity-pilot.md) is installed in
`pilot.kaiba.pseudo.design`. That identity namespace does not itself establish a
DNS zone, an update endpoint, or permission to publish a device address. The
bounded LAN trial changes no public records, parent delegation or router resolver.
Public DNS deployment remains deferred.

## Selected LAN rollout

Keep `pilot.kaiba.pseudo.design` as the chosen namespace and exercise DNS through
direct queries to isolated LAN listeners. Do not change parent delegation,
public endpoint records or the router resolver. The current pilot database and
admission services stay on Malak (`192.168.8.249`). A local workload registry
uses their existing current state and authenticated authority records. A
station SPIRE Agent joins Ace's owner authority through a source-restricted LAN
listener; the authority, local agent and probe identities remain stable.

Ace hosts the SPIFFE updater/controller, publisher and isolated primary plus
two read-only DNS replica processes. Explicit LAN-only configuration permits
private addresses for this qualification; the production default continues to
reject them. Separate local replica processes can test transfer and outage
handling, but do not establish independent failure domains or Internet DNS
availability. The actual current pilot instance and a separate operator grant
must authorize the updater; the probe installation label is not fleet admission.

Native acceptance depends on a reviewed station deployment. The workstation
account cannot read the root-protected pilot configuration or run passwordless
sudo. The read-only [station preflight](../scripts/pilot-lan-preflight.py)
exports allowlisted public configuration and the existing Ace enrollment tuple,
without private keys, database credentials or database changes. Ace's candidate
has been built, checked and test-activated; the owner's station installation
command and end-to-end acceptance remain pending.

## Prepared LAN implementation and evidence

The software slice is published in draft PRs. Ace is running its candidate under
test activation; this is not yet a qualified or persistent LAN deployment. Its
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
persistent systems remain at generation 10; no persistent switch of the LAN
candidate has been performed. The final published dependency lock evaluates to
the same candidate closure, and disabled
Ace and Mako evaluate unchanged. Final station registry/operator packages
passed locally. The station preparation refinement at Fleet
`869a8184c8a773f7a4d811ac2f74a7ba0c4ef49b` passed fourteen renderer tests.
It accepts an explicit maximum duration capped by current serving and credential
deadlines, and transfers only the newly created private review packet to its
named reviewer. The subsequent installer is pinned to published Fleet
`17b5a8ca7124a9eb6e5aa31c8fad91dba17818da`; runtime package and host pins remain
at `66ee0d6`.

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
reviewed station packet is now bound to cleanup at `2026-09-29T08:52:37Z`; its
prepared join grant expires at `2026-09-29T08:32:58Z`. These deadlines describe
this attempt only and do not authorize a later retry. Station installation must
still recheck live admission, and its native receipt, initial grant/readback,
signed publication and replica queries have not yet been accepted.

The trial's bounded cleanup stops the new DNS applications and Knot processes,
and the station bridge removes only its own firewall and socket ACL changes.
Encrypted authority, agent and workload state must be retained. After acceptance
or failure, restore the retained generation 10 configuration through the guarded
manual test-activation procedure and verify identity, storage and existing
services. This is not an automatic Nix rollback or a hardware rollback test.

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
| Ace, reserved LAN address `192.168.8.214` | Standalone SPIRE, Hydra/PostgreSQL and existing pilot credentials; baseline SPIRE listens on loopback | Test-activated local updater/controller/publisher, writable hidden origin and two isolated read-only replicas |
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

## Concrete implementation sequence

1. **Activate current pilot admission.** The previously installed
   [workload registry](https://github.com/PseudoDesign/kaiba-fleet/blob/c7d13f8ecd3e8d98108a2c6eb4787c550405e7c2/docs/spiffe-live-dns.md)
   reads the original `enrollments` lifecycle, while Ace's real pilot membership
   uses `pilot_enrollments`. The prepared explicit adapter verifies current
   pilot policy, immutable evidence, active credential and instance, including
   expiry, recovery and authority outages. Do not manufacture rehearsal
   `enrollments` rows. Bind the DNS workload to the actual enrollment through an
   operator-reviewed mapping; `ace-pilot-20260929` is presently the identity
   probe's instance, not an existing DNS admission decision.
2. **Accept the staged host composition.** The tested DNS packages/modules and
   exact identities are pinned, and Ace's candidate is test-activated. Complete
   station acceptance and the checks below before considering a persistent
   switch. Preserve the existing authority and probe. Keep the current enrollment
   authority authoritative; copying its database to Ace would be a separate
   service transfer. Retain isolated desired state and runtime credentials.
3. **Qualify the selected LAN arrangement.** Use Ace's loopback primary at
   port `15352`, LAN replicas at `15353`/`15354`, local controller at `18443`,
   and Malak registry at `18446`. Review the proposed numeric DNS assignment
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
