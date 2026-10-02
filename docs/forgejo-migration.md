# Forgejo migration and deployment

This rollout moves Kaiba development to Forgejo on Mako at
`https://git.pseudo.design`, with HTTPS Git, the existing Keycloak owner identity,
ARM64 builds on Ace and x86 builds on Malak. GitHub becomes a one-way code mirror
after acceptance. Future releases and documentation belong on Forgejo and
`https://docs.kaiba.pseudo.design`.

The implementation is staged. **GitHub remains authoritative.** No production
generation has been activated and no repository has been imported. Actions
defaults to disabled globally and imports explicitly disable it per repository.

## Repository scope

`ci/forgejo-projects.json` preserves the existing namespaces, names and visibility
for infrastructure, contracts, provisioning, Fleet, network and host configuration.
Fleet remains private. `kaiba-private` is excluded. The UI checkout has no Git
remote and contains uncommitted work; its namespace, visibility and source must
be resolved before adding it to the manifest. Do not invent a source repository
or commit that checkout's existing changes.

## Implemented components

- `modules/forgejo.nix` provides Forgejo LTS 15.0.9, PostgreSQL, loopback HTTP,
  nginx HTTPS, LFS, disabled Git SSH and closed public registration. A separate
  pinned package input leaves the qualified host kernel and OS pin intact.
- `modules/forgejo-sso.nix` creates a confidential Keycloak client with an exact
  callback and S256 PKCE. The authentication source admits the configured owner
  subject. Existing accounts must match their external identity binding before
  receiving administrator rights. Root-only recovery credentials remain local.
- `modules/forgejo-backup.nix` stops Forgejo while capturing PostgreSQL and state,
  restarts it on failure, encrypts to the existing owner recipients, and transfers
  ciphertext to the restricted receiver on Ace before pruning retention.
  It retains seven daily and four Sunday copies.
- `ci/forgejo_migrate.py` inventories and imports the explicit allowlist, refuses
  existing destinations or visibility drift, compares every Git head and tag,
  and reconciles portable issue, PR, label, milestone and release fields.
- `ci/forgejo_archive_github.py` streams available Actions artifacts and logs into
  age encryption and records plaintext and ciphertext hashes. Artifact digests
  are checked when GitHub provides them. Unavailable downloads remain explicit
  gaps in the receipts; existing encrypted copies are verified before reuse.
- `ci/hydra_forgejo_runs.py` prepares immutable jobsets for admitted provisioning
  waiters. It binds repository, workflow, run number, task ID and commit, checks
  approval and cancellation, validates the evaluation source and ten distinct
  planned jobs, and retains final deliveries for retry. The service is disabled
  until the corresponding Forgejo waiter is ported and qualified.
- `packages/forgejo-runner-vm.nix` defines a disposable KVM guest with its own
  Nix store image and only a read-only bootstrap share. Its daemon runs inside
  the guest. This image has been evaluated, **not boot-qualified**. A trusted host
  controller, host-enforced network restrictions and cleanup remain required.
- Infrastructure and contracts have initial `.forgejo/workflows/validate.yml`
  ports using pinned, fully qualified checkout actions. These workflows remain
  unqualified while Actions is disabled and builders are unavailable.

## Validation completed

The Python suite passes 73 tests, including import refusal, private credential
handling, identity admission and Hydra source substitution cases. The x86 VM
integration test passes under emulation: nginx and Forgejo startup, PostgreSQL,
512 MiB memory maximum, disabled registration and Actions, private Git push,
anonymous denial, database restore, repository restore and authenticated read
after restart. This is a database and repository recovery rehearsal; it does not
qualify the production encrypted backup or owner passkey login.

The Mako candidate builds on Mako with one compilation job and a 512 MiB build
limit. Its kernel, initrd, modules, boot arguments and fstab match the running
generation. The candidate is staged without activation. Recheck these comparisons
after updating the immutable infrastructure pin in the host flake.

Private inventory exports and encrypted recovery archives are kept outside Git
under `.worktrees/.private-observations/2026-10-02-forgejo-migration`. They contain
private project history and must not be attached to public reviews. The owner
must demonstrate decryption and restore; possession of ciphertext is insufficient.

## Remaining implementation and access gates

Ace rejects this workspace's SSH identity. Malak requires interactive sudo and
the workspace cannot use its KVM device. Restore the restricted operator paths
before receiver installation, native ARM checks or builder qualification. Public
DNS currently resolves the Git and docs names to Mako's public ingress; LAN
clients also need a working route or split DNS. Public TLS remains untested.

The remaining work is concrete:

1. Install the Ace receiver, provision its dedicated authorized key and pin the
   observed host key in Mako's runtime backup credentials. Qualify a full encrypted
   backup, off-host transfer, owner decryption and restore into an isolated instance.
