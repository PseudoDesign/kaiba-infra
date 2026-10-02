{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.kaibaForgejo;
  sso = cfg.sso;
in
{
  options.services.kaibaForgejo.sso = {
    enable = lib.mkEnableOption "owner-admitted Keycloak login";
    ownerSubject = lib.mkOption {
      type = lib.types.str;
      default = "";
    };
    adminPasswordFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/kaiba-human-identity/bootstrap-admin-password";
    };
    issuer = lib.mkOption {
      type = lib.types.str;
      default = "https://auth.pseudo.design/realms/kaiba";
    };
    localAdminURL = lib.mkOption {
      type = lib.types.str;
      default = "http://127.0.0.1:8080";
    };
  };
  config = lib.mkIf (cfg.enable && sso.enable) {
    assertions = [
      {
        assertion = sso.ownerSubject != "";
        message = "Forge SSO requires an explicit admitted owner subject.";
      }
    ];
    systemd.tmpfiles.rules = [ "d /var/lib/kaiba-forgejo-admin 0700 root root -" ];
    systemd.services.kaiba-forgejo-sso = {
      environment.PYTHONPATH = "${../ci}";
      wantedBy = [ "multi-user.target" ];
      after = [
        "forgejo.service"
        "kaiba-human-identity-configure.service"
      ];
      requires = [
        "forgejo.service"
        "kaiba-human-identity-configure.service"
      ];
      path = [
        pkgs.util-linux
        config.services.postgresql.package
      ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        LoadCredential = [ "admin-password:${sso.adminPasswordFile}" ];
        UMask = "0077";
        PrivateTmp = true;
        ProtectHome = true;
        NoNewPrivileges = true;
        TimeoutStartSec = "5min";
      };
      script = ''
        ${pkgs.python3}/bin/python3 ${../identity}/forgejo_sso.py \
          --forgejo ${cfg.package}/bin/forgejo --domain ${lib.escapeShellArg cfg.domain} \
          --owner-subject ${lib.escapeShellArg sso.ownerSubject} \
          --issuer ${lib.escapeShellArg sso.issuer} --admin-url ${lib.escapeShellArg sso.localAdminURL}
      '';
    };
  };
}
