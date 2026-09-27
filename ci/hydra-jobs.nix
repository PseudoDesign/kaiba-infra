# The application supplies its own checks and nixpkgs library; importing this
# policy must not change the application's dependencies or derivation paths.
{ checks, lib }:
let
  inventory = builtins.fromJSON (builtins.readFile ./provisioning-arm64.json);
  prefix = "checks.aarch64-linux.";
  job = path:
    let
      drv = lib.attrByPath (lib.splitString "." path)
        (throw "Hydra inventory attribute is missing: ${path}") { inherit checks; };
    in {
      name = lib.removePrefix prefix path;
      value = if lib.isDerivation drv && drv.system == "aarch64-linux"
        then drv else throw "Hydra job must be an aarch64-linux derivation: ${path}";
    };
in
assert inventory.jobs != [ ];
assert builtins.length inventory.jobs == builtins.length (lib.unique inventory.jobs);
assert lib.all (path: lib.hasPrefix prefix path && builtins.length (lib.splitString "." path) == 3) inventory.jobs;
{ aarch64-linux = lib.listToAttrs (map job inventory.jobs); }
