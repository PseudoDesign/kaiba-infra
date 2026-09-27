{ config, lib, pkgs, ... }:
let cfg = config.services.kaibaHydraBackupReceiver;
in {
  options.services.kaibaHydraBackupReceiver.enable = lib.mkEnableOption "restricted Hydra backup receiver on Mako";
  config = lib.mkIf cfg.enable {
    users.groups.hydra-backup = { };
    users.users.hydra-backup = {
      isSystemUser = true;
      group = "hydra-backup";
      home = "/var/lib/hydra-backup";
      shell = pkgs.bash;
    };
    systemd.tmpfiles.rules = [
      "d /var/lib/hydra-backup 0755 root root -"
      "d /var/backups/hydra 0750 root hydra-backup -"
      "d /var/backups/hydra/ace 0700 hydra-backup hydra-backup -"
    ];
    services.openssh = {
      enable = true;
      extraConfig = ''
        Match User hydra-backup
          AuthorizedKeysFile /var/lib/hydra-backup/authorized_keys
          ForceCommand ${pkgs.rrsync}/bin/rrsync -wo /var/backups/hydra/ace
          DisableForwarding yes
          PermitTTY no
          PasswordAuthentication no
          KbdInteractiveAuthentication no
        Match all
      '';
    };
  };
}
