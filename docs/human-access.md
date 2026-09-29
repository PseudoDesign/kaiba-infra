# Human passkey access

Kaiba human login uses Keycloak on Mako, an OIDC-authenticated Smallstep SSH
issuer on Mako, and ordinary OpenSSH on Ace and Mako. A passkey authenticates a
person; a short-lived SSH certificate authorizes that person to use an explicitly
mapped Unix account. The initial account is `adam`, which already has sudo
administration rights. This is human administrator access, not scoped agent
delegation. Pilot device identities, Hydra credentials, and owner recovery SSH
keys are separate.

The public issuer is `https://auth.pseudo.design/realms/kaiba`, and the certificate
endpoint is `https://ssh-ca.pseudo.design`. The immutable OIDC subject determines
`kaiba:person:<sub>`; email addresses and requested Unix usernames never determine
authority. Host configuration must explicitly map that principal to `adam`.

## Components and policy

| Component | Repository/module | State |
| --- | --- | --- |
| Keycloak, local PostgreSQL, realm policy | `kaiba-infra`, `human-identity` | PostgreSQL `keycloak`; `/var/lib/kaiba-human-identity` |
| SSH user certificate issuer | `kaiba-infra`, `ssh-user-ca` | `/var/lib/kaiba-ssh-ca`; `/var/lib/private/kaiba-ssh-ca-db` |
| Exact host principal mappings | `kaiba-infra`, `ssh-human-access` | Public CA and principal files in `/etc/ssh` |
| Linux/Nix workstation client | `kaiba-infra`, `packages.<system>.kaiba-login` | Local SSH agent; public certificate and session metadata under `$XDG_STATE_HOME/kaiba` |
| Encrypted daily backup | `human-access-backup`, `human-access-backup-receiver` | Ciphertext on Mako and Ace |
| Host composition and pinned infrastructure revision | `nix-pseudo-design` | `hosts/mako`, `hosts/ace` |

The SSH OIDC client is public and uses authorization code flow with S256 PKCE
and the exact callback `http://127.0.0.1:8400`. Password grants, implicit flow,
service accounts, device authorization, and optional offline scopes are disabled.
Human browser authentication requires a discoverable, user-verified passkey on
every authentication. Public registration and password reset are disabled.

Only the administrator-managed `kaiba-ssh-admin` group may receive certificates.
The issuer accepts user certificates for the exact subject principal, with an
eight-hour maximum lifetime, and rejects host certificates and X.509 issuance.
The certificate key ID records `issuer#sub`. Its only extension permits PTY
allocation; forwarding and user rc are not granted. Shell commands and sudo still
follow the mapped Unix account's policy. The issuer's private signing keys are
runtime credentials, never Nix values. Its audit wrapper removes upstream bearer
token fields before journald receives them.

The SSH module denies certificate login to root, service accounts, and accounts
without an explicit principal file. Existing owner `authorized_keys` remain
available for recovery. Removing a group blocks new issuance; an already issued
certificate remains usable until expiry or host revocation. Neither expiry nor
`kaiba logout` terminates existing SSH connections, multiplexed sessions, or sudo
processes.

## Deploy and qualify

Initial read-only inspection found Mako has 2 GB RAM, four ARM64 cores, no swap,
about 1.3 GB available RAM, and about 195 GB free root space. These figures are a
baseline, not a completed runtime capacity test. Keycloak uses a 384 MB Java heap,
768 MB cgroup high watermark, and 1 GB hard limit; its database pool is five
connections. PostgreSQL defaults to 64 MB shared buffers and 30 connections. The
SSH issuer is limited to 256 MB. Measure steady-state and peak usage during
enrollment, issuance, restart, and backup before accepting this shared host.

Keep a working owner SSH session open. Preserve the current system generation,
public pilot identity status, UID/GID assignments, and protected mount metadata.
Do not read or copy private pilot state or OTP/LUKS keys. Compare the proposed
kernel, initrd, mounts, and system closure before activation. Follow the host
repository's safe `/boot` and `/boot/firmware` automount procedure during any
activation that touches boot state. On Ace, generations older than the root-backed
home migration must not be selected unchanged.

Create the master bootstrap password on Mako without displaying it:

```sh
sudo bash -euo pipefail -c '
  umask 077
  install -d -m 0700 /var/lib/kaiba-human-identity
  test ! -e /var/lib/kaiba-human-identity/bootstrap-admin-password
  test ! -L /var/lib/kaiba-human-identity/bootstrap-admin-password
  set -C
  head -c 48 /dev/urandom | base64 > /var/lib/kaiba-human-identity/bootstrap-admin-password
'
```

From the reviewed infrastructure checkout, use an ARM64-capable Nix builder to
build the initializer, copy its closure to Mako, and run that exact executable:

