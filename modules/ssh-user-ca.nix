{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaSSHUserCA;
  state = "/var/lib/kaiba-ssh-ca";
  sshTemplate = pkgs.writeText "kaiba-ssh-user-certificate.tpl" (builtins.replaceStrings
    [ "@ISSUER@" ] [ (builtins.toJSON cfg.issuer) ] (builtins.readFile ../identity/ssh-user-certificate.tpl));
  settings = {
    address = "127.0.0.1:${toString cfg.listenPort}";
    dnsNames = [ cfg.hostName "localhost" ];
    logger.format = "json";
    db = { type = "badgerv2"; dataSource = "/var/lib/kaiba-ssh-ca-db"; };
    authority = {
      enableAdmin = false;
      disableIssuedAtCheck = false;
      claims = { enableSSHCA = true; disableRenewal = true; };
      provisioners = [{
        type = "OIDC";
        name = "kaiba-human";
        clientID = cfg.clientID;
        clientSecret = "";
        configurationEndpoint = "${cfg.issuer}/.well-known/openid-configuration";
        listenAddress = "127.0.0.1:8400";
        admins = [];
        groups = [ cfg.allowedGroup ];
        scopes = [ "openid" "email" "profile" ];
        claims = {
          enableSSHCA = true;
          disableRenewal = true;
          minUserSSHCertDuration = "5m";
          defaultUserSSHCertDuration = "8h";
          maxUserSSHCertDuration = "8h";
        };
        options = {
          ssh.templateFile = toString sshTemplate;
          x509.templateFile = toString ../identity/ssh-reject-x509.tpl;
        };
      }];
    };
    tls = { minVersion = 1.2; maxVersion = 1.3; renegotiation = false; };
  };
  configFile = (pkgs.formats.json {}).generate "kaiba-ssh-ca.json" settings;
  oidcReady = pkgs.writeShellScript "kaiba-ssh-ca-oidc-ready" ''
    exec ${pkgs.python3}/bin/python3 ${../identity/ssh-oidc-ready.py} \
      --issuer ${lib.escapeShellArg cfg.issuer} \
      --trust-bundle ${lib.escapeShellArg (if cfg.oidcTrustBundle != null
        then "${cfg.oidcTrustBundle}" else "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt")}
  '';
  run = pkgs.writeShellScript "kaiba-ssh-ca-start" ''
    set -eu
    umask 077
    ${pkgs.jq}/bin/jq --arg credentials "$CREDENTIALS_DIRECTORY" '
      .root = ($credentials + "/root_ca.crt") |
      .crt = ($credentials + "/intermediate_ca.crt") |
      .key = ($credentials + "/intermediate_ca_key") |
      .ssh = {userKey: ($credentials + "/ssh_user_ca_key")}
    ' ${configFile} > "$RUNTIME_DIRECTORY/ca.json"
    exec ${pkgs.python3}/bin/python3 ${../identity/ssh-ca-log.py} \
      ${cfg.package}/bin/step-ca "$RUNTIME_DIRECTORY/ca.json" \
      --password-file "$CREDENTIALS_DIRECTORY/password"
  '';
in {
  options.services.kaibaSSHUserCA = {
    enable = lib.mkEnableOption "Kaiba's passkey-authenticated human SSH certificate authority";
    package = lib.mkOption {
      type = lib.types.package;
      default = import ../identity/ssh-ca-package.nix { inherit pkgs; };
      description = "Pinned step-ca with Kaiba's issuance-time ceiling for SSH user certificates.";
    };
    hostName = lib.mkOption { type = lib.types.str; default = "ssh-ca.pseudo.design"; };
    issuer = lib.mkOption { type = lib.types.str; default = "https://auth.pseudo.design/realms/kaiba"; };
    clientID = lib.mkOption { type = lib.types.str; default = "kaiba-ssh"; };
    allowedGroup = lib.mkOption { type = lib.types.str; default = "kaiba-ssh-admin"; };
    listenPort = lib.mkOption { type = lib.types.port; default = 8443; };
    memoryMax = lib.mkOption { type = lib.types.str; default = "256M"; };
    oidcTrustBundle = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Additional public CA bundle for private OIDC TLS (primarily integration tests).";
    };
    proxy.enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Expose nginx HTTPS. Initialize the CA before activating this vhost, or bootstrap with this disabled.";
    };
    initPackage = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      default = import ../identity/ssh-ca-init-package.nix { inherit pkgs; };
      description = "Explicit root initialization command. Refuses any existing /var/lib/kaiba-ssh-ca path and prints only public trust.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [{
      assertion = lib.hasPrefix "https://" cfg.issuer && !(lib.hasSuffix "/" cfg.issuer);
      message = "kaibaSSHUserCA.issuer must be an HTTPS issuer URL without a trailing slash.";
    }];
    environment.systemPackages = [ cfg.initPackage ];
    environment.etc."kaiba-ssh-ca/config.json".source = configFile;
    systemd.services.kaiba-ssh-ca = {
      description = "Kaiba human SSH user certificate authority";
      wantedBy = [ "multi-user.target" ];
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      unitConfig = {
        ConditionPathExists = "${state}/initialized";
        StartLimitIntervalSec = 0;
      };
      environment = lib.optionalAttrs (cfg.oidcTrustBundle != null) {
        # Interpolation copies Nix path literals into the closure; toString
        # would leave a reference to an unavailable source-tree path at runtime.
        SSL_CERT_FILE = "${cfg.oidcTrustBundle}";
      };
      serviceConfig = {
        Type = "simple";
        # step-ca otherwise keeps running with OIDC disabled if discovery fails
        # once during initialization (for example before ACME replaces a cert).
        ExecStartPre = oidcReady;
        ExecStart = run;
        TimeoutStartSec = "30s";
        DynamicUser = true;
        User = "kaiba-ssh-ca";
        StateDirectory = "kaiba-ssh-ca-db";
        StateDirectoryMode = "0700";
        RuntimeDirectory = "kaiba-ssh-ca";
        RuntimeDirectoryMode = "0700";
        LoadCredential = map (name: "${name}:${state}/${name}") [
          "root_ca.crt" "intermediate_ca.crt" "intermediate_ca_key" "ssh_user_ca_key" "password"
        ];
        UMask = "0077";
        Restart = "on-failure";
        RestartSec = "10s";
        MemoryMax = cfg.memoryMax;
        NoNewPrivileges = true;
        PrivateTmp = true;
        PrivateDevices = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectControlGroups = true;
        RestrictSUIDSGID = true;
        RestrictNamespaces = true;
        LockPersonality = true;
        CapabilityBoundingSet = "";
        RestrictAddressFamilies = [ "AF_UNIX" "AF_INET" "AF_INET6" ];
      };
    };
    # NixOS runs nginx without root's directory traversal permission. Publish
    # just the public transport root into /run; private CA state stays 0700.
    systemd.services.kaiba-ssh-ca-trust = lib.mkIf cfg.proxy.enable {
      description = "Publish the public SSH CA transport root for nginx";
      before = [ "nginx.service" ];
      requiredBy = [ "nginx.service" ];
      unitConfig.ConditionPathExists = "${state}/initialized";
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        RuntimeDirectory = "kaiba-ssh-ca-trust";
        RuntimeDirectoryMode = "0755";
        ExecStart = "${pkgs.coreutils}/bin/install -m 0444 ${state}/root_ca.crt /run/kaiba-ssh-ca-trust/root_ca.crt";
        UMask = "0077";
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        NoNewPrivileges = true;
      };
    };
    services.nginx = lib.mkIf cfg.proxy.enable {
      enable = true;
      recommendedProxySettings = true;
      recommendedTlsSettings = true;
      virtualHosts.${cfg.hostName} = {
        enableACME = true;
        forceSSL = true;
        locations."/" = {
          proxyPass = "https://127.0.0.1:${toString cfg.listenPort}";
          extraConfig = ''
            proxy_ssl_server_name on;
            proxy_ssl_name ${cfg.hostName};
            proxy_ssl_verify on;
            proxy_ssl_verify_depth 2;
            proxy_ssl_trusted_certificate /run/kaiba-ssh-ca-trust/root_ca.crt;
            client_max_body_size 128k;
          '';
        };
      };
    };
    networking.firewall.allowedTCPPorts = lib.mkIf cfg.proxy.enable [ 80 443 ];
  };
}
