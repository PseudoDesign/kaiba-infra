{ pkgs, hydra }:
pkgs.runCommand "kaiba-hydra-github-plugin" {
  nativeBuildInputs = [ pkgs.patch ];
} ''
  mkdir -p "$out/Hydra/Plugin"
  cp ${hydra}/libexec/hydra/lib/Hydra/Plugin/GithubStatus.pm "$out/Hydra/Plugin/"
  chmod u+w "$out/Hydra/Plugin/GithubStatus.pm"
  cd "$out/Hydra/Plugin"
  patch --fuzz=0 -p1 < ${../patches/hydra-github-status.patch}
''