2. Boot-qualify disposable runner images on Ace and Malak. Implement a host
   controller with repository-scoped, server-enforced ephemeral registrations,
   one job per guest, a host deadline, deletion of the guest disk and bootstrap
   directory, and host-enforced egress restrictions. Never expose host stores,
   homes, sockets, administrator tokens, signing material or enrolled pilot state.
   Jobs queue when Malak is offline. Build jobs never run on Mako.
3. Port the remaining workflows individually. Preserve schedules, dispatches,
   required checks and artifact contracts. Replace GitHub-specific Hydra waiter
   identity with Forgejo task identity and verify planned derivation paths.
   Release/device-secret/native-staging provenance currently depends on
   `github.workflow_sha`; do not replace it blindly with a pull-request SHA.
   Use Forgejo-compatible artifact actions rather than GitHub's current versions.
4. Implement trusted atomic docs publication and future Forgejo releases. The
   nginx docs root exists, but no publisher is installed. Replace GitHub Pages
   upload/deploy steps. Keep all historic GitHub releases and assets intact.
5. Configure namespace ownership and collaborators; import and reconcile history.
   Review authorship, comments, reviews, wiki refs, LFS objects and release asset
   hashes separately. Archive project boards and Actions history that cannot be
   imported. Metadata/ref comparisons alone never declare a complete migration.
6. Qualify owner passkey login, external denial, private visibility, TLS, resource
   pressure and recovery on the native deployment. Preserve the active identity
   pilot, its credentials, storage and expiry mechanism.
7. Implement the one-way mirror with dedicated GitHub repository write credentials
   outside runner guests. Mirror only heads and tags. Detect unexpected GitHub
   writes before updating refs; never turn either side into a bidirectional mirror.

## Import and reconciliation commands

Run the migration client from a trusted operator environment with `gh` authenticated,
Git, Python and a root-only Forgejo migration token file. Tokens must never appear
in URLs, output, committed files or workflow secrets used by pull requests.

```sh
python3 ci/forgejo_migrate.py inventory --repo PseudoDesign/kaiba-infra \
  --output /private/migration/kaiba-infra.json
python3 ci/forgejo_migrate.py import --repo PseudoDesign/kaiba-infra \
  --forge-token-file /private/migration/forge-token \
  --output /private/migration/kaiba-infra-import.json
python3 ci/forgejo_migrate.py verify --repo PseudoDesign/kaiba-infra \
  --forge-token-file /private/migration/forge-token \
  --output /private/migration/kaiba-infra-refs.json
python3 ci/forgejo_migrate.py verify-metadata --repo PseudoDesign/kaiba-infra \
  --snapshot /private/migration/kaiba-infra.json \
  --forge-token-file /private/migration/forge-token \
  --output /private/migration/kaiba-infra-metadata.json
```

Outputs are private and never overwritten. Refresh source inventories immediately
before the final import. A rehearsal destination must be explicitly reconciled or
removed by the operator before a fresh import; the importer never overwrites one.

## Deployment and cutover sequence

Build the pinned host closures and retain both running generations as GC roots.
Compare boot, unlock, disk, pilot and identity configuration. Use temporary `test`
activation with a rollback watchdog before persistent `switch`; no reboot,
reinstallation or disk formatting is required. Verify all existing services and
native gates before persistence.

Freeze GitHub project writes only for the final migration window, capture a fresh
inventory, import, reconcile all history, and record the accepted immutable refs
and hashes. Enable reviewed workflows only after isolated builders qualify.
Require successful native CI, docs/release publication, recovery and identity
checks before declaring Forgejo authoritative. Then change owned flake inputs,
developer remotes, webhooks, badges and publishing links, and enable the one-way
code mirror. Preserve third-party upstreams and Go module identities unless their
module migration is separately implemented. Disable GitHub's primary CI/Pages
only after replacements pass. Preserve historical GitHub assets.

Observe capacity, backups, status delivery and mirror lag for seven days. Record
the observation period separately; passing a rehearsal does not complete it.

## Rollback

Before cutover, GitHub stays writable and authoritative, so rollback restores the
retained host generation and leaves source repositories intact. Restore encrypted
state only into an isolated instance first. Do not blindly downgrade a Forgejo
database after a schema upgrade.

After cutover, freeze Forgejo writes and snapshot it before deciding to restore
GitHub primacy. Reconcile new commits and collaboration history explicitly; a
code mirror does not contain new issues or review history. Restore remotes,
webhooks, docs and CI together, then resume writes on exactly one primary.

Forgejo references: [Actions configuration](https://forgejo.org/docs/v15.0/admin/actions/),
[ephemeral runner registration](https://forgejo.org/docs/v15.0/admin/actions/registration/),
and [artifact compatibility](https://forgejo.org/docs/v15.0/user/actions/advanced-features/).
