{ pkgs, hydra ? pkgs.hydra }:
let
  plugin = import ../modules/hydra-github-plugin.nix { inherit pkgs hydra; };
in pkgs.runCommand "kaiba-hydra-notifier-tests" {
  nativeBuildInputs = [ pkgs.perl ];
  PERL5LIB = "${hydra}/libexec/hydra/lib:${hydra.perlDeps}/lib/perl5/site_perl";
  PERL5OPT = "-I${plugin}";
} ''
  perl ${./hydra-github-status.t}
  mkdir -p "$out"
  echo passed > "$out/result"
''
