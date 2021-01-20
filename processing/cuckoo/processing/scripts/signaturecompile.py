#!/usr/bin/env python3
# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import argparse
import os.path
import sys

import hyperscan
from cuckoo.processing.signatures.pattern import (
    LoadedSignatures, _PATTERN_HYPERSCAN_FLAGS, _LoadedPatternTypes
)

def print_parent_sigs(pattern_id, loadedsigs):
    for sigid in loadedsigs.pattern_id_sigids[pattern_id]:
        sig = loadedsigs.sigid_siginfo[sigid]

        print(f"Signature: {sig.name}")

if __name__ == "__main__":
     argsp = argparse.ArgumentParser()
     argsp.add_argument("path", help="Path to Cuckoo 3 pattern signature file")
     args = argsp.parse_args()

     if not os.path.exists(args.path):
         sys.exit(f"Path does not exist.")

     loadedsigs = LoadedSignatures()
     loadedsigs.load_from_file(args.path)

     for pattern in loadedsigs.pattern_id_pattern.values():
         if pattern.TYPE != _LoadedPatternTypes.REGEX:
             continue

         hsdb = hyperscan.Database()
         try:
             hsdb.compile(
                 expressions=(pattern.regex.encode(),),
                 ids=(pattern.id,),
                 elements=1,
                 flags=(_PATTERN_HYPERSCAN_FLAGS,)
             )
         except hyperscan.error as e:
             print(f"File: {args.path}")
             print(f"Regex {pattern.regex!r} fails to compile. Error: {e}")
             print("Parent signatures:")
             print_parent_sigs(pattern.id, loadedsigs)
