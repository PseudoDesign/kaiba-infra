{ pkgs }:
let
  # Publicly documented NixOS/OpenSSH test keys, never production credentials.
  keys = import (pkgs.path + "/nixos/tests/ssh-keys.nix") pkgs;
  principal = "kaiba:person:00000000-0000-0000-0000-000000000001";
in pkgs.testers.runNixOSTest {
  name = "kaiba-ssh-human-access";
  requiredFeatures.kvm = false;
  nodes.server = { ... }: {
    imports = [ ../modules/ssh-human-access.nix ../modules/hydra-backup-receiver.nix ];
    services.kaibaHumanSSH = {
      enable = true;
      trustedUserCAKeys = [ keys.snakeOilEd25519PublicKey ];
      authorizedPrincipals.adam = [ principal ];
      revokedKeysFile = "/var/lib/kaiba-human-ssh/revoked.krl";
    };
    services.kaibaHydraBackupReceiver.enable = true;
    users.users.adam = {
      isNormalUser = true;
      extraGroups = [ "wheel" ];
      openssh.authorizedKeys.keys = [ keys.snakeOilPublicKey ];
    };
    users.users.other = { isNormalUser = true; };
    security.sudo.wheelNeedsPassword = false;
    services.openssh.settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      # The fixture intentionally sends many failed logins from one client.
      # Production keeps OpenSSH's default brute-force source penalties.
      PerSourcePenalties = "no";
    };
    systemd.services.fixture-krl = {
      wantedBy = [ "multi-user.target" ];
      before = [ "sshd.service" ];
      requiredBy = [ "sshd.service" ];
      serviceConfig.Type = "oneshot";
      script = ''
        install -d -m 0700 /var/lib/kaiba-human-ssh
        if ! test -e /var/lib/kaiba-human-ssh/revoked.krl; then
          ${pkgs.openssh}/bin/ssh-keygen -k -f /var/lib/kaiba-human-ssh/revoked.krl /dev/null
          chmod 0600 /var/lib/kaiba-human-ssh/revoked.krl
        fi
      '';
    };
    environment.systemPackages = [ pkgs.openssh ];
    virtualisation.memorySize = 512;
  };
  nodes.client = {
    environment.systemPackages = [ pkgs.openssh pkgs.python3 pkgs.step-cli ];
    virtualisation.memorySize = 512;
  };
  testScript = ''
    import json
    import shlex

    start_all()
    server.wait_for_unit("sshd.service")
    client.wait_for_unit("multi-user.target")
    client.succeed("install -m 600 ${keys.snakeOilEd25519PrivateKey} /root/ca")
    client.succeed("install -m 600 ${keys.snakeOilPrivateKey} /root/owner")
    client.succeed("ssh-keygen -q -t ed25519 -N \"\" -f /root/human")
    client.succeed("ssh-keyscan server > /root/known_hosts")
    connection = "ssh -n -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/root/known_hosts -o ConnectTimeout=5 "
    certificate = connection + "-i /root/human -o CertificateFile=/root/human-cert.pub "
    recovery = connection + "-i /root/owner "

    def sign(principals="${principal}", validity="-1m:+8h", ca="ca", host=False):
        client.succeed("rm -f /root/human-cert.pub")
        command = "ssh-keygen -q -s /root/" + ca + " -I 'https://auth.example.test/realms/kaiba#00000000-0000-0000-0000-000000000001' -z 42 -V " + shlex.quote(validity)
        if principals is not None:
            command += " -n " + shlex.quote(principals)
        if host:
            command += " -h"
        client.succeed(command + " /root/human.pub")

    with subtest("owner recovery and exact human principal work independently"):
        assert client.succeed(recovery + "adam@server sudo -n id -u").strip() == "0"
        sign()
        assert client.succeed(certificate + "adam@server id -un").strip() == "adam"
        assert client.succeed(certificate + "adam@server sudo -n id -u").strip() == "0"
        server.succeed("test $(stat -Lc %u:%a /etc/ssh/kaiba-human-principals/adam) = 0:444")
        server.succeed("sshd -t")

    with subtest("a trusted CA does not grant root, service, or unlisted account access"):
        for user in ["root", "other", "hydra-backup"]:
            sign(user)
            client.fail(certificate + user + "@server true")
        for principals in ["adam", "kaiba:person:another-person", None]:
            sign(principals)
            client.fail(certificate + "adam@server true")

    with subtest("certificate type, issuer and validity are enforced by sshd"):
        for validity in ["-10m:-5m", "+5m:+10m"]:
            sign(validity=validity)
            client.fail(certificate + "adam@server true")
        sign(ca="owner")
        client.fail(certificate + "adam@server true")
        sign(host=True)
        client.fail(certificate + "adam@server true")

    with subtest("the client inspects an actual OpenSSH certificate and logs out only its own key"):
        sign()
        client.succeed("ssh-agent -a /run/kaiba-test-agent > /run/agent-environment")
        env = "SSH_AUTH_SOCK=/run/kaiba-test-agent "
        client.succeed(env + "ssh-add /root/owner")
        client.succeed(env + "ssh-add /root/human")
        before = client.succeed(env + "ssh-add -L")
        client.succeed("cp ${../client/kaiba.py} /root/kaiba.py")
        # Direct agent signing fixtures avoid a fake browser test. The CA/OIDC
        # boundary is tested separately by ssh-user-ca.nix.
        certificate_text = client.succeed("cat /root/human-cert.pub").strip()
        parsed = json.loads(client.succeed("step ssh inspect --format json /root/human-cert.pub"))
        config = {
            "caURL": "https://ssh-ca.example.test", "rootFingerprint": "a" * 64,
            "sshUserCAFingerprint": parsed["SigningKeyFingerprint"],
            "issuer": "https://auth.example.test/realms/kaiba", "clientID": "kaiba-ssh",
            "principal": "${principal}",
        }
        client.succeed("printf %s " + shlex.quote(json.dumps(config)) + " > /root/config.json")
        # Exercise exact inspection against the real pinned step-cli JSON format.
        client.succeed("python3 -c " + shlex.quote("import sys; sys.path.insert(0, '/root'); import kaiba; from pathlib import Path; c=kaiba.load_config(Path('/root/config.json')); assert kaiba.inspect_certificate(Path('/root/human-cert.pub').read_text(), c)['active']"))
        # A dedicated fixture comment is installed by signing another certificate
        # then adding it with ssh-add, matching the public agent identity contract.
        client.succeed("ssh-keygen -q -t ed25519 -N \"\" -C 'kaiba-human:" + "a" * 32 + "' -f /root/tracked")
        client.succeed("ssh-keygen -q -s /root/ca -I fixture -V -1m:+8h -n '${principal}' /root/tracked.pub")
        # -C loads only the certificate, like step ssh login.
        # This OpenSSH release returns 1 even after a successful certificate-only
        # add; verify the actual agent contents below instead of its exit status.
        code, output = client.execute(env + "ssh-add -C /root/tracked")
        assert code in [0, 1], output
        client.succeed(env + "python3 -c " + shlex.quote("import sys; sys.path.insert(0, '/root'); import kaiba; from pathlib import Path; p=Path('/root/tracked-state'); p.mkdir(mode=0o700); marker='kaiba-human:'+'a'*32; keys=kaiba.owned_keys(marker); certs=[k for k in keys if '-cert-' in k]; assert len(certs)==1; kaiba.write_state(p/'session.json', {'agent': kaiba.agent_identity(), 'comment': marker, 'certificate': certs[0]})"))
        selected = env + connection + "-o IdentityFile=/root/tracked-cert.pub adam@server true"
        client.succeed(selected)
        client.succeed(env + "python3 -c " + shlex.quote("import sys; sys.path.insert(0, '/root'); import kaiba; from pathlib import Path; kaiba.logout(Path('/root/tracked-state/session.json'), kaiba.agent_identity())"))
        client.fail(selected)
        after = client.succeed(env + "ssh-add -L")
        assert after == before, "logout altered unrelated agent identities"

    with subtest("revocation denies the certificate while owner recovery and backup restrictions survive"):
        sign()
        public_certificate = client.succeed("cat /root/human-cert.pub").strip()
        server.succeed("printf '%s\\n' " + shlex.quote(public_certificate) + " > /run/revoked-cert.pub")
        server.succeed("ssh-keygen -k -u -f /var/lib/kaiba-human-ssh/revoked.krl /run/revoked-cert.pub")
        client.fail(certificate + "adam@server true")
        client.succeed(recovery + "adam@server true")
        effective = server.succeed("sshd -T -C user=hydra-backup,host=client,addr=192.0.2.1").lower()
        assert "rrsync -wo /var/backups/hydra/ace" in effective
        assert "disableforwarding yes" in effective
        assert "permittty no" in effective
        server.succeed("systemctl restart sshd")
        server.wait_for_unit("sshd.service")
        client.fail(certificate + "adam@server true")
        client.succeed(recovery + "adam@server true")

    with subtest("unsafe revocation file ownership is rejected before sshd starts"):
        server.succeed("chmod 0666 /var/lib/kaiba-human-ssh/revoked.krl")
        server.fail("systemctl restart sshd")
        server.succeed("chmod 0600 /var/lib/kaiba-human-ssh/revoked.krl; systemctl reset-failed sshd; systemctl start sshd")
        server.wait_for_unit("sshd.service")
        client.succeed(recovery + "adam@server true")
  '';
}
