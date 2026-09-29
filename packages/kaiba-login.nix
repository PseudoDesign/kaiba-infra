{ lib, writeShellApplication, python3, step-cli, openssh, cacert }:
writeShellApplication {
  name = "kaiba";
  runtimeInputs = [ python3 step-cli openssh ];
  text = ''
    if [[ -z "''${SSL_CERT_FILE:-}" ]]; then
      if [[ -r /etc/ssl/certs/ca-certificates.crt ]]; then
        export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
      else
        export SSL_CERT_FILE="${cacert}/etc/ssl/certs/ca-bundle.crt"
      fi
    fi
    exec python3 ${../client/kaiba.py} "$@"
  '';
  meta = {
    description = "Human passkey login for Kaiba SSH certificates";
    platforms = lib.platforms.linux;
    mainProgram = "kaiba";
  };
}
