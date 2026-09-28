{ pkgs }:
let
  ciFixture = pkgs.writeText "hydra-ci-fixture.py" ''
    import sys
    sys.path.insert(0, "${../ci}")
    import hydra_ci_runs as ci

    class GitHub:
        def __init__(self, token):
            assert token == "test_only_github_token"

        def get(self, path):
            if path.startswith("/actions/workflows/"):
                return {"workflow_runs": [{"id": 42, "run_attempt": 2, "workflow_id": 123,
                    "path": ci.WORKFLOW, "repository": {"full_name": ci.REPOSITORY},
                    "head_sha": "a" * 40, "event": "workflow_dispatch", "status": "in_progress",
                    "conclusion": None}]}
            assert path.startswith("/actions/runs/42/attempts/2/jobs?")
            return {"jobs": [{"id": 99, "run_id": 42, "run_attempt": 2, "status": "in_progress",
                "conclusion": None, "name": "ARM64 checks on Hydra (" + "a" * 40 + ")"}]}

    ci.GitHub = GitHub
    raise SystemExit(ci.main(["--workflow-id", "123", "--username", "adam"]))
  '';
  mockNix = pkgs.writeShellScriptBin "nix-store" ''
    echo /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-fixture.drv
    echo /nix/store/cccccccccccccccccccccccccccccccc-kernel
  '';
  mockCachix = pkgs.writeShellScriptBin "cachix" ''
    test "$CACHIX_AUTH_TOKEN" = test_only_cache_token
    ${pkgs.coreutils}/bin/cat > /var/lib/kaiba-hydra-publish/pushed-paths
    test ! -e /var/lib/kaiba-hydra-publish/fail
  '';
in pkgs.testers.runNixOSTest {
  name = "kaiba-hydra-integration";
  # Also runnable under emulation on development machines without KVM.
  requiredFeatures.kvm = false;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules/hydra.nix ];
    services.kaibaHydra = {
      enable = true;
      publicURL = "http://localhost:3000";
      proxyAddress = "192.0.2.1";
      github = { enable = true; tokenFile = "/run/github-token"; };
      cachePublish = { enable = true; tokenFile = "/run/cachix-token"; };
      ciRuns = { enable = true; workflowId = 123; passwordFile = "/run/hydra-password"; };
      backup = {
        enable = true;
        host = "receiver";
        keyFile = "/run/backup-key";
        knownHostsFile = "/run/backup-known-hosts";
      };
    };
    systemd.timers.kaiba-hydra-backup.wantedBy = lib.mkForce [ ];
    systemd.timers.kaiba-hydra-publish.wantedBy = lib.mkForce [ ];
    systemd.timers.kaiba-hydra-ci-runs.wantedBy = lib.mkForce [ ];
    systemd.services.kaiba-hydra-ci-runs.serviceConfig.ExecStart =
      lib.mkForce "${pkgs.python3}/bin/python3 ${ciFixture}";
    systemd.services.kaiba-hydra-publish.path = lib.mkForce [ mockNix mockCachix ];
    systemd.tmpfiles.rules = [
      "f /run/github-token 0600 root root - test_only_github_token"
      "f /run/cachix-token 0600 root root - test_only_cache_token"
    ];
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
    machine.wait_for_unit("hydra-notify.service")
    machine.succeed("test $(stat -c %a /run/kaiba-hydra-notify) = 700; test $(stat -c %a /run/kaiba-hydra-notify/hydra.conf) = 600")
    machine.fail("runuser -u hydra-www -- cat /run/kaiba-hydra-notify/hydra.conf")
    machine.fail("grep -q test_only_github_token /var/lib/hydra/hydra.conf")
    machine.succeed("su - hydra -c 'hydra-create-user adam --password test-only-password --role admin'")
    machine.succeed("install -m 600 /dev/null /run/hydra-password; printf %s test-only-password > /run/hydra-password")
    machine.succeed("cp -r ${../ci} /tmp/ci")
    machine.succeed("printf '%s' '{\"build\":999,\"project\":\"kaiba-provisioning\",\"jobset\":\"main\",\"job\":\"aarch64-linux.enrollment-storage-vm\",\"system\":\"aarch64-linux\",\"finished\":true,\"buildStatus\":0,\"drvPath\":\"/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-fixture.drv\",\"outputs\":[{\"path\":\"/nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-fixture\"}]}' > /tmp/publish.json")
    machine.succeed("runuser -u hydra-queue-runner -- env HYDRA_JSON=/tmp/publish.json python3 /tmp/ci/hydra_publish.py enqueue")
    machine.succeed("touch /var/lib/kaiba-hydra-publish/fail")
    machine.fail("systemctl start kaiba-hydra-publish")
    machine.succeed("test -f /var/lib/kaiba-hydra-publish/999.json; rm /var/lib/kaiba-hydra-publish/fail")
    machine.succeed("systemctl start kaiba-hydra-publish; test ! -f /var/lib/kaiba-hydra-publish/999.json")
    machine.succeed("grep -Fx /nix/store/cccccccccccccccccccccccccccccccc-kernel /var/lib/kaiba-hydra-publish/pushed-paths")
    command = "python3 /tmp/ci/setup_hydra.py --url http://localhost:3000 --apply --password-file /run/hydra-password"
    machine.succeed(command)
    machine.succeed(command)
    machine.succeed("systemctl start kaiba-hydra-ci-runs")
    machine.succeed("curl -fsS -H 'Accept: application/json' http://localhost:3000/jobset/kaiba-provisioning/ci-42-2 | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x[\"flake\"] == \"github:PseudoDesign/kaiba-provisioning/\" + \"a\"*40; assert x[\"enabled\"] in (0,2); assert x[\"keepnr\"] == 0'")
    machine.succeed("runuser -u postgres -- psql -d hydra -c \"update jobsets set enabled=0 where name='ci-42-2'\"")
    machine.succeed("systemctl start kaiba-hydra-ci-runs")
    assert machine.succeed("runuser -u postgres -- psql -At -d hydra -c \"select enabled from jobsets where name='ci-42-2'\"").strip() == "0"
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
    assert machine.succeed("runuser -u postgres -- psql -At -d hydra_restore -c \"select enabled from jobsets where project='kaiba-provisioning' and name='main'\"").strip() == "0"
    machine.succeed("mkdir /tmp/restored-state; tar -xzf /var/backups/hydra/$(date -u +%F)/state.tar.gz -C /tmp/restored-state; test -d /tmp/restored-state/hydra")
    machine.fail("ssh -n -o BatchMode=yes -i /run/backup-key -o UserKnownHostsFile=/run/backup-known-hosts hydra-backup@receiver 'touch /tmp/escape'")
    receiver.succeed("test ! -e /tmp/escape")
  '';
}
