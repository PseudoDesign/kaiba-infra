{ config, lib, pkgs, ... }:
let cfg = config.services.kaibaHumanAccessBackupReceiver;
in {
  options.services.kaibaHumanAccessBackupReceiver.enable = lib.mkEnableOption "ciphertext-only human access backup receiver on Ace";
  config = lib.mkIf cfg.enable {
    users.groups.human-access-backup = {};
    users.users.human-access-backup = {
      isSystemUser = true;
      group = "human-access-backup";
      home = "/var/lib/kaiba-human-backup-receiver";
      shell = pkgs.bash;
    };
    systemd.tmpfiles.rules = [
      "d /var/lib/kaiba-human-backup-receiver 0755 root root -"
      "d /var/backups/kaiba-human-access 0700 human-access-backup human-access-backup -"
    ];
    services.openssh = {
      enable = true;
      extraConfig = ''
        Match User human-access-backup
          AuthorizedKeysFile /var/lib/kaiba-human-backup-receiver/authorized_keys
          ForceCommand ${pkgs.rrsync}/bin/rrsync -wo /var/backups/kaiba-human-access
          DisableForwarding yes
          PermitTTY no
          PasswordAuthentication no
          KbdInteractiveAuthentication no
        Match all
      '';
    };
  };
}
