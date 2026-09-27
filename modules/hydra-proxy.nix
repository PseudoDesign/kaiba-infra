{ config, lib, ... }:
let cfg = config.services.kaibaHydraProxy;
in {
  options.services.kaibaHydraProxy = {
    enable = lib.mkEnableOption "Hydra's public HTTPS endpoint on Mako";
    hostName = lib.mkOption { type = lib.types.str; default = "hydra.pseudo.design"; };
    upstream = lib.mkOption { type = lib.types.str; description = "Ace's reserved address and Hydra port."; };
  };
  config = lib.mkIf cfg.enable {
    services.nginx = {
      enable = true;
      recommendedProxySettings = true;
      recommendedTlsSettings = true;
      virtualHosts.${cfg.hostName} = {
        enableACME = true;
        forceSSL = true;
        locations."/" = {
          proxyPass = "http://${cfg.upstream}";
          extraConfig = ''
            proxy_set_header X-Request-Base https://${cfg.hostName};
            proxy_read_timeout 300;
          '';
        };
      };
    };
    networking.firewall.allowedTCPPorts = [ 80 443 ];
  };
}
