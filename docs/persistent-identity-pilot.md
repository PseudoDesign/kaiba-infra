# Persistent identity pilot on Ace

Update, 2026-09-30: the standalone installation below remains Ace's persistent
baseline. A later two-host profile temporarily promotes that same authority
for the LAN pilot, preserving its identity and state. See the
[current LAN rollout](pilot-dns-rollout.md) for the latest deployment status;
the loopback-only scope and observations below describe the original phase.

Status: installed persistently on Ace and verified at
`2026-09-29T06:09:10Z`, using the owner-selected SPIFFE trust domain
`pilot.kaiba.pseudo.design`. Guarded test activation, explicit initialization,
persistent switch, fresh SSH access, and a post-switch identity probe passed.
A subsequent controlled warm reboot passed at `2026-09-29T06:44:11Z`;
the earlier native SPIRE smoke used temporary state and completed cleanup;
it is separate evidence from this installation.

## Selected scope

Ace runs a local SPIRE Server, SPIRE Agent, and one dedicated Workload API
probe under the standalone role. This is the persistent identity foundation
for standalone Kaiba, not the complete controller, enrollment, or application
installation. The authority listens on loopback. This phase adds no remote
member listener, provider enrollment, fleet admission, workload-registry grant,
DNS publication, or migration of the existing enrolled pilot identity.

| Setting | Selected value |
| --- | --- |
| Host | Ace, Raspberry Pi 5 Model B Rev 1.1 |
| Role | `standalone`, identity services only |
| SPIFFE trust domain | `pilot.kaiba.pseudo.design` |
| Logical device ID | `ace` |
| Enrollment-instance label | `ace-pilot-20260929` |
| Network exposure | Loopback SPIRE authority and local Unix Workload API |
| Hardware assurance | Unqualified; existing storage/unlock profile retained |

The trust domain is an identity namespace. Selecting it does not create a DNS
record, configure public TLS, or expose a network service. Future names such as
`spire.pilot.kaiba.pseudo.design` and `updates.pilot.kaiba.pseudo.design` can
separate the remote identity endpoint from DNS-update service traffic. Those
names are planned choices here; neither endpoint nor its DNS records
is implemented by this phase.

