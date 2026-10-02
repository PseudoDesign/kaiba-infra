{ pkgs, forgejoPackage }:
pkgs.testers.runNixOSTest {
  name = "kaiba-forgejo";
  requiredFeatures.kvm = false;
  nodes.machine =
    { ... }:
    {
      imports = [ ../modules/forgejo.nix ];
      services.kaibaForgejo = {
        enable = true;
        package = forgejoPackage;
        enableACME = false;
        domain = "git.test";
        docsDomain = "docs.test";
      };
      virtualisation.memorySize = 1536;
      environment.systemPackages = [
        pkgs.curl
        pkgs.git
        pkgs.python3
      ];
    };
  testScript = ''
    import json
    start_all()
    machine.wait_for_unit("forgejo.service")
    machine.wait_for_unit("nginx.service")
    machine.wait_for_open_port(3010)
    machine.succeed("curl -fsS -H 'Host: git.test' http://127.0.0.1/api/v1/version")
    machine.succeed("sudo -u postgres psql -d forgejo -c 'SELECT 1'")
    machine.succeed("test $(cat /sys/fs/cgroup/system.slice/forgejo.service/memory.max) = 536870912")
    machine.succeed("test $(cat /sys/fs/cgroup/system.slice/forgejo.service/memory.swap.max) = 0")
    machine.succeed("ss -ltn | grep '127.0.0.1:3010'")
    machine.fail("ss -ltn | grep ':2222 '")
    machine.succeed("grep -q 'DISABLE_REGISTRATION = true' /var/lib/forgejo/custom/conf/app.ini")
    machine.succeed("grep -q 'ENABLED = false' /var/lib/forgejo/custom/conf/app.ini")
    machine.succeed("sudo -u forgejo ${forgejoPackage}/bin/forgejo --config /var/lib/forgejo/custom/conf/app.ini admin user create --username fixture --password FixturePassword123456 --email fixture@example.test --admin --must-change-password=false")
    token = json.loads(machine.succeed("curl -fsS -u fixture:FixturePassword123456 -H 'Content-Type: application/json' -d '{\"name\":\"fixture\",\"scopes\":[\"all\"]}' http://127.0.0.1:3010/api/v1/users/fixture/tokens"))["sha1"]
    machine.succeed(f"curl -fsS -H 'Authorization: token {token}' -H 'Content-Type: application/json' -d '{{\"name\":\"fixture\",\"private\":true}}' http://127.0.0.1:3010/api/v1/user/repos")
    machine.succeed("mkdir /tmp/source && cd /tmp/source && git init && git config user.email fixture@example.test && git config user.name Fixture && echo evidence > README && git add README && git commit -m fixture")
    machine.succeed(f"cd /tmp/source && git push http://fixture:{token}@127.0.0.1:3010/fixture/fixture.git HEAD:main")
    machine.fail("GIT_TERMINAL_PROMPT=0 git ls-remote http://127.0.0.1:3010/fixture/fixture.git")
    before = machine.succeed("cd /tmp/source && git rev-parse HEAD").strip()
    machine.succeed("systemctl stop forgejo && sudo -u postgres pg_dump -Fc forgejo > /tmp/forgejo.dump && tar -czf /tmp/state.tar.gz -C /var/lib forgejo && systemctl start forgejo")
    machine.succeed("sudo -u postgres createdb forgejo_restore && sudo -u postgres pg_restore -d forgejo_restore /tmp/forgejo.dump")
    machine.succeed("sudo -u postgres psql -d forgejo_restore -tAc \"SELECT name FROM repository WHERE name = 'fixture'\" | grep -x fixture")
    machine.succeed("mkdir /tmp/restore && tar -xzf /tmp/state.tar.gz -C /tmp/restore")
    restored = machine.succeed("git --git-dir=/tmp/restore/forgejo/repositories/fixture/fixture.git rev-parse refs/heads/main").strip()
    assert restored == before
    machine.wait_for_open_port(3010)
    machine.succeed(f"git ls-remote http://fixture:{token}@127.0.0.1:3010/fixture/fixture.git")
  '';
}
