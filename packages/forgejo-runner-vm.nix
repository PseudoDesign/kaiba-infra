{
  nixpkgs,
  system,
  runnerPackage,
}:
let
  guest = nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [
      (nixpkgs + "/nixos/modules/virtualisation/qemu-vm.nix")
      (
        { pkgs, lib, ... }:
        {
          system.stateVersion = "26.05";
          networking.hostName = "kaiba-ci";
          services.openssh.enable = false;
          nix.settings.experimental-features = [
            "nix-command"
            "flakes"
          ];
          nix.settings.trusted-users = [ "root" ];
          virtualisation = {
            memorySize = 4096;
            cores = 2;
            diskSize = 32768;
            graphics = false;
            mountHostNixStore = false;
            useNixStoreImage = true;
            sharedDirectories = lib.mkForce { };
            qemu.options = [
              "-enable-kvm"
              "-cpu host"
              # The sole host share contains this VM's ephemeral runner config.
              # Never share a host Nix store, socket, home or administrator token.
              "-virtfs local,path=$KAIBA_RUNNER_BOOTSTRAP,security_model=none,mount_tag=bootstrap,readonly=on"
            ];
          };
          fileSystems."/run/forgejo-bootstrap" = {
            device = "bootstrap";
            fsType = "9p";
            options = [
              "trans=virtio"
              "version=9p2000.L"
              "ro"
              "msize=65536"
            ];
          };
          environment.systemPackages = [
            pkgs.nix
            pkgs.git
            pkgs.nodejs_22
            pkgs.python3
            pkgs.python3Packages.virtualenv
            pkgs.curl
            pkgs.jq
            pkgs.gnutar
            pkgs.gzip
            pkgs.unzip
            pkgs.coreutils
            pkgs.findutils
            pkgs.gnugrep
            pkgs.gnused
            pkgs.bash
            pkgs.cacert
            runnerPackage
          ];
          systemd.services.forgejo-runner = {
            wantedBy = [ "multi-user.target" ];
            wants = [ "network-online.target" ];
            after = [ "network-online.target" ];
            requires = [ "run-forgejo\\x2dbootstrap.mount" ];
            path = [
              pkgs.nix
              pkgs.git
              pkgs.nodejs_22
              pkgs.python3
              pkgs.curl
              pkgs.jq
              pkgs.bash
              pkgs.coreutils
              pkgs.gnutar
              pkgs.gzip
              pkgs.unzip
            ];
            serviceConfig = {
              WorkingDirectory = "/var/lib/forgejo-runner";
              StateDirectory = "forgejo-runner";
              UMask = "0077";
              ExecStart = "${runnerPackage}/bin/forgejo-runner daemon --config /run/forgejo-bootstrap/runner.yaml";
              Restart = "no";
              RuntimeMaxSec = "6h";
              ExecStopPost = "${pkgs.systemd}/bin/systemctl --no-block poweroff";
            };
          };
        }
      )
    ];
  };
in
guest.config.system.build.vm