Host configuration belongs in
[`nix-pseudo-design` PR 14](https://github.com/PseudoDesign/nix-pseudo-design/pull/14),
recorded at `5ff9b5f3e161ba62f1e595338681fdaea3ff9dd6`.
It imports the fleet identity-pilot module and selects the fleet's tested SPIRE
and probe packages without replacing Ace's existing host package inputs.
Reusable service modules and bootstrap behavior belong in
[`kaiba-fleet` PR 29](https://github.com/PseudoDesign/kaiba-fleet/pull/29), tested
at `c7d13f8ecd3e8d98108a2c6eb4787c550405e7c2`. The pinned
[module guide](https://github.com/PseudoDesign/kaiba-fleet/blob/c7d13f8ecd3e8d98108a2c6eb4787c550405e7c2/docs/spiffe-persistent-pilot.md)
describes initialization and recovery boundaries.
This document records rollout boundaries and evidence; it does not make host
configuration a second infrastructure implementation.

## Bootstrap and workload boundary

The pilot distinguishes a fresh installation from lost or partially restored
authority/agent state. Initialization is an explicit operator action through
`kaiba-identity-pilot-initialize.service`; merely enabling the module leaves an
uninitialized installation stopped. Its durable bootstrap manifest and root
bundle live under `/var/lib/kaiba/identity/pilot-bootstrap`, separately from the
server and local-agent state. Pre-start guards compare the configured IDs,
manifest, authority key and database bundle, agent key and unexpired
certificate, admitted node, and exact workload selectors. Inconsistent
established state blocks startup instead of silently replacing the authority,
grant, or identity. A missing manifest skips ordinary startup; explicit
initialization still refuses remaining authority or agent state. The companion
`kaiba-identity-pilot-bundle.service` provides the initialized authority's trust
bundle for the agent. Bundle restoration is allowed only from the existing
guarded authority; it does not reconstruct missing authority or admission
state. The ten-group VM rehearsal passed these software continuity checks.

This guard is software continuity checking: it cannot detect restoration of a
complete older disk snapshot and does not establish hardware rollback
protection. Startup requires the host time service to report synchronization.
The one-hour agent credential lifetime and disabled automatic rebootstrap mean
that prolonged downtime can require explicit recovery. This initial pilot
does not establish autonomous offline startup.

The initial workload is `kaiba-identity-pilot-probe.service`, selected by both
that exact systemd unit and the `kaiba-identity-pilot-probe` user, with Workload
API access. Its exact identity is:

```text
spiffe://pilot.kaiba.pseudo.design/device/ace/instance/ace-pilot-20260929/workload/identity-probe
```

The probe fetches once at startup and every five minutes. Repeated fetches
can show that the service continues obtaining credentials; they do not prove
credential rotation within one process. Record that behavior separately if a
long-running watch is exercised. The VM separately proved rotation with a live
source. Ace denied a request from the correct user running under the wrong
unit. Certificate issuance demonstrates workload identity only. The
configured instance label is not an admitted fleet inventory instance, and it
confers no `dns:update` permission or production membership.

Retain authority and agent state on the existing encrypted root filesystem,
with separate service ownership and restricted access. Workload credential
rotation must not replace the trust domain, bootstrap a new node, or require
manual activation of each certificate serial. Service restart must reuse the
enrolled agent state without needing its consumed bootstrap grant. Missing or
inconsistent established state needs explicit recovery, whose trust and
membership implications must be reviewed before replacing it.

## Preserve the installed host

Ace is already an infrastructure host with Hydra and PostgreSQL active. The
earlier inventory's small service sample was incomplete; it does not justify
treating Ace as an empty or disposable machine. Preserve Hydra, PostgreSQL,
human-access integration, existing enrolled pilot state, and their access paths.

The pre-change configuration is the merged `nix-pseudo-design` tree at
`8ec7763670d0d4722162251cc4eb2f5e00432b54`. It matches the inspected source tree
at `9264275ecc43b3c0e5046b855777b129c592933e`, which evaluates to the pre-change
active system:

```text
/nix/store/f4q82s6kzy6y4q943y9v9nsm64c9s0xp-nixos-system-ace-26.05.20260807.ee48b14
```

Retain this known working closure and compare the candidate's kernel, initrd,
fstab, storage-unlock helper, existing service units, and pilot mount/account
metadata before activation. The identity rollout must preserve kernel 6.18.42,
the root-backed `/home` layout, disabled swap, and Ace's dedicated pre-HKDF
OTP-derived LUKS recipe. Ace does not use the shared fresh-install HKDF layout;
changing its unlock scheme or salt would not reproduce its existing key.
Password fallback is disabled in the installed hardware profile. Do not run
disko, `nixos-anywhere`, an unlock migration, firmware update, or OTP/TPM
operation as part of this service installation.

The activation helper checked the kernel, initrd, kernel modules, fstab,
crypttab, existing Hydra/PostgreSQL/SSH/pilot unit definitions, and pilot
metadata before both `test` and `switch`; all comparisons passed. Mako's
evaluated configuration was unchanged. The previous Ace system is retained at
`/nix/var/nix/gcroots/kaiba-identity-pilot-before`, with boot generation 9 kept
for reviewed recovery. The new persistent system is generation 10.

The existing enrolled pilot uses UID/GID `994:988`, a mode-0700 state directory,
a mode-0600 single-link state file, and a `nosuid,nodev,noexec` self-bind mount.
Compare public identity status and metadata without reading or copying private
pilot credentials. The new identity services must not replace that state.

Ace has nested `/boot` and `/boot/firmware` automounts. A prior activation
started the firmware mount directly and triggered emergency mode, interrupting
networking. Follow the host's
[guarded activation procedure](https://github.com/PseudoDesign/nix-pseudo-design/blob/8ec7763670d0d4722162251cc4eb2f5e00432b54/docs/human-access.md#future-deployments-and-recovery):
start the outer automount, enter `/boot`, start the firmware automount, enter
`/boot/firmware`, verify both automounts and the actual VFAT source partition,
then run activation from that same shell. Hold this mount context during both
`test` and `switch`; do not directly start `boot-firmware.mount`.

Recovery must use a generation compatible with the current root-backed home
layout. Older generations requiring the removed home LV can enter emergency
mode; do not select historical boot entries blindly. NixOS generation rollback
does not restore database state or prove that an old authority snapshot is
safe. The installation acceptance below did not reboot Ace. The subsequent warm-reboot
record is separate evidence and does not establish cold boot or recovery.

## Acceptance record

The host's sanitized
[native acceptance report](https://github.com/PseudoDesign/nix-pseudo-design/blob/5ff9b5f3e161ba62f1e595338681fdaea3ff9dd6/docs/observations/2026-09-29-ace-identity-pilot.json)
records successful guarded test activation, explicit initialization, persistent
switch, fresh SSH access and a post-switch probe at `2026-09-29T06:09:10Z`.
Both the active and persistent system point to:

```text
/nix/store/ylpbjk8jzr195l7yn7f713sgjfimicbs-nixos-system-ace-26.05.20260807.ee48b14
```

Ace obtained the exact probe SVID and denied the same user from the wrong
systemd unit. The probe could not access authority keys or the admin socket.
Server/agent restart reused the authority, admitted node and registration while
the consumed grant was absent. Existing public enrollment status was unchanged,
existing services including Hydra and PostgreSQL were healthy, and there were
no failed units. That original installation report explicitly marks hardware qualification, reboot,
and DNS publication as untested; the later warm-reboot record is additive.

The booted system remained
`80qsyq2nvpx0d8g0c5jwm6912qmp9yc4-nixos-system-ace-26.05.20260807.ee48b14`.
That historical boot link is distinct from the pre-change active closure above;
this test did not reboot Ace. It does not establish that an older generation is
a safe rollback target for the current storage layout.

The synthetic VM passed ten groups: uninitialized activation does not mint;
partial initialization is retained and denied; killed initialization stops
daemons and blocks partial retry; explicit initialization consumes its grant;
root-owned output and repeated initialization preserve identity; wrong-unit
denial and live-source rotation; cold VM reboot preserves identity; clean
SQLite restart preserves sidecar ownership; missing durable state and
configuration drift fail closed; and bundle restoration uses the guarded
existing authority. Its result flags both hardware and offline rollback as
unqualified. Cold VM reboot is separate evidence from physical boot on Ace.

Keep published evidence sanitized. SPIRE's admitted-node record contains the
consumed grant; do not publish raw node state, SSH trust files, grants, keys,
or private access details. The host rollout retains the concrete deployment
and observation record; this summary records only public identities, closures,
and acceptance outcomes.

| Check | Status |
| --- | --- |
| Owner-selected trust domain and persistent pilot scope | Authorized |
| Running source and pre-change system closure identified | Recorded above |
| Candidate preserves kernel, initrd/modules, fstab/crypttab and existing service/pilot units | Exact comparisons passed before both activations |
| Guarded test activation and existing-service health | Passed on Ace |
| Intended unit receives exact identity | Passed on Ace; timer configured for subsequent health fetches |
| Rotation within one long-running process | Passed in VM; not separately observed on Ace's persistent authority |
| Correct user under the wrong unit denied that identity | Passed on Ace and in VM |
| Probe cannot read authority keys or access its admin socket | Passed on Ace |
| Server/agent restart with consumed grant absent | Passed on Ace; authority, node and registration preserved |
| Existing public enrollment, Hydra/PostgreSQL and failed-unit checks | Passed on Ace; status unchanged and services healthy |
| Established-state loss fails closed in software rehearsal | Passed in the ten-group VM suite |
| Guarded persistent switch, fresh SSH and post-switch probe | Passed on Ace; generation 10 active and persistent |
| Prior generation retained and Mako configuration unchanged | Verified |
| Controlled online warm reboot on Ace | Passed with automatic startup; generation 10, bundle, enrollment and exact probe identity preserved |
| Cold boot, offline restart and recovery on Ace | Not exercised by this rollout |
| Physical boot, rollback and time-continuity qualification | Open |

## Subsequent controlled warm reboot

Ace was rebooted at `2026-09-29T06:42:40Z` after confirming idle Hydra builds,
retained recovery generation 9, and matching default boot kernel/initrd. The
first observation at 35 seconds correctly failed readiness: SPIRE was waiting
for time synchronization and the probe output still belonged to the old boot.
At `2026-09-29T06:44:11Z` (77 seconds uptime), all eleven comparison checks
passed automatically, without manually starting the probe, SPIRE or clock.

The [separate warm-reboot receipt](https://github.com/PseudoDesign/nix-pseudo-design/blob/codex/spiffe-persistent-pilot/docs/observations/2026-09-29-ace-identity-warm-reboot.json)
records changed boot/probe invocation IDs, the expected booted/current/persistent
generation, unchanged trust-bundle and public enrollment digests, a fresh valid
identity and healthy existing services. The [read-only observation tool](https://github.com/PseudoDesign/kaiba-provisioning/blob/80edf573aadbca788df2c547dfaf3f96ad37e6a8/scripts/offline-qualification/observe_reboot.py)
retains bounded evidence privately and rejects stale preboot output. Its
self-reported observations do not attest the boot chain or qualify cold boot,
clock continuity, offline recovery or hardware rollback protection.

The owner selected LAN DNS qualification as the next integration step. The
[LAN/DNS rollout record](pilot-dns-rollout.md) keeps public delegation separate.

Local identity success does not establish fleet admission, DNS-update
authorization, public reachability, or autonomous production readiness. The
[SPIFFE/SPIRE roadmap](spiffe-spire-plan.md) and
[offline qualification matrix](offline-qualification.md) retain those gates.
