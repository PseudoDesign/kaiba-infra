{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.kaibaForgejoBackupReceiver;
in
{
  options.services.kaibaForgejoBackupReceiver.enable = lib.mkEnableOption "encrypted forge backup receiver";
  config = lib.mkIf cfg.enable {
    users.groups.forgejo-backup = { };
    users.users.forgejo-backup = {
      isSystemUser = true;
      group = "forgejo-backup";
      home = "/var/lib/kaiba-forgejo-backup-receiver";
      shell = pkgs.bash;
    };
    systemd.tmpfiles.rules = [
      "d /var/lib/kaiba-forgejo-backup-receiver 0755 root root -"
      "d /var/backups/kaiba-forgejo 0700 forgejo-backup forgejo-backup -"
    ];
    services.openssh.extraConfig = ''
      Match User forgejo-backup
        AuthorizedKeysFile /var/lib/kaiba-forgejo-backup-receiver/authorized_keys
        ForceCommand ${pkgs.rrsync}/bin/rrsync -wo /var/backups/kaiba-forgejo
        DisableForwarding yes
        PermitTTY no
        PasswordAuthentication no
        KbdInteractiveAuthentication no
      Match all
    '';
  };
}
