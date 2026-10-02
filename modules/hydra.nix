{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaHydra;
  # Six kernel/compiler dependencies in the inventoried graph require this
  # feature; actual concurrency is still limited to one build and two cores.
  features = [ "nixos-test" "big-parallel" ] ++ lib.optional cfg.kvm "kvm";
in {
  imports = [ ./hydra-integrations.nix ./hydra-ci-runs.nix ./hydra-forgejo.nix ];
  options.services.kaibaHydra = {
    enable = lib.mkEnableOption "Kaiba's serial native Hydra builder";
    publicURL = lib.mkOption { type = lib.types.str; default = "https://hydra.pseudo.design"; };
    proxyAddress = lib.mkOption {
      type = lib.types.strMatching "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+";
      description = "Mako's reserved IPv4 address, the only remote Hydra client.";
    };
    kvm = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Advertise KVM only after the native sandbox smoke test passes.";
    };
    backup = {
      enable = lib.mkEnableOption "daily PostgreSQL and Hydra state snapshots to Mako";
      host = lib.mkOption { type = lib.types.str; default = "mako"; };
      keyFile = lib.mkOption { type = lib.types.str; default = "/var/lib/kaiba-hydra-backup/id_ed25519"; };
      knownHostsFile = lib.mkOption { type = lib.types.str; default = "/var/lib/kaiba-hydra-backup/known_hosts"; };
    };
  };

  config = lib.mkIf cfg.enable {
    services.hydra = {
      enable = true;
      hydraURL = cfg.publicURL;
      listenHost = "0.0.0.0";
      # Manage the local database declaratively. The pinned upstream module's
      # implicit bootstrap passes createdb's -O flag to runuser by mistake.
      dbi = "dbi:Pg:dbname=hydra;user=hydra;host=/run/postgresql;";
      notificationSender = "hydra@pseudo.design";
      useSubstitutes = true;
      buildMachinesFiles = [ "/etc/nix/machines" ];
      minimumDiskFree = 20;
      minimumDiskFreeEvaluator = 10;
      maxServers = 3;
      minSpareServers = 1;
      maxSpareServers = 2;
      extraConfig = ''
        max_concurrent_evals = 1
      '';
    };

    services.postgresql = {
      enable = true;
      ensureDatabases = [ "hydra" ];
      ensureUsers = [ { name = "hydra"; ensureDBOwnership = true; } ];
      identMap = ''
        hydra hydra hydra
        hydra hydra-queue-runner hydra
        hydra hydra-www hydra
        hydra root hydra
      '';
      authentication = ''
        local all hydra peer map=hydra
      '';
    };
    systemd.services.hydra-init = {
      requires = [ "postgresql.target" ];
      after = [ "postgresql.target" ];
      preStart = lib.mkBefore ''
        ${pkgs.util-linux}/bin/runuser -u postgres -- ${config.services.postgresql.package}/bin/psql \
          -v ON_ERROR_STOP=1 -d hydra -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm'
      '';
    };

    nix.buildMachines = [ {
      hostName = "localhost";
      protocol = null;
      systems = [ pkgs.stdenv.hostPlatform.system ];
      supportedFeatures = features;
      maxJobs = 1;
    } ];
    nix.settings = {
      experimental-features = [ "nix-command" "flakes" ];
      max-jobs = 1;
      cores = 2;
      sandbox = true;
      system-features = lib.mkForce features;
      # These are the only fetch origins used by the two jobset flakes.
      allowed-uris = [ "github:" "https://github.com/" "https://api.github.com/" "https://codeload.github.com/" ];
      # Read-only caches already used by the provisioning GitHub Actions lane.
      substituters = [
        "https://cache.nixos.org"
        "https://nixos-raspberrypi.cachix.org"
        "https://kaiba-provisioning.cachix.org"
      ];
      trusted-public-keys = [
        "nixos-raspberrypi.cachix.org-1:4iMO9LXa8BqhU+Rpg6LQKiGa2lsNh/j2oiYLNOQ5sPI="
        "kaiba-provisioning.cachix.org-1:31oP2cYGmH0RaAvvzw7mbMSP7yfQviyDLF8fBYHqgNE="
      ];
      require-sigs = true;
    };
    # Both the daemon and Hydra's direct local-store builds must avoid tmpfs.
    systemd.services.nix-daemon.environment.TMPDIR = "/var/tmp/nix-build";
    systemd.services.hydra-queue-runner.environment.TMPDIR = "/var/tmp/nix-build";
    systemd.services.hydra-evaluator.environment.TMPDIR = "/var/tmp/nix-build";
    # Hydra enables restrict-eval for legacy jobsets, but not for flake jobsets.
    # Propagate it to the flake metadata and nix-eval-jobs child processes too.
    systemd.services.hydra-evaluator.environment.NIX_CONFIG = "restrict-eval = true";
    systemd.tmpfiles.rules = [ "d /var/tmp/nix-build 1777 root root -" ]
      ++ lib.optionals cfg.backup.enable [
        "d /var/lib/kaiba-hydra-backup 0700 root root -"
        "d /var/backups/hydra 0700 root root -"
      ];

    networking.firewall.extraCommands = ''
      iptables -A nixos-fw -s ${cfg.proxyAddress}/32 -p tcp --dport 3000 -j nixos-fw-accept
    '';
    networking.firewall.extraStopCommands = ''
      iptables -D nixos-fw -s ${cfg.proxyAddress}/32 -p tcp --dport 3000 -j nixos-fw-accept 2>/dev/null || true
    '';

    nix.gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 14d";
    };

    systemd.services.kaiba-hydra-backup = lib.mkIf cfg.backup.enable {
      description = "Snapshot Hydra database and state and replicate seven daily copies to Mako";
      after = [ "postgresql.service" "network-online.target" ];
      wants = [ "network-online.target" ];
      requires = [ "postgresql.service" ];
      path = [ pkgs.coreutils pkgs.findutils pkgs.gnutar pkgs.gzip pkgs.rsync pkgs.openssh pkgs.util-linux ];
      serviceConfig = {
        Type = "oneshot";
        UMask = "0077";
        LoadCredential = [ "ssh-key:${cfg.backup.keyFile}" "known-hosts:${cfg.backup.knownHostsFile}" ];
      };
      script = ''
        set -euo pipefail
        staging=$(mktemp -d /var/backups/hydra/.snapshot-XXXXXXXX)
        trap 'rm -rf "$staging"' EXIT
        runuser -u postgres -- ${config.services.postgresql.package}/bin/pg_dump -Fc hydra > "$staging/hydra.dump"
        # Runtime/cache files are rebuilt. Logs may change while builds run;
        # pg_dump is consistent, and interrupted builds are retried on restore.
        tar --exclude=hydra/.cache --exclude=hydra/www/.cache --exclude=hydra/git \
          --exclude=hydra/run --warning=no-file-changed \
          -czf "$staging/state.tar.gz" -C /var/lib hydra || test "$?" -eq 1
        readlink -f /run/current-system > "$staging/system-generation"
        ${config.services.postgresql.package}/bin/pg_restore --list "$staging/hydra.dump" >/dev/null
        tar -tzf "$staging/state.tar.gz" >/dev/null
        (cd "$staging" && sha256sum hydra.dump state.tar.gz system-generation > SHA256SUMS)
        snapshot=/var/backups/hydra/$(date -u +%F)
        # Never replace a completed daily snapshot while the receiver reads it.
        if [ ! -e "$snapshot" ]; then mv "$staging" "$snapshot"; fi
        find /var/backups/hydra -mindepth 1 -maxdepth 1 -type d -name '????-??-??' \
          | sort -r | tail -n +8 | xargs -r rm -rf --
        export RSYNC_RSH="ssh -i $CREDENTIALS_DIRECTORY/ssh-key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$CREDENTIALS_DIRECTORY/known-hosts"
        rsync -a --delete --exclude='.snapshot-*' /var/backups/hydra/ \
          ${lib.escapeShellArg "hydra-backup@${cfg.backup.host}:."}
      '';
    };
    systemd.timers.kaiba-hydra-backup = lib.mkIf cfg.backup.enable {
      wantedBy = [ "timers.target" ];
      timerConfig = { OnCalendar = "*-*-* 03:00:00"; Persistent = true; };
    };
  };
}
