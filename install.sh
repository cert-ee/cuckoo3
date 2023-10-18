#!/bin/bash

pip install -U wheel
pip install -U requests
# TMP solution until new versions of sflock etc are released to PyPI
pip install -U git+https://github.com/cert-ee/peepdf
pip install -U git+https://github.com/cert-ee/sflock
pip install -U git+https://github.com/cert-ee/roach
pip install -U git+https://github.com/cert-ee/httpreplay

declare -a pkglist=("./common" "./processing" "./machineries" "./web" "./node" "./core")

for pkg in ${pkglist[@]}
do
  if ! [[ -d "$pkg" ]]; then
    echo "Missing package: $pkg"
    exit 1
  fi

  pip install -e "$pkg"
  if [ $? -ne 0 ]; then
      echo "Install of $pkg failed"
      exit 1
  fi
done
