{ pkgs }:
let
  certs = import (pkgs.path + "/nixos/tests/common/acme/server/snakeoil-certs.nix");
  browserPython = pkgs.python3.withPackages (ps: [ ps.selenium ps.cryptography ]);
  caProxy = {
    proxyPass = "https://127.0.0.1:8443";
    extraConfig = ''
      proxy_ssl_server_name on;
      proxy_ssl_name ${certs.domain};
      proxy_ssl_verify on;
      proxy_ssl_verify_depth 2;
      proxy_ssl_trusted_certificate /run/kaiba-ssh-ca-root.crt;
      access_log off;
    '';
  };
in pkgs.testers.runNixOSTest {
  name = "kaiba-human-identity";
  nodes.identity = { config, lib, ... }: {
    imports = [ ../modules/human-identity.nix ../modules/ssh-user-ca.nix ];
    services.kaibaHumanIdentity = {
      enable = true;
      domain = certs.domain;
      bootstrapAdminPasswordFile = "/var/lib/kaiba-human-identity/bootstrap-admin-password";
    };
    systemd.services.kaiba-human-identity-secrets.preStart = ''
      install -d -m 0700 /var/lib/kaiba-human-identity
      printf %s test-only-identity-bootstrap > /var/lib/kaiba-human-identity/bootstrap-admin-password
      chmod 0600 /var/lib/kaiba-human-identity/bootstrap-admin-password
    '';
    services.kaibaSSHUserCA = {
      enable = true;
      hostName = certs.domain;
      issuer = "https://${certs.domain}/realms/kaiba";
      oidcTrustBundle = certs.ca.cert;
      proxy.enable = false;
    };
    systemd.services.test-ca-init = {
      before = [ "nginx.service" "kaiba-ssh-ca.service" ];
      requiredBy = [ "nginx.service" "kaiba-ssh-ca.service" ];
      serviceConfig = { Type = "oneshot"; RemainAfterExit = true; };
      script = ''
        ${config.services.kaibaSSHUserCA.initPackage}/bin/kaiba-ssh-ca-init > /run/public-trust.json
        install -m 0644 /var/lib/kaiba-ssh-ca/root_ca.crt /run/kaiba-ssh-ca-root.crt
      '';
    };
    services.nginx = {
      enable = true;
      virtualHosts.${certs.domain} = {
        enableACME = lib.mkForce false;
        sslCertificate = certs.${certs.domain}.cert;
        sslCertificateKey = certs.${certs.domain}.key;
        locations."/ssh/" = caProxy;
        locations."/root/" = caProxy;
        locations."= /provisioners" = caProxy;
        locations."= /version" = caProxy;
      };
    };
    # This environment lacks KVM; restrict optional x86 intrinsics under TCG.
    # ARM live deployments keep the normal JVM configuration.
    systemd.services.keycloak.environment.JAVA_OPTS_APPEND = lib.mkIf pkgs.stdenv.hostPlatform.isx86_64 "-XX:UseAVX=0 -XX:-UseSHA";
    networking.firewall.allowedTCPPorts = [ 80 443 ];
    networking.extraHosts = "127.0.0.1 ${certs.domain}";
    security.pki.certificateFiles = [ certs.ca.cert ];
    virtualisation.memorySize = 2048;
    virtualisation.cores = 2;
    environment.systemPackages = [ pkgs.python3 pkgs.curl ];
  };
  nodes.browser = { nodes, ... }: {
    networking.extraHosts = "${nodes.identity.networking.primaryIPAddress} ${certs.domain}";
    security.pki.certificateFiles = [ certs.ca.cert ];
    virtualisation.memorySize = 2048;
    virtualisation.cores = 2;
    environment.systemPackages = [
      pkgs.chromium pkgs.chromedriver browserPython pkgs.curl pkgs.openssh
      (pkgs.callPackage ../packages/kaiba-login.nix {})
    ];
  };
  testScript = ''
    import json

    def browser_ready(marker):
        browser.wait_until_succeeds("test -f /tmp/" + marker + " -o -f /tmp/browser-flow-failed", timeout=180)
        browser.succeed("if test -f /tmp/browser-flow-failed; then cat /tmp/browser-flow.log; exit 1; fi")

    start_all()
    identity.wait_for_unit("kaiba-human-identity-configure.service", timeout=600)
    identity.wait_for_open_port(8080)
    identity.wait_for_unit("kaiba-ssh-ca.service")
    identity.wait_for_open_port(8443)
    identity.succeed("curl -fsS https://${certs.domain}/realms/kaiba/.well-known/openid-configuration > /tmp/discovery.json")
    identity.succeed("cp ${../identity/keycloak_admin.py} /tmp/keycloak_admin.py")
    identity.succeed("cp ${./identity/assert_policy.py} /tmp/assert_policy.py")
    identity.succeed("python3 /tmp/assert_policy.py")
    identity.fail("runuser -u nobody -- cat /var/lib/kaiba-human-identity/bootstrap-admin-password")
    identity.succeed("systemctl restart kaiba-human-identity-configure")
    identity.succeed("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-start --owner owner")
    identity.fail("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-start --owner second-owner")
    identity.fail("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-finalize")
    identity.succeed("python3 -c 'import json; p=\"/var/lib/kaiba-human-identity/owner-enrollment.json\"; x=json.load(open(p)); x[\"expires_at\"]=0; open(p,\"w\").write(json.dumps(x))'")
    identity.succeed("systemctl start kaiba-human-identity-enrollment-expiry")
    identity.succeed("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-resume")
    status = json.loads(identity.succeed("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-status"))
    assert status["phase"] == "enrolling" and status["passkey_count"] == 0
    assert status["principal"] == "kaiba:person:" + status["subject"]

    # Real Chromium WebAuthn calls against the live Keycloak service use only
    # virtual test authenticators; no hardware passkey success is claimed.
    fixture = {
        "ssh_ca_public_key": identity.succeed("cat /var/lib/kaiba-ssh-ca/ssh_user_ca.pub").strip(),
        "rootFingerprint": json.loads(identity.succeed("cat /run/public-trust.json"))["rootFingerprint"],
        "url": identity.succeed("cat /var/lib/kaiba-human-identity/owner-enrollment-url").strip(),
        "password": identity.succeed("cat /var/lib/kaiba-human-identity/owner-enrollment-password").strip(),
    }
    browser.succeed("cat > /tmp/enrollment.json <<'FIXTURE'\n" + json.dumps(fixture) + "\nFIXTURE")
    browser.succeed("cp ${./identity/browser_flow.py} /tmp/browser_flow.py")
    browser.succeed("cp ${./identity/client_flow.py} /tmp/client_flow.py")
    browser.succeed("python3 /tmp/browser_flow.py > /tmp/browser-flow.log 2>&1 &")
    browser_ready("first-passkey-ready")
    identity.fail("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-finalize")
    browser.succeed("touch /tmp/register-second")
    browser_ready("second-passkey-ready")
    # Expiry removes bootstrap access without granting SSH. Local-root
    # finalization remains possible using the two already registered passkeys.
    identity.succeed("python3 -c 'import json; p=\"/var/lib/kaiba-human-identity/owner-enrollment.json\"; x=json.load(open(p)); x[\"expires_at\"]=0; open(p,\"w\").write(json.dumps(x))'")
    identity.succeed("systemctl start kaiba-human-identity-enrollment-expiry")
    identity.succeed("test ! -e /var/lib/kaiba-human-identity/owner-enrollment-password")
    identity.succeed("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-finalize")
    identity.succeed("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-finalize")
    browser.succeed("touch /tmp/owner-finalized")
    browser_ready("passkey-login-success")
    browser.succeed("test ! -e /tmp/browser-flow-failed")
    identity.succeed("python3 /tmp/assert_policy.py --enrolled")
    identity.fail("kaiba-human-identity --password-file /var/lib/kaiba-human-identity/bootstrap-admin-password enroll-resume")
    identity.succeed("systemctl restart keycloak")
    identity.wait_for_unit("keycloak.service", timeout=300)
    identity.succeed("systemctl restart kaiba-human-identity-configure")
    identity.succeed("python3 /tmp/assert_policy.py --enrolled")
    identity.succeed("test $(systemctl show keycloak -p MemoryMax --value) = 1073741824")
    identity.succeed("test $(systemctl show keycloak -p MemorySwapMax --value) = 0")
    print("Keycloak cgroup peak bytes:", identity.succeed("systemctl show keycloak -p MemoryPeak --value").strip())
    print("PostgreSQL memory bytes:", identity.succeed("systemctl show postgresql -p MemoryCurrent --value").strip())
  '';
}
