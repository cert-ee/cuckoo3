#!/bin/bash

if ! [[ -d "../deps" ]];
then
  echo "../deps does not exist"
  exit 1
fi


# TMP solution until new versions of sflock etc are released to PyPI
declare -a deplist=("../deps/sflock" "../deps/roach" "../deps/httpreplay")

for dep in ${deplist[@]}
do
  if ! [[ -d "$dep" ]]; then
    echo "Missing dependecy: $dep"
    exit 1
  fi

  pip install -e "$dep"
  if [ $? -ne 0 ]; then
      echo "Install of $dep failed"
      exit
  fi
done

pip install -U requests

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