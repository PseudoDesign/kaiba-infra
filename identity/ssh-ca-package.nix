{ pkgs }:
# Applies to pinned step-ca 0.29.0, authority/provisioner/sign_ssh_options.go.
# Keep this local policy until upstream supports an absolute issuance horizon.
pkgs.step-ca.overrideAttrs (old: {
  patches = (old.patches or []) ++ [ ./ssh-ca-expiry.patch ];
})
