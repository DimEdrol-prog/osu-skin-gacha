{
  description = "Skin Gacha";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-26.05";
    uv2nix.url = "github:pyproject-nix/uv2nix";
    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

        uvOverlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };

        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages {
            python = pkgs.python3;
          }).overrideScope
            (
              pkgs.lib.composeManyExtensions [
                pyproject-build-systems.overlays.default
                uvOverlay
              ]
            );
        virtualenv = pythonSet.mkVirtualEnv "dev-env" workspace.deps.all;
      in
      {
        /*
          default = pkgs.stdenv.mkDerivation {
            pname = "skin-gacha";
            version = "0.5.0";
            src = ./.;
            pyproject = true;
            dontBuild = true;
            dontConfigure = true;
            dontUseCmakeConfigure = true;
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
              makeWrapper ${virtualenv}/bin/python $out/bin/skin-gacha \
              --add-flags "$src/main.py" \
              --prefix PYTHONPATH : "${pkgs.python3Packages.tkinter}/${pkgs.python3.sitePackages}:$src" \
              --set TCL_LIBRARY "${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}" \
              --set TK_LIBRARY "${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
            '';
          };
        */
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "skin-gacha";
          version = "0.5.0";
          src = ./.;
          dontBuild = true;
          dontConfigure = true;
          dontUseCmakeConfigure = true;
          nativeBuildInputs = [ pkgs.makeWrapper ];
          makeWrapperArgs = [
            "--set TCL_LIBRARY ${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}"
            "--set TK_LIBRARY ${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
          ];
          installPhase = ''
            mkdir -p $out/bin
            makeWrapper ${virtualenv}/bin/python $out/bin/skin-gacha \
            --add-flags "$src/main.py" \
            --prefix PYTHONPATH : "${pkgs.python3Packages.tkinter}/${pkgs.python3.sitePackages}:$src" \
            --set TCL_LIBRARY "${pkgs.tcl}/lib/tcl${pkgs.lib.versions.majorMinor pkgs.tcl.version}" \
            --set TK_LIBRARY "${pkgs.tk}/lib/tk${pkgs.lib.versions.majorMinor pkgs.tk.version}"
          '';
        };
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.gnumake
            virtualenv
            pkgs.uv
          ];
        };
      }
    );
}
