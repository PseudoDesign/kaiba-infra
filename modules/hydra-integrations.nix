{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaHydra;
  scripts = ../ci;
  patchedPlugin = import ./hydra-github-plugin.nix {
    inherit pkgs;
    hydra = config.services.hydra.package;
  };
in {
  options.services.kaibaHydra = {
    github = {
      enable = lib.mkEnableOption "per-job GitHub commit statuses for the two main jobsets";
      tokenFile = lib.mkOption {
        type = lib.types.str;
        default = "/var/lib/kaiba-hydra-secrets/github-token";
        description = "Runtime GitHub token with commit-status write access to the two Kaiba repositories.";
      };
    };
    cachePublish = {
      enable = lib.mkEnableOption "retryable publication of successful provisioning build closures";
      package = lib.mkPackageOption pkgs "cachix" { };
      tokenFile = lib.mkOption {
        type = lib.types.str;
        default = "/var/lib/kaiba-hydra-secrets/cachix-token";
        description = "Runtime Cachix write token, scoped to the provisioning cache.";
      };
    };
  };

  config = lib.mkIf cfg.enable (lib.mkMerge [
    (lib.mkIf cfg.github.enable {
      systemd.services.hydra-notify = {
        environment = {
          HYDRA_CONFIG = lib.mkForce "/run/kaiba-hydra-notify/hydra.conf";
          # -I takes precedence over the upstream wrapper's PERL5LIB. Only
          # the patched notifier module is overlaid; no Hydra rebuild is needed.
          PERL5OPT = "-I${patchedPlugin}";
        };
        preStart = ''
          ${pkgs.python3}/bin/python3 ${scripts}/hydra_notify_config.py \
            --output /run/kaiba-hydra-notify/hydra.conf
        '';
        serviceConfig = {
          LoadCredential = [ "github-token:${cfg.github.tokenFile}" ];
          RuntimeDirectory = "kaiba-hydra-notify";
          RuntimeDirectoryMode = "0700";
          UMask = "0077";
        };
      };
    })
    (lib.mkIf cfg.cachePublish.enable {
      services.hydra.extraConfig = ''
        <runcommand>
          job = kaiba-provisioning:main:*
          events = buildFinished
          command = ${pkgs.python3}/bin/python3 ${scripts}/hydra_publish.py enqueue
        </runcommand>
      '';
      systemd.tmpfiles.rules = [
        "d /var/lib/kaiba-hydra-publish 0700 hydra-queue-runner hydra -"
      ];
      systemd.services.kaiba-hydra-publish = {
        description = "Publish qualified Hydra build closures to Cachix";
        after = [ "network-online.target" "hydra-init.service" ];
        wants = [ "network-online.target" ];
        requires = [ "hydra-init.service" ];
        path = [ config.nix.package cfg.cachePublish.package ];
        environment.NIX_REMOTE = "daemon";
        serviceConfig = {
          Type = "oneshot";
          User = "hydra-queue-runner";
          Group = "hydra";
          LoadCredential = [ "cachix-token:${cfg.cachePublish.tokenFile}" ];
          UMask = "0077";
          TimeoutStartSec = "2h";
          ExecStart = "${pkgs.python3}/bin/python3 ${scripts}/hydra_publish.py publish";
        };
      };
      systemd.timers.kaiba-hydra-publish = {
        wantedBy = [ "timers.target" ];
        timerConfig = { OnBootSec = "2min"; OnUnitInactiveSec = "5min"; };
      };
    })
  ]);
}
