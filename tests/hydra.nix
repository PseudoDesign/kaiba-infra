{ pkgs }:
pkgs.testers.runNixOSTest {
  name = "kaiba-hydra-integration";
  # Also runnable under emulation on development machines without KVM.
  requiredFeatures.kvm = false;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules/hydra.nix ];
    services.kaibaHydra = {
      enable = true;
      publicURL = "http://localhost:3000";
      proxyAddress = "192.0.2.1";
      backup = {
        enable = true;
        host = "receiver";
        keyFile = "/run/backup-key";
        knownHostsFile = "/run/backup-known-hosts";
      };
    };
    systemd.timers.kaiba-hydra-backup.wantedBy = lib.mkForce [ ];
    virtualisation.memorySize = 3072;
    virtualisation.cores = 2;
    environment.systemPackages = [ pkgs.python3 pkgs.curl pkgs.openssh ];
  };
  nodes.receiver = {
    imports = [ ../modules/hydra-backup-receiver.nix ];
    services.kaibaHydraBackupReceiver.enable = true;
    networking.firewall.allowedTCPPorts = [ 22 ];
    virtualisation.memorySize = 768;
  };
  testScript = ''
    start_all()
    machine.wait_for_unit("hydra-server.service")
    machine.wait_for_open_port(3000)
    machine.succeed("su - hydra -c 'hydra-create-user adam --password test-only-password --role admin'")
    machine.succeed("install -m 600 /dev/null /run/hydra-password; printf %s test-only-password > /run/hydra-password")
    machine.succeed("cp -r ${../ci} /tmp/ci")
    command = "python3 /tmp/ci/setup_hydra.py --url http://localhost:3000 --apply --password-file /run/hydra-password"
    machine.succeed(command)
    machine.succeed(command)
    machine.succeed("curl -fsS -H 'Accept: application/json' http://localhost:3000/jobset/kaiba-provisioning/main | python3 -c 'import json,sys; assert json.load(sys.stdin)[\"enabled\"] == 0'")
    machine.fail(command + " --stage provisioning")
    machine.succeed("systemctl restart hydra-server")
    machine.wait_for_open_port(3000)
    machine.succeed(command)
    machine.succeed("test $(stat -c %a /var/tmp/nix-build) = 1777")
    machine.succeed("systemctl show hydra-evaluator -p Environment --value > /tmp/evaluator.env")
    machine.succeed("python3 -c 'import os,shlex,subprocess; env=dict(os.environ); env.update(item.split(\"=\", 1) for item in shlex.split(open(\"/tmp/evaluator.env\").read())); result=subprocess.run([\"${pkgs.util-linux}/bin/runuser\", \"-u\", \"hydra\", \"--\", \"/run/current-system/sw/bin/nix\", \"eval\", \"--impure\", \"--expr\", \"builtins.readFile /etc/hostname\"], env=env, capture_output=True); assert result.returncode != 0 and b\"forbidden\" in result.stderr, result.stderr'")
    receiver.wait_for_unit("sshd.service")
    machine.succeed("ssh-keygen -q -t ed25519 -N \"\" -f /run/backup-key")
    public_key = machine.succeed("cat /run/backup-key.pub").strip()
    receiver.succeed(f"echo '{public_key}' > /var/lib/hydra-backup/authorized_keys; chmod 644 /var/lib/hydra-backup/authorized_keys")
    # Synthetic VM hosts and test-only key; production pins the verified key.
    machine.succeed("ssh-keyscan receiver > /run/backup-known-hosts")
    machine.succeed("systemctl start kaiba-hydra-backup")
    receiver.succeed("cd /var/backups/hydra/ace/$(date -u +%F); sha256sum -c SHA256SUMS")
    machine.succeed("runuser -u postgres -- createdb hydra_restore")
    machine.succeed("cat /var/backups/hydra/$(date -u +%F)/hydra.dump | runuser -u postgres -- pg_restore --no-owner -d hydra_restore")
    assert machine.succeed("runuser -u postgres -- psql -At -d hydra_restore -c \"select enabled from jobsets where project='kaiba-provisioning'\"").strip() == "0"
    machine.succeed("mkdir /tmp/restored-state; tar -xzf /var/backups/hydra/$(date -u +%F)/state.tar.gz -C /tmp/restored-state; test -d /tmp/restored-state/hydra")
    machine.fail("ssh -n -o BatchMode=yes -i /run/backup-key -o UserKnownHostsFile=/run/backup-known-hosts hydra-backup@receiver 'touch /tmp/escape'")
    receiver.succeed("test ! -e /tmp/escape")
  '';
}
