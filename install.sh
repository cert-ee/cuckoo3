#!/bin/bash

# TMP solution to install latest sflock dev changes before it is released as a package.
tmpdir="$(mktemp -d)/sflockmaster.zip"
wget -O "$tmpdir" "https://github.com/Evert0x/sflock/archive/master.zip"
if [ $? -ne 0 ]; then
    echo "Failed to download sflock master from Github"
fi

pip install "$tmpdir"

# TMP solution to install latest roach dev changes before it is released as a package.
tmpdir="$(mktemp -d)/roach.zip"
wget -O "$tmpdir" "https://github.com/Evert0x/roach/archive/master.zip"
if [ $? -ne 0 ]; then
    echo "Failed to download roach master from Github"
fi
pip install "$tmpdir"

pip install -e ./common
pip install -e ./processing
pip install -e ./machineries
pip install -e ./web
pip install -e ./node
pip install -e ./core
