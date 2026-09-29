{ pkgs, stateDir ? "/var/lib/kaiba-ssh-ca" }:
pkgs.writeShellApplication {
  name = "kaiba-ssh-ca-init";
  text = ''
    exec ${pkgs.python3}/bin/python3 ${./ssh-ca-init.py} \
      --step ${pkgs.step-cli}/bin/step --state-dir ${pkgs.lib.escapeShellArg stateDir} "$@"
  '';
}
