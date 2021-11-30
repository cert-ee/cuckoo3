#!/usr/bin/env python
# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import sys

try:
    from cuckoo.common.migrate import CWDFileMigrator
except ImportError:
    sys.exit(
        "Cuckoo must first be installed in dev mode before this "
        "script can run"
    )

if __name__ == "__main__":
    if len(sys.argv) > 1:
        comment = sys.argv[1].strip()
    else:
        comment = ""

    CWDFileMigrator.update_hashfiles(comment)