```sh
kaiba_init=$(nix build .#packages.aarch64-linux.ssh-ca-init --no-link --print-out-paths)
nix copy --to ssh-ng://adam@mako "$kaiba_init"
ssh adam@mako sudo "$kaiba_init/bin/kaiba-ssh-ca-init"
```

This explicit initialization refuses *every* existing state directory, including
an interrupted initialization; there is no overwrite flag. Preserve and investigate
partial state instead of deleting it and silently changing trust. The command prints
only public trust. Initialization must precede activation of the CA nginx vhost,
whose upstream TLS verification requires the generated root certificate.
Before activation, ensure both public names resolve to Mako's HTTPS entry point
and ACME validation can reach its nginx service.

Set up Mako's dedicated backup SSH key at
`/var/lib/kaiba-human-backup/id_ed25519`, its pinned Ace host key in `known_hosts`
alongside it, and the public backup key in Ace's root-owned
`/var/lib/kaiba-human-backup-receiver/authorized_keys`. The receiver forces
write-only `rrsync`, has no terminal or forwarding, and is never a human CA
principal. Use only reviewed owner-controlled public age/SSH recipients for
encryption. The operator must retain the corresponding private recovery key
outside both hosts.

Test-deploy before switching persistently. Verify Keycloak, PostgreSQL, the
policy reconciler, SSH issuer, nginx, and existing services; check available
memory, `MemoryPeak`, `memory.events`, restart counts, and absence of OOM kills.
Verify public HTTPS discovery, the passkey browser flow, and certificate issuance.
Only `/realms/kaiba/` and `/resources/` are forwarded by the public identity
vhost; master-realm administration remains available only through loopback.
Check blocked paths through nginx, not merely against the backend.

## Enroll the initial owner

Run the management helper through an existing owner SSH session on Mako:

```sh
sudo kaiba-human-identity \
  --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password \
  enroll-start --owner adam
```

This creates one initial owner without SSH-group membership. A separate enrollment
client accepts its random temporary password for 30 minutes, restricted to the
pending-owner role. The expiry timer checks every minute. Read the enrollment URL
and password *on your own terminal* using sudo from
`/var/lib/kaiba-human-identity/owner-enrollment-url` and
`owner-enrollment-password`; do not paste them into chat, Git, or logs.

Open the URL in your own browser, enter that password, and register the first
passkey. Then visit the Kaiba account console at
`https://auth.pseudo.design/realms/kaiba/account/` using that passkey and add a
second. Prefer a separate recovery device or passkey account. The server verifies
two distinct registered credential IDs, but cannot prove independent physical
devices or independent sync accounts without attestation.

Finalize from the owner SSH session:

```sh
sudo kaiba-human-identity \
  --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password \
  enroll-finalize
```

Finalization requires two passkeys, disables the enrollment client, deletes all
owner password credentials and the pending role, then grants the SSH group. It is
repeatable after an interrupted finalization. It never resets an existing owner's
passkeys. The master bootstrap credential is separate, root-only operational
state; it is not an alternative password login to the human realm.

Use `enroll-status` with the same helper/password-file arguments to inspect only
the public subject, phase, expiry, and passkey count. If the initial ceremony
expires, `enroll-resume` rotates its temporary password and opens another bounded
window for the recorded, unfinished owner. It preserves registered passkeys and
refuses an already finalized or privileged owner.

Record the owner's public subject and generated SSH CA public key in the host
composition. Enable `kaibaHumanSSH` on Ace and Mako with exactly that principal
mapped to `adam`. Review the public CA fingerprint through an existing trusted SSH
session before distributing workstation configuration. Do not infer the subject
from the username or email.

## Workstation login (Linux with Nix)

Install a reviewed, immutable infrastructure revision:

```sh
nix profile install 'github:PseudoDesign/kaiba-infra/<reviewed-revision>#kaiba-login'
```

Create `~/.config/kaiba/login.json` owned by your workstation user, without group
or world write access. Populate all six fields with the reviewed public values:

```json
{
  "caURL": "https://ssh-ca.pseudo.design",
  "rootFingerprint": "<64-character transport-root SHA256 hex>",
  "sshUserCAFingerprint": "SHA256:<OpenSSH user CA fingerprint>",
  "issuer": "https://auth.pseudo.design/realms/kaiba",
  "clientID": "kaiba-ssh",
  "principal": "kaiba:person:<immutable owner subject>"
}
```

The transport root fingerprint comes from Mako's `public-trust.json`. Obtain the
separate SSH signing-key fingerprint with `ssh-keygen -lf` on `ssh_user_ca.pub`.
The client verifies both; the public ACME certificate on nginx is a third, distinct
TLS concern. Never replace fingerprint verification with insecure TLS.

Run the client on your own workstation, with your local SSH agent available:

