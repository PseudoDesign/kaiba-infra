{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaHumanIdentity;
  realmConfig = import ../identity/realm.nix {
    inherit (cfg) domain realm sshClientId sshRedirectUris enableDeviceAuthorization;
  };
  realmFile = pkgs.writeText "kaiba-realm.json" (builtins.toJSON realmConfig);
  runtimePath = lib.types.addCheck lib.types.str (value:
    lib.hasPrefix "/" value && !lib.hasPrefix "/nix/store/" value);
  helper = pkgs.writeShellApplication {
    name = "kaiba-human-identity";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${../identity/keycloak_admin.py} \
        --url http://127.0.0.1:${toString cfg.httpPort} \
        --config ${realmFile} \
        --username ${lib.escapeShellArg cfg.bootstrapAdminUsername} \
        --state-directory /var/lib/kaiba-human-identity "$@"
    '';
  };
in {
  options.services.kaibaHumanIdentity = {
    enable = lib.mkEnableOption "Kaiba passkey human identity";
    domain = lib.mkOption { type = lib.types.str; default = "auth.pseudo.design"; };
    realm = lib.mkOption { type = lib.types.str; default = "kaiba"; };
    sshClientId = lib.mkOption { type = lib.types.str; default = "kaiba-ssh"; };
    sshRedirectUris = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "http://127.0.0.1:8400" ];
      description = "Exact loopback callback URIs for the SSH OIDC client; wildcards are forbidden.";
    };
    proxy.enable = lib.mkOption { type = lib.types.bool; default = true; };
    enableDeviceAuthorization = lib.mkOption { type = lib.types.bool; default = false; };
    httpPort = lib.mkOption { type = lib.types.port; default = 8080; };
    bootstrapAdminUsername = lib.mkOption { type = lib.types.str; default = "kaiba-bootstrap-admin"; };
    bootstrapAdminPasswordFile = lib.mkOption {
      type = runtimePath;
      description = "Root-owned runtime password file for the separate master-realm bootstrap administrator.";
    };
    javaHeapMB = lib.mkOption { type = lib.types.ints.positive; default = 384; };
    memoryHighMB = lib.mkOption { type = lib.types.ints.positive; default = 768; };
    memoryMaxMB = lib.mkOption { type = lib.types.ints.positive; default = 1024; };
    databasePasswordFile = lib.mkOption {
      type = runtimePath;
      default = "/var/lib/kaiba-human-identity/database-password";
      description = "Runtime DB password. The default file is generated once; custom paths must already exist.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      { assertion = cfg.memoryMaxMB >= cfg.memoryHighMB && cfg.memoryHighMB > cfg.javaHeapMB;
        message = "Kaiba Keycloak requires memoryMaxMB >= memoryHighMB > javaHeapMB."; }
      { assertion = cfg.realm != "master" && builtins.match "[A-Za-z0-9_-]+" cfg.realm != null;
        message = "The Kaiba human realm must be a distinct, simple realm name."; }
      { assertion = cfg.sshRedirectUris != [ ] && builtins.all (uri:
          builtins.match "http://127[.]0[.]0[.]1:[0-9]+" uri != null) cfg.sshRedirectUris;
        message = "Kaiba SSH redirects must be exact numeric-loopback HTTP URIs without wildcards."; }
      { assertion = config.services.keycloak.initialAdminPassword == null;
        message = "Kaiba Keycloak bootstrap credentials must be runtime files, never initialAdminPassword."; }
    ];
    environment.systemPackages = [ helper ];
    services.nginx = lib.mkIf cfg.proxy.enable {
      enable = true;
      virtualHosts.${cfg.domain} = {
        enableACME = true;
        forceSSL = true;
        locations = let
          frontend = {
            proxyPass = "http://127.0.0.1:${toString cfg.httpPort}";
            recommendedProxySettings = false;
            extraConfig = ''
              # Reject matrix and double-encoded paths before JAX-RS routing.
              if ($uri ~ "[%;]") { return 404; }
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $remote_addr;
              proxy_set_header X-Forwarded-Proto https;
              proxy_set_header X-Forwarded-Host $host;
              client_max_body_size 128k;
              access_log off;
            '';
          };
        in {
          "= /realms/${cfg.realm}/kaiba-enrollment-complete".extraConfig = ''
            default_type text/html;
            access_log off;
            add_header Referrer-Policy no-referrer always;
            add_header Cache-Control no-store always;
            return 200 '<!doctype html><html lang="en"><meta charset="utf-8"><title>Continue Kaiba setup</title><h1>Continue Kaiba setup</h1><p>Open your account and add a second passkey on a different authenticator before finishing setup.</p><p><a href="/realms/${cfg.realm}/account/">Open your account</a></p></html>';
          '';
          "/realms/${cfg.realm}/" = frontend;
          "/resources/" = frontend;
          "/".return = "404";
        };
      };
    };
    networking.firewall.allowedTCPPorts = lib.mkIf cfg.proxy.enable [ 80 443 ];
    services.keycloak = {
      enable = true;
      database = { type = "postgresql"; passwordFile = cfg.databasePasswordFile; };
      settings = {
        hostname = "https://${cfg.domain}";
        hostname-strict = true;
        http-enabled = true;
        http-host = "127.0.0.1";
        http-port = cfg.httpPort;
        proxy-headers = "xforwarded";
        proxy-trusted-addresses = "127.0.0.1/32";
        bootstrap-admin-username = cfg.bootstrapAdminUsername;
        bootstrap-admin-password = { _secret = cfg.bootstrapAdminPasswordFile; };
        cache = "local";
        db-pool-initial-size = 1;
        db-pool-min-size = 1;
        db-pool-max-size = 5;
        http-pool-max-threads = 16;
        health-enabled = true;
        metrics-enabled = false;
        http-management-host = "127.0.0.1";
        http-management-port = 9000;
      };
    };
    services.postgresql.settings = {
      shared_buffers = lib.mkDefault "64MB";
      max_connections = lib.mkDefault 30;
    };
    systemd.services.kaiba-human-identity-secrets = {
      before = [ "keycloakPostgreSQLInit.service" "keycloak.service" ];
      requiredBy = [ "keycloakPostgreSQLInit.service" "keycloak.service" ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        StateDirectory = "kaiba-human-identity";
        StateDirectoryMode = "0700";
        UMask = "0077";
      };
      path = [ pkgs.openssl pkgs.coreutils ];
      script = lib.optionalString (cfg.databasePasswordFile == "/var/lib/kaiba-human-identity/database-password") ''
        if [ ! -e /var/lib/kaiba-human-identity/database-password ]; then
          openssl rand -hex 32 > /var/lib/kaiba-human-identity/database-password
        fi
      '' + ''
        test -s ${lib.escapeShellArg cfg.databasePasswordFile}
        test -s ${lib.escapeShellArg cfg.bootstrapAdminPasswordFile}
      '';
    };
    systemd.services.keycloak = {
      environment.JAVA_OPTS_KC_HEAP = "-Xms128m -Xmx${toString cfg.javaHeapMB}m";
      serviceConfig = {
        MemoryHigh = "${toString cfg.memoryHighMB}M";
        MemoryMax = "${toString cfg.memoryMaxMB}M";
        MemorySwapMax = 0;
        LimitCORE = 0;
        UMask = "0077";
        PrivateTmp = true;
        ProtectHome = true;
        NoNewPrivileges = true;
        TimeoutStartSec = "10min";
      };
    };
    systemd.timers.kaiba-human-identity-enrollment-expiry = {
      wantedBy = [ "timers.target" ];
      timerConfig = { OnBootSec = "1min"; OnUnitInactiveSec = "1min"; };
    };
    systemd.services.kaiba-human-identity-enrollment-expiry = {
      after = [ "keycloak.service" ];
      requires = [ "keycloak.service" ];
      serviceConfig = {
        Type = "oneshot";
        LoadCredential = [ "admin-password:${cfg.bootstrapAdminPasswordFile}" ];
        UMask = "0077";
        PrivateTmp = true;
        ProtectSystem = "strict";
        ReadWritePaths = [ "/var/lib/kaiba-human-identity" ];
        ProtectHome = true;
        NoNewPrivileges = true;
        ExecStart = "${helper}/bin/kaiba-human-identity expire-enrollment";
      };
    };
    systemd.services.kaiba-human-identity-configure = {
      description = "Reconcile and verify Kaiba's managed realm and SSH client policy";
      after = [ "keycloak.service" ];
      requires = [ "keycloak.service" ];
      partOf = [ "keycloak.service" ];
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        LoadCredential = [ "admin-password:${cfg.bootstrapAdminPasswordFile}" ];
        DynamicUser = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        NoNewPrivileges = true;
        RestrictAddressFamilies = [ "AF_INET" "AF_INET6" ];
        TimeoutStartSec = "8min";
        # Keycloak 26.7 signals systemd READY before asynchronous first-boot
        # realm/database initialization ends. Discovery can also appear before
        # admin routes are ready, so wait on its actual readiness endpoint.
        ExecStartPre = "${pkgs.curl}/bin/curl --fail --silent --output /dev/null --retry 150 --retry-delay 2 --retry-all-errors --retry-max-time 300 --max-time 5 http://127.0.0.1:9000/health/ready";
        ExecStart = "${helper}/bin/kaiba-human-identity reconcile";
      };
    };
  };
}
