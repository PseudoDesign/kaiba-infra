{
  description = "Kaiba CI policy and Hydra infrastructure";

  # Match the current host repository's Raspberry Pi nixpkgs pin.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/ee48b147c18c7de1e6ec97dc74792be42724bed1";

  outputs = { self, nixpkgs }: let
    systems = [ "aarch64-linux" "x86_64-linux" ];
    forSystems = nixpkgs.lib.genAttrs systems;
  in {
    checks = forSystems (system: let
      pkgs = import nixpkgs { inherit system; };
    in {
      selector = pkgs.runCommand "kaiba-infra-tests" {
        nativeBuildInputs = [ pkgs.python3 ];
        src = nixpkgs.lib.fileset.toSource {
          root = ./.;
          fileset = nixpkgs.lib.fileset.unions [ ./ci ./client ./identity ./tests ./examples ];
        };
      } ''
        cp -r "$src" source
        chmod -R u+w source
        cd source
        export PYTHONDONTWRITEBYTECODE=1
        python3 -m unittest discover -s tests -v
        mkdir -p "$out"
        echo passed > "$out/result"
      '';
    });

    hydraJobs.aarch64-linux = self.checks.aarch64-linux;

    packages = forSystems (system: let
      pkgs = import nixpkgs { inherit system; };
    in {
      kvm-smoke-test = pkgs.testers.runNixOSTest {
        name = "kaiba-kvm-smoke";
        nodes.machine = {
          virtualisation.memorySize = 512;
          virtualisation.cores = 1;
        };
        testScript = ''
          start_all()
          machine.wait_for_unit("multi-user.target")
          assert "enabled" in machine.send_monitor_command("info kvm"), "KVM is not active"
          machine.succeed("test $(uname -m) = ${if system == "aarch64-linux" then "aarch64" else "x86_64"}")
        '';
      };
      hydra-integration-test = import ./tests/hydra.nix { inherit pkgs; };
      hydra-notifier-test = import ./tests/hydra-notifier.nix { inherit pkgs; };
      kaiba-login = pkgs.callPackage ./packages/kaiba-login.nix { };
      ssh-ca-init = import ./identity/ssh-ca-init-package.nix { inherit pkgs; };
      ssh-user-ca = import ./identity/ssh-ca-package.nix { inherit pkgs; };
      ssh-user-ca-test = import ./tests/ssh-user-ca.nix { inherit pkgs; };
      human-identity-test = import ./tests/human-identity.nix { inherit pkgs; };
      ssh-human-access-test = import ./tests/ssh-human-access.nix { inherit pkgs; };
      human-access-backup-test = import ./tests/human-access-backup.nix { inherit pkgs; };
    });

    nixosModules.hydra = import ./modules/hydra.nix;
    nixosModules.hydra-proxy = import ./modules/hydra-proxy.nix;
    nixosModules.hydra-backup-receiver = import ./modules/hydra-backup-receiver.nix;
    nixosModules.human-identity = import ./modules/human-identity.nix;
    nixosModules.ssh-user-ca = import ./modules/ssh-user-ca.nix;
    nixosModules.ssh-human-access = import ./modules/ssh-human-access.nix;
    nixosModules.human-access-backup = import ./modules/human-access-backup.nix;
    nixosModules.human-access-backup-receiver = import ./modules/human-access-backup-receiver.nix;
  };
}
