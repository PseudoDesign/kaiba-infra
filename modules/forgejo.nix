{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.kaibaForgejo;
in
{
  imports = [
    ./forgejo-backup.nix
    ./forgejo-sso.nix
  ];
  options.services.kaibaForgejo = {
    enable = lib.mkEnableOption "Kaiba Forgejo";
    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.forgejo-lts;
    };
    domain = lib.mkOption {
      type = lib.types.str;
      default = "git.pseudo.design";
    };
    docsDomain = lib.mkOption {
      type = lib.types.str;
      default = "docs.kaiba.pseudo.design";
    };
    enableACME = lib.mkOption {
      type = lib.types.bool;
      default = true;
    };
    actionsEnable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Enable only after isolated builders and workflow admission are qualified.";
    };
    memoryHighMB = lib.mkOption {
      type = lib.types.ints.positive;
      default = 384;
    };
    memoryMaxMB = lib.mkOption {
      type = lib.types.ints.positive;
      default = 512;
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.memoryMaxMB > cfg.memoryHighMB;
        message = "Forgejo's memory maximum must exceed its pressure threshold.";
      }
    ];
    services.forgejo = {
      enable = true;
      package = cfg.package;
      stateDir = "/var/lib/forgejo";
      database = {
        type = "postgres";
        name = "forgejo";
        user = "forgejo";
        socket = "/run/postgresql";
      };
      lfs.enable = true;
      settings = {
        DEFAULT.APP_NAME = "Kaiba Git";
        server = {
          DOMAIN = cfg.domain;
          ROOT_URL = "https://${cfg.domain}/";
          HTTP_ADDR = "127.0.0.1";
          HTTP_PORT = 3010;
          DISABLE_SSH = true;
          START_SSH_SERVER = false;
          SSH_CREATE_AUTHORIZED_KEYS_FILE = false;
        };
        service = {
          DISABLE_REGISTRATION = true;
          ALLOW_ONLY_EXTERNAL_REGISTRATION = true;
          SHOW_REGISTRATION_BUTTON = false;
          REQUIRE_SIGNIN_VIEW = false;
        };
        oauth2_client = {
          ENABLE_AUTO_REGISTRATION = cfg.sso.enable;
          ACCOUNT_LINKING = "disabled";
        };
        openid = {
          ENABLE_OPENID_SIGNIN = false;
          ENABLE_OPENID_SIGNUP = false;
        };
        repository = {
          DEFAULT_PRIVATE = "last";
          DISABLE_HTTP_GIT = false;
        };
        security = {
          REVERSE_PROXY_LIMIT = 1;
          REVERSE_PROXY_TRUSTED_PROXIES = "127.0.0.1/32,::1/128";
        };
        session.COOKIE_SECURE = true;
        database.MAX_OPEN_CONNS = 10;
        indexer.REPO_INDEXER_ENABLED = false;
        actions.ENABLED = cfg.actionsEnable;
        "cron.cleanup_actions" = {
          ENABLED = true;
          SCHEDULE = "@daily";
        };
        log.LEVEL = "Warn";
      };
    };
    # The pinned Forgejo wrapper supplies Git/GnuPG itself. Avoid rebuilding
    # the Pi overlay's unrelated Git toolchain on the service host.
    systemd.services.forgejo.path = lib.mkForce [
      cfg.package
      pkgs.coreutils
      pkgs.findutils
      pkgs.gnugrep
      pkgs.gnused
      pkgs.systemd
      pkgs.util-linux
    ];
    systemd.services.forgejo.serviceConfig = {
      MemoryHigh = "${toString cfg.memoryHighMB}M";
      MemoryMax = "${toString cfg.memoryMaxMB}M";
      MemorySwapMax = 0;
      CPUQuota = "100%";
      UMask = "0027";
    };
    services.nginx = {
      enable = true;
      virtualHosts.${cfg.domain} = {
        enableACME = cfg.enableACME;
        forceSSL = cfg.enableACME;
        locations."/" = {
          proxyPass = "http://127.0.0.1:3010";
          proxyWebsockets = true;
          extraConfig = ''
            client_max_body_size 2g;
            proxy_read_timeout 600s;
            proxy_send_timeout 600s;
          '';
        };
      };
      virtualHosts.${cfg.docsDomain} = {
        enableACME = cfg.enableACME;
        forceSSL = cfg.enableACME;
        root = "/var/lib/kaiba-docs/current";
        locations."/".tryFiles = "$uri $uri/ =404";
        extraConfig = ''
          add_header X-Content-Type-Options nosniff always;
          add_header Referrer-Policy strict-origin-when-cross-origin always;
        '';
      };
    };
    systemd.tmpfiles.rules = [
      "d /var/lib/kaiba-docs 0755 root root -"
      "d /var/lib/kaiba-docs/releases 0755 root root -"
    ];
    networking.firewall.allowedTCPPorts = [
      80
      443
    ];
  };
}
