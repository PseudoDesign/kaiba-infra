{ pkgs }:
let
  # Public test fixture only. Never use this key for an actual backup.
  recoveryKey = ./backup-fixtures/TEST-ONLY-recovery.agekey;
  recipient = "age1dt8t9w25qavu4xul2gm2upestdt02we6jfk0j4m5glt6p6mnw9cq3n4w9e";
in pkgs.testers.runNixOSTest {
  name = "kaiba-human-access-backup";
  requiredFeatures.kvm = false;
  nodes.machine = { lib, ... }: {
    imports = [ ../modules/human-access-backup.nix ];
    services.postgresql = { enable = true; ensureDatabases = [ "keycloak" ]; };
    services.kaibaHumanAccessBackup = {
      enable = true;
      recipients = [ recipient ];
      receiverHost = "receiver";
      keyFile = "/run/backup-key";
      knownHostsFile = "/run/backup-known-hosts";
    };
    systemd.timers.kaiba-human-access-backup.wantedBy = lib.mkForce [];
    # Model the CA's actual DynamicUser/StateDirectory layout. Issuance policy
    # and real key handling have their own step-ca integration test.
    systemd.services.kaiba-ssh-ca = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        DynamicUser = true;
        StateDirectory = "kaiba-ssh-ca-db";
        StateDirectoryMode = "0700";
        ExecStart = "${pkgs.coreutils}/bin/sleep infinity";
      };
    };
    environment.systemPackages = [ pkgs.openssh pkgs.rsync pkgs.python3 pkgs.util-linux ];
    virtualisation.memorySize = 1024;
  };
  nodes.receiver = {
    imports = [ ../modules/human-access-backup-receiver.nix ];
    services.kaibaHumanAccessBackupReceiver.enable = true;
    networking.firewall.allowedTCPPorts = [ 22 ];
    virtualisation.memorySize = 512;
  };
  testScript = ''
    import pathlib
    import subprocess
    import tarfile
    import tempfile

    start_all()
    machine.wait_for_unit("postgresql.target")
    machine.wait_for_unit("kaiba-ssh-ca.service")
    receiver.wait_for_unit("sshd.service")
    machine.succeed("install -d -m 700 /var/lib/kaiba-human-identity /var/lib/kaiba-ssh-ca")
    machine.succeed("printf 'test-only-issuer-state' > /var/lib/kaiba-human-identity/owner.json; printf 'test-only-encrypted-ca-key' > /var/lib/kaiba-ssh-ca/ssh_user_ca_key; printf 'test-only-trust' > /var/lib/kaiba-ssh-ca/initialized; printf 'test-only-replay-record' > /var/lib/kaiba-ssh-ca-db/state")
    machine.succeed("runuser -u postgres -- psql -d keycloak -c \"CREATE TABLE identity_fixture (subject text PRIMARY KEY, enrolled boolean NOT NULL); INSERT INTO identity_fixture VALUES ('stable-subject', false);\"")
    machine.succeed("ssh-keygen -q -t ed25519 -N \"\" -f /run/backup-key; ssh-keyscan receiver > /run/backup-known-hosts")
    public_key = machine.succeed("cat /run/backup-key.pub").strip()
    receiver.succeed(f"printf '%s\\n' '{public_key}' > /var/lib/kaiba-human-backup-receiver/authorized_keys; chmod 644 /var/lib/kaiba-human-backup-receiver/authorized_keys")
    # An enrollment change must finish before either state is snapshotted.
    # Waiting for that lock must not interrupt the running CA.
    machine.succeed("systemd-run --unit=enrollment-lock-fixture --property=UMask=0077 ${pkgs.util-linux}/bin/flock --exclusive /var/lib/kaiba-human-identity/owner-enrollment.lock ${pkgs.runtimeShell} -c '${pkgs.coreutils}/bin/touch /run/enrollment-lock-held; exec ${pkgs.coreutils}/bin/sleep infinity'")
    machine.wait_for_file("/run/enrollment-lock-held", timeout=30)
    before = machine.succeed("systemctl show kaiba-ssh-ca -p InvocationID --value").strip()
    machine.succeed("systemctl start --no-block kaiba-human-access-backup")
    machine.wait_until_succeeds("lslocks -nr -o MODE,PATH | grep 'WRITE[*].*owner-enrollment.lock'", timeout=30)
    machine.succeed("systemctl is-active --quiet kaiba-ssh-ca; test -z \"$(find /var/backups/kaiba-human-access -name keycloak.dump -o -name state.tar.gz -o -name '*.tar.age')\"")
    assert before == machine.succeed("systemctl show kaiba-ssh-ca -p InvocationID --value").strip()
    machine.succeed("runuser -u postgres -- psql -d keycloak -c 'UPDATE identity_fixture SET enrolled = true'; printf test-only-issuer-state > /var/lib/kaiba-human-identity/owner.json")
    machine.succeed("systemctl stop enrollment-lock-fixture; systemctl start kaiba-human-access-backup")
    assert machine.succeed("stat -c '%U %a' /var/lib/kaiba-human-identity /var/lib/kaiba-human-identity/owner-enrollment.lock").splitlines() == ["root 700", "root 600"]
    machine.succeed("systemctl is-active --quiet kaiba-ssh-ca")
    name = receiver.succeed("ls /var/backups/kaiba-human-access").strip()
    assert name.endswith(".tar.age") and chr(10) not in name
    receiver.succeed(f"head -c 22 /var/backups/kaiba-human-access/{name} | grep -F age-encryption.org/v1")
    receiver.fail("grep -arF test-only-encrypted-ca-key /var/backups/kaiba-human-access")
    machine.succeed("test -z \"$(find /var/backups/kaiba-human-access -maxdepth 1 -type d -name '.staging-*' -print)\"")

    # Decrypt on the isolated test driver, representing the owner's recovery
    # machine. The sender and receiver are never given the recovery key.
    receiver.copy_from_machine(f"/var/backups/kaiba-human-access/{name}", "encrypted-backup")
    ciphertext = receiver.out_dir / "encrypted-backup" / name
    with tempfile.TemporaryDirectory() as directory:
        recovery = pathlib.Path(directory)
        archive = recovery / "identity.tar"
        subprocess.run(["${pkgs.age}/bin/age", "--decrypt", "-i", "${recoveryKey}", "-o", str(archive), str(ciphertext)], check=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(recovery, filter="data")
        subprocess.run(["${pkgs.coreutils}/bin/sha256sum", "-c", "SHA256SUMS"], cwd=recovery, check=True)
        state = recovery / "state"
        state.mkdir()
        with tarfile.open(recovery / "state.tar.gz") as bundle:
            bundle.extractall(state, filter="data")
        assert (state / "kaiba-human-identity/owner.json").read_text() == "test-only-issuer-state"
        assert (state / "kaiba-ssh-ca/ssh_user_ca_key").read_text() == "test-only-encrypted-ca-key"
        assert (state / "kaiba-ssh-ca-db/state").read_text() == "test-only-replay-record"
        machine.copy_from_host(str(recovery / "keycloak.dump"), "/run/restored-keycloak.dump")
        machine.succeed("runuser -u postgres -- createdb keycloak_restore")
        machine.succeed("cat /run/restored-keycloak.dump | runuser -u postgres -- pg_restore --no-owner -d keycloak_restore")
        assert machine.succeed("runuser -u postgres -- psql -At -d keycloak_restore -c 'SELECT subject || chr(58) || enrolled FROM identity_fixture'").strip() == "stable-subject:true"

    # Seed older ciphertext snapshots, then run the production retention and
    # transfer logic. Only the newest seven encrypted files remain on both ends.
    for index in range(1, 10):
        machine.succeed(f"cp /var/backups/kaiba-human-access/{name} /var/backups/kaiba-human-access/200001{index:02d}T000000Z.tar.age")
    machine.succeed("systemctl start kaiba-human-access-backup")
    local = machine.succeed("ls /var/backups/kaiba-human-access").splitlines()
    remote = receiver.succeed("ls /var/backups/kaiba-human-access").splitlines()
    assert len(local) == 7 and local == remote
    assert all(path.endswith(".tar.age") for path in remote)

    # A snapshot error must restart a previously active CA and remove plaintext.
    before = machine.succeed("systemctl show kaiba-ssh-ca -p InvocationID --value").strip()
    machine.succeed("runuser -u postgres -- dropdb keycloak")
    machine.fail("systemctl start kaiba-human-access-backup")
    machine.succeed("systemctl is-active --quiet kaiba-ssh-ca")
    assert before != machine.succeed("systemctl show kaiba-ssh-ca -p InvocationID --value").strip()
    machine.succeed("test -z \"$(find /var/backups/kaiba-human-access -maxdepth 1 -type d -name '.staging-*' -print)\"")
    assert receiver.succeed("ls /var/backups/kaiba-human-access").splitlines() == remote

    ssh = "ssh -n -i /run/backup-key -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/backup-known-hosts"
    machine.fail(ssh + " human-access-backup@receiver 'touch /tmp/escape'")
    receiver.succeed("test ! -e /tmp/escape")
    machine.succeed("printf test-only-probe > /run/probe")
    machine.fail(f"rsync -e '{ssh}' /run/probe human-access-backup@receiver:../../tmp/escape")
    machine.fail(f"rsync -e '{ssh}' human-access-backup@receiver:{name} /run/forbidden-download")
    receiver.succeed("test ! -e /tmp/escape")
    machine.succeed("test ! -e /run/forbidden-download")
  '';
}
