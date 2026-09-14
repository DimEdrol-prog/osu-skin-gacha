{
  description = "Skin Gacha";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
  };

  outputs =
    { self, nixpkgs, ... }@inputs:
    let
      supportedSystems = [
        "x86_64-linux"
      ];
      forEachSupportedSystem =
        f:
        nixpkgs.lib.genAttrs supportedSystems (
          system:
          f {
            pkgs = import nixpkgs { inherit system; };
          }
        );
    in
    {
      devShells = forEachSupportedSystem (
        { pkgs }: {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              tk
              tcl
              stdenv.cc.cc.lib
              zlib
              gnumake
            ];

            shellHook = ''
              export TCL_LIBRARY="${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}"
              export TK_LIBRARY="${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
              python -m venv .venv
              source .venv/bin/activate
            '';
          };
        }
      );

      packages = forEachSupportedSystem (
        { pkgs }: {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "skin-gacha";
            version = "1.0.0";
            src = ./.;
            pyproject = true;
            build-system = with pkgs.python3Packages; [
              setuptools
            ];
            makeWrapperArgs = [
              "--set TCL_LIBRARY ${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}"
              "--set TK_LIBRARY ${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
            ];
          };
        }
      );
    };
}
