{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaHumanAccessBackup;
  recipients = pkgs.writeText "kaiba-human-access-backup-recipients" (lib.concatStringsSep "\n" cfg.recipients + "\n");
in {
  options.services.kaibaHumanAccessBackup = {
    enable = lib.mkEnableOption "encrypted human identity and SSH issuer backups";
    recipients = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      description = "Owner-controlled age or SSH public recipients; private recovery keys never belong on the issuer or backup receiver.";
    };
    receiverHost = lib.mkOption { type = lib.types.str; };
    keyFile = lib.mkOption { type = lib.types.str; default = "/var/lib/kaiba-human-backup/id_ed25519"; };
    knownHostsFile = lib.mkOption { type = lib.types.str; default = "/var/lib/kaiba-human-backup/known_hosts"; };
  };
  config = lib.mkIf cfg.enable {
    assertions = [{ assertion = cfg.recipients != []; message = "Human access backups require at least one owner-controlled encryption recipient."; }];
    systemd.tmpfiles.rules = [
      "d /var/lib/kaiba-human-backup 0700 root root -"
      "d /var/backups/kaiba-human-access 0700 root root -"
    ];
    systemd.services.kaiba-human-access-backup = {
      description = "Encrypt human identity and SSH CA backups before transfer to Ace";
      after = [ "postgresql.target" "network-online.target" ];
      requires = [ "postgresql.target" ];
      wants = [ "network-online.target" ];
      unitConfig.ConditionPathExists = "/var/lib/kaiba-ssh-ca/initialized";
      path = [ pkgs.age pkgs.coreutils pkgs.findutils pkgs.gnutar pkgs.gzip pkgs.rsync pkgs.openssh pkgs.util-linux pkgs.systemd ];
      serviceConfig = {
        Type = "oneshot";
        UMask = "0077";
        LoadCredential = [ "ssh-key:${cfg.keyFile}" "known-hosts:${cfg.knownHostsFile}" ];
      };
      script = ''
        set -euo pipefail
        staging=$(mktemp -d /var/backups/kaiba-human-access/.staging-XXXXXXXX)
        was_active=0
        cleanup() {
          result=$?
          trap - EXIT
          set +e
          if [ "$was_active" = 1 ]; then systemctl start kaiba-ssh-ca.service || result=1; fi
          rm -rf -- "$staging"
          exit "$result"
        }
        trap cleanup EXIT
        # Enrollment updates PostgreSQL and its local owner state together.
        # Share its lock so the dump and archive describe one completed change;
        # wait before stopping issuance, and release before encryption/transfer.
        exec 9>> /var/lib/kaiba-human-identity/owner-enrollment.lock
        flock --exclusive 9
        if systemctl is-active --quiet kaiba-ssh-ca.service; then
          was_active=1
          systemctl stop kaiba-ssh-ca.service
        fi
        # Resolve only systemd's expected top-level StateDirectory indirection.
        # Do not follow arbitrary symlinks inside the archived directories.
        test "$(readlink -f /var/lib/kaiba-ssh-ca-db)" = /var/lib/private/kaiba-ssh-ca-db
        runuser -u postgres -- ${config.services.postgresql.package}/bin/pg_dump -Fc keycloak > "$staging/keycloak.dump"
        ${config.services.postgresql.package}/bin/pg_restore --list "$staging/keycloak.dump" >/dev/null
        tar -czf "$staging/state.tar.gz" -C /var/lib kaiba-human-identity kaiba-ssh-ca \
          -C /var/lib/private kaiba-ssh-ca-db
        readlink -f /run/current-system > "$staging/system-generation"
        date -u +%FT%TZ > "$staging/created-at"
        (cd "$staging" && sha256sum keycloak.dump state.tar.gz system-generation created-at > SHA256SUMS)
        flock --unlock 9
        exec 9>&-
        if [ "$was_active" = 1 ]; then
          systemctl start kaiba-ssh-ca.service
          was_active=0
        fi
        # Only the encrypted bundle is eligible for synchronization.
        stamp=$(date -u +%Y%m%dT%H%M%SZ)
        tar -C "$staging" -cf - keycloak.dump state.tar.gz system-generation created-at SHA256SUMS \
          | age -R ${recipients} -o "$staging/identity.tar.age"
        mv "$staging/identity.tar.age" "/var/backups/kaiba-human-access/$stamp.tar.age"
        find /var/backups/kaiba-human-access -maxdepth 1 -type f -name '*.tar.age' \
          | sort -r | tail -n +8 | xargs -r rm -f --
        export RSYNC_RSH="ssh -i $CREDENTIALS_DIRECTORY/ssh-key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$CREDENTIALS_DIRECTORY/known-hosts"
        rsync -a --delete --include='*.tar.age' --exclude='*' /var/backups/kaiba-human-access/ \
          ${lib.escapeShellArg "human-access-backup@${cfg.receiverHost}:."}
      '';
    };
    systemd.timers.kaiba-human-access-backup = {
      wantedBy = [ "timers.target" ];
      timerConfig = { OnCalendar = "*-*-* 03:15:00 UTC"; Persistent = true; };
    };
  };
}
