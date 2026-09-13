{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (
      ps: with ps; [
        tkinter
        customtkinter
        requests
        pillow
        pyinstaller
        beautifulsoup4
      ]
    ))
    python3
    python3Packages.tkinter
    tk
    tcl
    stdenv.cc.cc.lib
    zlib
  ];
  shellHook = ''
    export TCL_LIBRARY="${pkgs.tcl}/lib/tcl8.6"
    export TK_LIBRARY="${pkgs.tk}/lib/tk8.6"
    python -m venv .venv                                                                                
    source .venv/bin/activate
  '';
}
