{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaHydra.ciRuns;
in {
  options.services.kaibaHydra.ciRuns = {
    enable = lib.mkEnableOption "immutable Hydra jobsets for GitHub PR and manual CI runs";
    workflowId = lib.mkOption {
      type = lib.types.ints.positive;
      description = "GitHub ID of kaiba-provisioning's reviewed CI workflow.";
    };
    githubTokenFile = lib.mkOption {
      type = lib.types.str;
      default = config.services.kaibaHydra.github.tokenFile;
      description = "Runtime GitHub credential with Actions and Contents read permission.";
    };
    username = lib.mkOption {
      type = lib.types.str;
      default = "adam";
      description = "Hydra account permitted to create provisioning jobsets.";
    };
    passwordFile = lib.mkOption {
      type = lib.types.str;
      description = "Runtime Hydra password, loaded only into the discovery service.";
    };
  };

  config = lib.mkIf (config.services.kaibaHydra.enable && cfg.enable) {
    systemd.services.kaiba-hydra-ci-runs = {
      description = "Discover admitted GitHub PR/manual CI runs for Hydra";
      after = [ "network-online.target" "hydra-server.service" ];
      wants = [ "network-online.target" ];
      requires = [ "hydra-server.service" ];
      serviceConfig = {
        Type = "oneshot";
        DynamicUser = true;
        LoadCredential = [
          "github-token:${cfg.githubTokenFile}"
          "hydra-password:${cfg.passwordFile}"
        ];
        UMask = "0077";
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        NoNewPrivileges = true;
        RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_INET6" ];
        TimeoutStartSec = "5min";
        ExecStart = "${pkgs.python3}/bin/python3 ${../ci}/hydra_ci_runs.py "
          + "--workflow-id ${toString cfg.workflowId} --username ${lib.escapeShellArg cfg.username}";
      };
    };
    systemd.timers.kaiba-hydra-ci-runs = {
      wantedBy = [ "timers.target" ];
      timerConfig = { OnBootSec = "1min"; OnUnitInactiveSec = "1min"; };
    };
  };
}
