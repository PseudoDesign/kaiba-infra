{ config, lib, pkgs, ... }:
let
  cfg = config.services.kaibaHumanSSH;
  users = builtins.attrNames cfg.authorizedPrincipals;
  principalType = lib.types.strMatching "kaiba:person:[A-Za-z0-9._-]+";
in {
  options.services.kaibaHumanSSH = {
    enable = lib.mkEnableOption "certificate authentication for explicitly authorized humans";
    trustedUserCAKeys = lib.mkOption {
      type = lib.types.listOf lib.types.singleLineStr;
      default = [ ];
      description = "Public OpenSSH user CA keys; never private signing keys.";
    };
    authorizedPrincipals = lib.mkOption {
      type = lib.types.attrsOf (lib.types.listOf principalType);
      default = { };
      example = { adam = [ "kaiba:person:00000000-0000-0000-0000-000000000001" ]; };
      description = "Existing normal Unix users and their exact immutable human principals. Unlisted accounts have no certificate access.";
    };
    revokedKeysFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "/var/lib/kaiba-human-ssh/revoked.krl";
      description = ''
        Absolute path to an existing root-owned OpenSSH KRL. Provision it before
        enabling and replace it atomically. An absent/unreadable KRL causes
        OpenSSH to reject all public-key logins, including recovery keys.
        The module never initializes or silently replaces revocation state.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      { assertion = cfg.trustedUserCAKeys != [ ]; message = "kaibaHumanSSH requires a public user CA key."; }
      { assertion = users != [ ]; message = "kaibaHumanSSH requires explicit human principal mappings."; }
      {
        assertion = lib.all (name:
          builtins.match "[a-z_][a-z0-9_-]*" name != null
          && name != "root"
          && builtins.hasAttr name config.users.users
          && config.users.users.${name}.isNormalUser
          && cfg.authorizedPrincipals.${name} != [ ]
        ) users;
        message = "kaibaHumanSSH principal mappings must name existing normal users, never root/service accounts.";
      }
      {
        assertion = cfg.revokedKeysFile == null ||
          (lib.hasPrefix "/" cfg.revokedKeysFile && !lib.hasPrefix "/nix/store/" cfg.revokedKeysFile);
        message = "kaibaHumanSSH.revokedKeysFile must be an absolute runtime path outside the Nix store.";
      }
    ];
    services.openssh = {
      enable = true;
      settings = {
        TrustedUserCAKeys = toString (pkgs.writeText "kaiba-human-ssh-user-ca.pub"
          (lib.concatStringsSep "\n" cfg.trustedUserCAKeys + "\n"));
        # An absent per-user file denies certificates instead of falling back
        # to matching a Unix username. Ordinary authorized_keys are unchanged.
        AuthorizedPrincipalsFile = "/etc/ssh/kaiba-human-principals/%u";
        LogLevel = lib.mkDefault "VERBOSE";
      } // lib.optionalAttrs (cfg.revokedKeysFile != null) {
        RevokedKeys = cfg.revokedKeysFile;
      };
    };
    environment.etc = lib.mapAttrs' (name: principals:
      lib.nameValuePair "ssh/kaiba-human-principals/${name}" {
        text = lib.concatStringsSep "\n" principals + "\n";
        mode = "0444";
      }
    ) cfg.authorizedPrincipals;
    systemd.services.sshd.serviceConfig.ExecStartPre = lib.mkIf (cfg.revokedKeysFile != null) [
      (pkgs.writeShellScript "kaiba-human-ssh-check-krl" ''
        set -eu
        file=${lib.escapeShellArg cfg.revokedKeysFile}
        test ! -L "$file"
        test -f "$file"
        test "$(${pkgs.coreutils}/bin/stat -c %u "$file")" = 0
        test "$(${pkgs.coreutils}/bin/stat -c %h "$file")" = 1
        mode=$(${pkgs.coreutils}/bin/stat -c %a "$file")
        test "$((0$mode & 0022))" = 0
        test "$(${pkgs.coreutils}/bin/readlink -f "$file")" = "$file"
        directory=$(${pkgs.coreutils}/bin/dirname "$file")
        while :; do
          test "$(${pkgs.coreutils}/bin/stat -c %u "$directory")" = 0
          mode=$(${pkgs.coreutils}/bin/stat -c %a "$directory")
          test "$((0$mode & 0022))" = 0
          test "$directory" != / || break
          directory=$(${pkgs.coreutils}/bin/dirname "$directory")
        done
        # Ask OpenSSH to parse the KRL; no private key is read.
        ${pkgs.openssh}/bin/ssh-keygen -Q -l -f "$file" >/dev/null
      '')
    ];
  };
}
