{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.kaibaHydra.forgejo;
in
{
  options.services.kaibaHydra.forgejo = {
    enable = lib.mkEnableOption "Forgejo admitted-run discovery and Hydra status reporting";
    tokenFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/kaiba-hydra-secrets/forgejo-token";
    };
    passwordFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/kaiba-hydra-bootstrap/adam-password";
    };
  };
  config = lib.mkIf (config.services.kaibaHydra.enable && cfg.enable) {
    nix.settings.allowed-uris = [
      "git+https://git.pseudo.design/"
      "https://git.pseudo.design/"
    ];
    systemd.services.kaiba-hydra-forgejo = {
      after = [
        "network-online.target"
        "hydra-server.service"
      ];
      wants = [ "network-online.target" ];
      requires = [ "hydra-server.service" ];
      serviceConfig = {
        Type = "oneshot";
        DynamicUser = true;
        StateDirectory = "kaiba-hydra-forgejo";
        StateDirectoryMode = "0700";
        LoadCredential = [
          "forge-token:${cfg.tokenFile}"
          "hydra-password:${cfg.passwordFile}"
        ];
        UMask = "0077";
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        NoNewPrivileges = true;
        RestrictAddressFamilies = [
          "AF_UNIX"
          "AF_INET"
          "AF_INET6"
        ];
        TimeoutStartSec = "5min";
        ExecStart = "${pkgs.python3}/bin/python3 ${../ci}/hydra_forgejo_runs.py";
      };
    };
    systemd.timers.kaiba-hydra-forgejo = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "1min";
        OnUnitInactiveSec = "1min";
      };
    };
  };
}
