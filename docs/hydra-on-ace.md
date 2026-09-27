# Hydra on Ace

Ace runs Hydra, PostgreSQL, and one native ARM64 build at a time. Mako serves
`https://hydra.pseudo.design` and receives daily backups. The host composition
lives in `nix-pseudo-design`; this repository exports the service modules and
the job inventory. Application checks stay in `kaiba-provisioning`.

## Reproducible checks

```sh
python3 -m unittest discover -s tests -v
nix flake check --no-build
nix build --no-link .#checks.x86_64-linux.selector
nix build --no-link -L .#hydra-integration-test
```

The integration test starts real Hydra/PostgreSQL services, reconciles the
jobsets twice, verifies the provisioning gate, restarts the service, sends a
snapshot through the restricted SSH receiver, and restores the database into
a separate test database. It can run under emulation without host KVM.

Provisioning imports `ci/hydra-jobs.nix` from a locked, non-flake input of this
repository. The helper resolves the ten inventory entries from the application's
own `checks`. It rejects absent jobs and incorrect architectures without
overriding their derivations or dependencies. Update the provisioning input lock
after inventory changes. Hydra polls each repository's `main` directly; the
application revision is not a locked dependency of the infrastructure flake.

## Qualify and deploy

Before activation, record both hosts' running generations and build the candidate
host closures. Compare them with `nix store diff-closures`. Check the kernel,
initrd, firmware, disk-unlock configuration and existing services explicitly;
Review and explicitly authorize any unrelated operating-system upgrade before
including it in this deployment.
Use `nixos-rebuild test` before `switch`. Retain the previous generation as a GC
root until acceptance is complete. No reinstall or disk-formatting step is part
of this rollout.

Ace's pilot account must remain UID 994/GID 988, with its existing state directory
mode 0700, state-file mode 0600, and `nosuid,nodev,noexec` protected mount. Record
metadata and public client status only. Do not read, copy, regenerate or change
ownership of the enrolled credential, and do not introduce swap.

The service defaults to `kvm = false`. Run the native smoke test **on Ace** from
a clean checkout of this repository:

```sh
nix build --no-link -L --rebuild --option extra-system-features kvm \
  .#packages.aarch64-linux.kvm-smoke-test
```

The test queries QEMU to prove that KVM is actually enabled inside the Nix build
environment. `--rebuild` avoids treating a cached result from another builder as
hardware qualification. Record the host generation with the result before
setting `services.kaibaHydra.kvm = true`. A failure keeps provisioning disabled.

Build scratch goes to `/var/tmp/nix-build` on disk. Scheduling starts at one
build, two compilation cores and one evaluation. The builder advertises
`big-parallel` because kernel/compiler dependencies require that feature;
it does not raise these concurrency limits. The queue stops below 20 GiB
free, and evaluation stops below 10 GiB. After reclaiming space, explicitly
restart `hydra-queue-runner` and `hydra-evaluator`. Weekly GC removes unrooted
paths older than 14 days; each jobset retains three successful builds.

## HTTPS and administrator

The deployment uses Ace `192.168.8.214` and Mako `192.168.8.247`; maintain these
as reserved LAN addresses. DNS for `hydra.pseudo.design` must reach Mako's public
ingress. Only Mako may reach Ace's TCP port 3000. Hydra receives the public URL
and forwarded HTTPS headers, so login cookies and links use the correct origin.

Create the Hydra administrator locally on Ace, using the installed Hydra wrapper:

```sh
sudo -iu hydra hydra-create-user adam --full-name 'Adam Schafer' \
  --email-address admin@pseudo.design --password-prompt --role admin
```

The password is entered interactively and is never supplied as a command-line
argument or committed. Public visitors can view builds; write operations require
Hydra authentication. No GitHub write token or cache signing key is required.

## Stage the jobsets

Preview the complete configuration, then apply it with the password prompt:

```sh
python3 ci/setup_hydra.py
python3 ci/setup_hydra.py --apply
```

This creates `kaiba-infra/main` enabled and `kaiba-provisioning/main` disabled,
with five-minute polling. Repeating a stage reconciles that desired state.
The command checks every write by reading the server configuration back.

After the latest infrastructure build succeeds and native qualification passes:

```sh
python3 ci/setup_hydra.py --stage provisioning --apply
```

The command refuses this stage unless the latest finished selector build is
successful. Hardware qualification is an operator prerequisite, not a claim
inferred from the infrastructure build. Run the default infrastructure stage
again to disable **future evaluations** of provisioning; already queued/running
builds must be cancelled separately in Hydra if needed.

GitHub Actions remains the PR gate. These jobsets build only `main`; this rollout
does not claim full provisioning workflow parity. Verify all ten ARM64 jobs,
their acceleration logs, a subsequent main evaluation, and reuse of unchanged
successful derivations before expanding the workload.

## Backups

Create a dedicated SSH key on Ace at
`/var/lib/kaiba-hydra-backup/id_ed25519` (directory 0700, private key 0600).
Install only its public key on Mako at
`/var/lib/hydra-backup/authorized_keys` (root-owned, mode 0644). Pin Mako's
verified SSH host public key in Ace's
`/var/lib/kaiba-hydra-backup/known_hosts`. No private key belongs in a Nix
expression, lockfile or store path.

Mako's dedicated `hydra-backup` account accepts only rsync writes within
`/var/backups/hydra/ace`; shell commands, forwarding and PTYs are disabled.
Ace's timer runs daily at 03:00 in the host timezone. It creates a consistent
PostgreSQL dump, Hydra state archive and checksums, retaining seven dated
snapshots locally and on Mako. Inputs/caches and runtime sockets are omitted.
Build logs can continue changing during the snapshot; in-flight builds must be
retried after recovery. The live Nix store is not a backup source.

```sh
sudo systemctl start kaiba-hydra-backup
sudo systemctl status kaiba-hydra-backup
sudo journalctl -u kaiba-hydra-backup
```

Confirm the checksums on Mako before relying on the backup. A failed transfer
fails the service and leaves the local snapshot available for retry. After a
receiver outage, a rerun uploads the already completed daily snapshot.

To recover, first deploy the same locked Hydra/PostgreSQL configuration to an
isolated host. Verify `SHA256SUMS`, stop the Hydra services and their timers,
restore the dump into a fresh `hydra` database owned by `hydra`, and restore the
state archive under `/var/lib` with its numeric owners. Use `pg_restore` from the
same PostgreSQL major version. Run `hydra-init`, disable jobset polling while
checking results, then restart services and retry interrupted builds. Recreate
missing outputs from Git and trusted caches. Restore testing must use a separate
database/host; do not drop the live database to rehearse recovery.

## Rollback

Disable provisioning evaluations first. Roll back Ace and Mako to the recorded
previous system generations if service acceptance fails. Preserve the new Hydra
database/state for diagnosis; never include pilot state in cleanup. A NixOS
generation rollback does not undo a database migration, so restore a matching
Hydra snapshot when rolling back across database schema versions.
