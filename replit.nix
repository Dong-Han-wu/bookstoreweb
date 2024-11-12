{pkgs}: {
  deps = [
    pkgs.openssh
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
  ];
}
