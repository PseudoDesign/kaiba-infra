{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.kaibaForgejo;
  b = cfg.backup;
  recipients = pkgs.writeText "forgejo-backup-recipients" (
    lib.concatStringsSep "\n" b.recipients + "\n"
  );
in
{
  options.services.kaibaForgejo.backup = {
    enable = lib.mkEnableOption "consistent encrypted forge backups";
    recipients = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
    };
    receiverHost = lib.mkOption {
      type = lib.types.str;
      default = "192.168.8.214";
    };
    keyFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/kaiba-forgejo-backup/id_ed25519";
    };
    knownHostsFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/kaiba-forgejo-backup/known_hosts";
    };
  };
  config = lib.mkIf (cfg.enable && b.enable) {
    assertions = [
      {
        assertion = b.recipients != [ ];
        message = "Forge backups require owner recovery recipients.";
      }
    ];
    systemd.tmpfiles.rules = [
      "d /var/lib/kaiba-forgejo-backup 0700 root root -"
      "d /var/lib/kaiba-forgejo-admin 0700 root root -"
      "d /var/backups/kaiba-forgejo 0700 root root -"
      "d /var/backups/kaiba-forgejo/daily 0700 root root -"
      "d /var/backups/kaiba-forgejo/weekly 0700 root root -"
    ];
    systemd.services.kaiba-forgejo-backup = {
      after = [
        "postgresql.target"
        "network-online.target"
      ];
      requires = [ "postgresql.target" ];
      wants = [ "network-online.target" ];
      path = [
        pkgs.age
        pkgs.coreutils
        pkgs.findutils
        pkgs.gnutar
        pkgs.gzip
        pkgs.rsync
        pkgs.openssh
        pkgs.util-linux
        pkgs.systemd
      ];
      serviceConfig = {
        Type = "oneshot";
        UMask = "0077";
        LoadCredential = [
          "ssh-key:${b.keyFile}"
          "known-hosts:${b.knownHostsFile}"
        ];
      };
      script = ''
        set -euo pipefail
        exec 9>/var/lib/kaiba-forgejo-backup/backup.lock
        flock --exclusive 9
        staging=$(mktemp -d /var/backups/kaiba-forgejo/.staging-XXXXXXXX)
        was_active=0
        cleanup() {
          result=$?
          trap - EXIT
          set +e
          if [ "$was_active" = 1 ]; then systemctl start forgejo.service || result=1; fi
          rm -rf -- "$staging"
          exit "$result"
        }
        trap cleanup EXIT
        trap 'exit 143' TERM
        trap 'exit 130' INT
        if systemctl is-active --quiet forgejo.service; then
          was_active=1
          systemctl stop forgejo.service
        fi
        runuser -u postgres -- ${config.services.postgresql.package}/bin/pg_dump -Fc forgejo > "$staging/forgejo.dump"
        ${config.services.postgresql.package}/bin/pg_restore --list "$staging/forgejo.dump" >/dev/null
        tar -czf "$staging/state.tar.gz" -C /var/lib forgejo kaiba-forgejo-backup kaiba-forgejo-admin kaiba-docs
        readlink -f /run/current-system > "$staging/system-generation"
        date -u +%FT%TZ > "$staging/created-at"
        (cd "$staging" && sha256sum forgejo.dump state.tar.gz system-generation created-at > SHA256SUMS)
        if [ "$was_active" = 1 ]; then
          systemctl start forgejo.service
          was_active=0
        fi
        stamp=$(date -u +%Y%m%dT%H%M%SZ)
        tar -C "$staging" -cf - forgejo.dump state.tar.gz system-generation created-at SHA256SUMS \
          | age -R ${recipients} -o "$staging/forgejo.tar.age"
        mv "$staging/forgejo.tar.age" "/var/backups/kaiba-forgejo/daily/$stamp.tar.age"
        if [ "$(date -u +%u)" = 7 ]; then
          cp --reflink=auto "/var/backups/kaiba-forgejo/daily/$stamp.tar.age" "/var/backups/kaiba-forgejo/weekly/$stamp.tar.age"
        fi
        export RSYNC_RSH="ssh -i $CREDENTIALS_DIRECTORY/ssh-key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$CREDENTIALS_DIRECTORY/known-hosts"
        # Transfer successfully before pruning either local or remote recovery copies.
        rsync -a --exclude='.staging-*' /var/backups/kaiba-forgejo/ ${lib.escapeShellArg "forgejo-backup@${b.receiverHost}:."}
        find /var/backups/kaiba-forgejo/daily -maxdepth 1 -type f -name '*.tar.age' | sort -r | tail -n +8 | xargs -r rm -f --
        find /var/backups/kaiba-forgejo/weekly -maxdepth 1 -type f -name '*.tar.age' | sort -r | tail -n +5 | xargs -r rm -f --
        rsync -a --delete --exclude='.staging-*' /var/backups/kaiba-forgejo/ ${lib.escapeShellArg "forgejo-backup@${b.receiverHost}:."}
      '';
    };
    systemd.timers.kaiba-forgejo-backup = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = "*-*-* 03:30:00 UTC";
        Persistent = true;
      };
    };
  };
}
