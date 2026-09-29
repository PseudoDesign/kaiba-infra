{ pkgs }:
let
  certs = import (pkgs.path + "/nixos/tests/common/acme/server/snakeoil-certs.nix");
  python = pkgs.python3.withPackages (p: [ p.cryptography p.pyjwt ]);
  fixture = ./ssh-oidc-fixture.py;
in pkgs.testers.runNixOSTest {
  name = "kaiba-ssh-user-ca";
  requiredFeatures.kvm = false;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules/ssh-user-ca.nix ];
    services.kaibaSSHUserCA = {
      enable = true;
      hostName = certs.domain;
      issuer = "https://oidc.test:9443";
      oidcTrustBundle = "/run/oidc-trust.crt";
      proxy.enable = true;
    };
    networking.hosts."127.0.0.1" = [ "oidc.test" certs.domain ];
    services.nginx.virtualHosts.${certs.domain} = {
      enableACME = lib.mkForce false;
      sslCertificate = certs.${certs.domain}.cert;
      sslCertificateKey = certs.${certs.domain}.key;
    };
    # The bootstrap phase installs trust explicitly before enabling ingress.
    systemd.services.nginx.wantedBy = lib.mkForce [];
    systemd.services.oidc-fixture = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig.ExecStart = "${python}/bin/python3 ${fixture} serve";
    };
    environment.systemPackages = [ python pkgs.openssh pkgs.curl ];
    virtualisation.memorySize = 1024;
  };
  testScript = ''
    start_all()
    machine.wait_for_unit("multi-user.target")
    machine.wait_for_open_port(9443)
    # Booting an uninitialized host never silently creates new trust.
    machine.succeed("test ! -e /var/lib/kaiba-ssh-ca")
    machine.fail("systemctl is-active --quiet kaiba-ssh-ca.service")
    machine.succeed("kaiba-ssh-ca-init > /run/public-trust.json")
    fingerprint = machine.succeed("sha256sum /var/lib/kaiba-ssh-ca/root_ca.crt /var/lib/kaiba-ssh-ca/ssh_user_ca.pub")
    machine.fail("kaiba-ssh-ca-init")
    assert fingerprint == machine.succeed("sha256sum /var/lib/kaiba-ssh-ca/root_ca.crt /var/lib/kaiba-ssh-ca/ssh_user_ca.pub")
    machine.succeed("test $(stat -c %a /var/lib/kaiba-ssh-ca) = 700; test $(stat -c %a /var/lib/kaiba-ssh-ca/password) = 600")
    # Discovery outages and initially untrusted TLS must prevent a running CA
    # with OIDC disabled. Once issuer trust is ready, startup retries recover
    # automatically; never manually restart the CA to make this test pass.
    machine.succeed("cp /run/fixture-oidc.crt /run/oidc-trust.crt; systemctl stop oidc-fixture")
    machine.fail("systemctl start kaiba-ssh-ca.service")
    machine.fail("systemctl is-active --quiet kaiba-ssh-ca.service")
    machine.fail("curl --cacert /var/lib/kaiba-ssh-ca/root_ca.crt -fsS https://localhost:8443/health")
    machine.succeed("cp ${certs.ca.cert} /run/oidc-trust.crt; systemctl start oidc-fixture")
    machine.wait_for_open_port(9443)
    restarts = int(machine.succeed("systemctl show kaiba-ssh-ca -p NRestarts --value").strip())
    machine.wait_until_succeeds(f"test $(systemctl show kaiba-ssh-ca -p NRestarts --value) -gt {restarts}", timeout=30)
    machine.wait_until_succeeds("journalctl -u kaiba-ssh-ca --no-pager | grep -F CERTIFICATE_VERIFY_FAILED", timeout=30)
    machine.fail("curl --cacert /var/lib/kaiba-ssh-ca/root_ca.crt -fsS https://localhost:8443/health")
    machine.succeed("cp /run/fixture-oidc.crt /run/oidc-trust.crt")
    machine.wait_for_unit("kaiba-ssh-ca.service")
    machine.wait_for_open_port(8443)
    machine.succeed("systemctl start nginx.service")
    machine.wait_for_unit("kaiba-ssh-ca-trust.service")
    machine.succeed("test $(stat -c %a /run/kaiba-ssh-ca-trust) = 755; test $(stat -c %a /run/kaiba-ssh-ca-trust/root_ca.crt) = 444")
    machine.succeed("runuser -u nginx -- test -r /run/kaiba-ssh-ca-trust/root_ca.crt")
    machine.fail("runuser -u nginx -- test -r /var/lib/kaiba-ssh-ca/root_ca.crt")
    machine.succeed("curl --cacert ${certs.ca.cert} -fsS https://${certs.domain}/health")
    # Prove nginx verifies the internal TLS chain, rather than accepting any
    # certificate from a process listening on the configured local port.
    machine.succeed("install -m 0444 ${certs.ca.cert} /run/kaiba-ssh-ca-trust/root_ca.crt; systemctl reload nginx")
    machine.wait_until_fails("curl --cacert ${certs.ca.cert} -fsS https://${certs.domain}/health", timeout=30)
    machine.succeed("install -m 0444 /var/lib/kaiba-ssh-ca/root_ca.crt /run/kaiba-ssh-ca-trust/root_ca.crt; systemctl reload nginx")
    machine.wait_until_succeeds("curl --cacert ${certs.ca.cert} -fsS https://${certs.domain}/health", timeout=30)
    machine.succeed("${python}/bin/python3 ${fixture} verify")
    journal = machine.succeed("journalctl -u kaiba-ssh-ca --no-pager")
    assert chr(34) + "ott" + chr(34) not in journal, "bearer token field reached journal"
    machine.succeed("systemctl restart kaiba-ssh-ca.service")
    machine.wait_for_open_port(8443)
    machine.succeed("curl --cacert /var/lib/kaiba-ssh-ca/root_ca.crt -fsS https://localhost:8443/health")
    assert fingerprint == machine.succeed("sha256sum /var/lib/kaiba-ssh-ca/root_ca.crt /var/lib/kaiba-ssh-ca/ssh_user_ca.pub")
    machine.succeed("ssh-keygen -Lf /run/issued-cert.pub")
    machine.fail("runuser -u nobody -- cat /var/lib/kaiba-ssh-ca/password")
    machine.fail("runuser -u nobody -- cat /run/credentials/kaiba-ssh-ca.service/ssh_user_ca_key")
  '';
}
