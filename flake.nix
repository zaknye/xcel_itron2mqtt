{
  description = "Development environment for xcel_itron2mqtt";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python3.withPackages (
          ps: with ps; [
            async-timeout
            certifi
            charset-normalizer
            idna
            ifaddr
            requests
            urllib3
            zeroconf
            pyyaml
            paho-mqtt
            tenacity
          ]
        );
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.python3Packages.pip
            # client for debugging mqtt
            pkgs.mosquitto
            pkgs.mqttui
          ];

          shellHook = ''
            echo "Python development environment loaded"
            echo "Python version: $(python --version)"
            echo "WARNING: Changes to xcel_itron2mqtt/requirements.txt also need to be updated here"
          '';
        };
      }
    );
}
