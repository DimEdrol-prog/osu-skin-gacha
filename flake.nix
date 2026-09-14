{
  description = "Skin Gacha";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
    uv2nix.url = "github:pyproject-nix/uv2nix";
    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs";
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      ...
    }:
    let
      supportedSystems = [
        "x86_64-linux"
      ];
      forEachSupportedSystem =
        f:
        nixpkgs.lib.genAttrs supportedSystems (
          system:
          let
            pkgs = import nixpkgs { inherit system; };
            workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
            overlay = workspace.mkPyprojectOverlay {
              sourcePreference = "wheel";
            };
            pythonSet =
              (pkgs.callPackage pyproject-nix.build.packages {
                python = pkgs.python3;
              }).overrideScope
                (
                  pkgs.lib.composeManyExtensions [
                    pyproject-build-systems.overlays.default
                    overlay
                  ]
                );
            venv = pythonSet.mkVirtualEnv "skin-gacha-env" workspace.deps.default;
          in
          f { inherit pkgs venv; }
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
              uv
              venv
            ];

            shellHook = ''
              unset PYTHONPATH
              export TCL_LIBRARY="${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}"
              export TK_LIBRARY="${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
              python -m venv .venv
              source .venv/bin/activate
            '';
          };
        }
      );

      packages = forEachSupportedSystem (
        { pkgs, venv }: {
          default = pkgs.stdenv.mkDerivation {
            pname = "skin-gacha";
            version = "1.0.0";
            src = ./.;
            pyproject = true;
            dontBuild = true;
            build-system = with pkgs.python3Packages; [
              setuptools
            ];
            dependencies = with pkgs.python3Packages; [
              tkinter
              customtkinter
              requests
              pillow
              beautifulsoup4
              pygame-ce
            ];
            nativeBuildInputs = [ pkgs.makeWrapper ];
            makeWrapperArgs = [
              "--set TCL_LIBRARY ${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}"
              "--set TK_LIBRARY ${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
            ];
            installPhase = ''
              mkdir -p $out/bin
              makeWrapper ${venv}/bin/python $out/bin/skin-gacha \
              --add-flags "$src/main.py" \
              --prefix PYTHONPATH : "${pkgs.python3Packages.tkinter}/${pkgs.python3.sitePackages}:$src" \
              --set TCL_LIBRARY "${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}" \
              --set TK_LIBRARY "${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
            '';
          };
        }
      );
    };
}