```sh
kaiba login
kaiba status
```

`kaiba login` opens the browser authentication flow, creates an ephemeral SSH key
in memory, loads it into the local agent, and validates the returned certificate's
signing CA, principal, identity, and lifetime. No private SSH key is written to
disk. A public certificate path is returned in `certificateFile`; the default is
`~/.local/state/kaiba/certificate.pub`. The client refuses a remote SSH session.
Do not run human login in an automation workspace or forward this SSH agent there.

Use a dedicated SSH profile to ensure routine operations actually use the
certificate, even when owner recovery keys are also present:

```sshconfig
Host ace-human mako-human
    User adam
    IdentityFile ~/.local/state/kaiba/certificate.pub
    IdentitiesOnly yes
    ForwardAgent no
    ControlMaster no
    ControlPath none

Host ace-human
    HostName ace

Host mako-human
    HostName mako
```

The `IdentityFile` is a public certificate that selects its agent-held private
key. Adapt its path if you use `XDG_STATE_HOME`. Keep host-key verification
enabled. Verify `ssh ace-human` and `ssh mako-human` in new sessions and check the
server audit entry for the certificate identity. To remove only the identity
installed by this client:

```sh
kaiba logout
```

Logout preserves unrelated SSH agent keys and existing SSH/browser sessions.
Fresh login requires another passkey authentication. An eight-hour certificate
is a ceiling, not an indefinitely renewable credential. Run `kaiba logout` before
`kaiba login` when replacing an existing or expired login.

If the recorded agent socket has disappeared or been replaced, login and logout
clear only Kaiba's public session record. They do not remove keys from another
agent. If the original socket still exists, use that agent to log out first.

## Revocation and recovery

For immediate subject-wide denial, remove its host principal mapping and deploy
that change on both hosts. Remove the Keycloak SSH group to stop new certificates.
Terminate existing sessions separately if the incident requires it.

For individual certificate revocation, OpenSSH can use a runtime KRL via
`kaibaHumanSSH.revokedKeysFile`. Provision a valid root-owned KRL before enabling
the option and update it atomically. Never replace it with an empty file. The
module validates ownership, path, and parseability before sshd starts. OpenSSH
rejects **all public-key authentication, including owner recovery keys**, if a
configured KRL is missing or unreadable; retain an out-of-band recovery route.
The default leaves this global option unset. CA rotation requires reviewed trust
replacement on both hosts and workstations. A KRL enabled later needs its own
backup and restore procedure; the identity backup below does not include it.

Daily backups stop the SSH issuer briefly to snapshot its issuance database,
dump PostgreSQL, archive identity and CA state, and restart the issuer even after
a snapshot error. The bundle includes checksums and the system generation. It is
encrypted with age before transfer; plaintext staging remains root-only on Mako
and is removed on exit. Ace receives ciphertext only. Seven recent snapshots are
retained on each host. Build outputs and pilot state are excluded.

The transport root key initially remains in `offline-root/`, encrypted under a
separate password and excluded from the running service's credentials. After an
owner has verified encrypted recovery, move this root material to genuinely
offline storage. This does not make the online SSH signing key an offline key.
Do not remove the only recoverable root copy before verifying the owner's backup.

Test a restore on an isolated system: decrypt with an owner-controlled recovery
key, verify `SHA256SUMS`, restore the PostgreSQL custom dump into an empty database,
restore identity and CA state with private ownership/modes, then compare the
original public CA fingerprints and subject IDs. Restore the CA database under
`/var/lib/private/kaiba-ssh-ca-db` with systemd's expected state-directory layout.
Keep public DNS and host trust pointed at the original deployment during the
drill. A production recovery test requires the owner's private backup key; a
synthetic test key proves the mechanism, not possession of that key.

If all passkeys are lost, recover through retained owner SSH/console access and
a separately reviewed local administrator procedure that preserves the existing
subject. `enroll-resume` cannot recover a finalized owner. Never reuse pilot
credentials, turn on public signup, add a generic password fallback, or create
a new CA as a shortcut. Restore preserves user subjects, passkeys, and issuer keys; bootloader
rollback alone does not roll back PostgreSQL or Keycloak schema migrations.

## Verification

```sh
python3 -m unittest discover -s tests -v
nix build .#checks.x86_64-linux.selector
nix build .#human-identity-test .#ssh-user-ca-test \
  .#ssh-human-access-test .#human-access-backup-test
```

The identity test uses real Keycloak and Chromium with virtual WebAuthn
authenticators. The CA test exercises actual certificate issuance and rejection.
The SSH test uses real sshd and a client agent. The backup test encrypts, transfers,
decrypts, and restores synthetic database/state fixtures. These tests complement
native Mako resource checks and the owner's real passkey and recovery ceremonies.
