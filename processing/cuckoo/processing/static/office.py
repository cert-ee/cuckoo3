# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import logging
import re
import zipfile
import zlib
import oletools.olevba

from cuckoo.common.log import set_logger_level

from ..errors import StaticAnalysisError

set_logger_level("alevba", logging.ERROR)

class OfficeStaticAnalysisError(StaticAnalysisError):
    pass

def _deobfuscate(code):
    """Bruteforce approach of regex-based deobfuscation."""
    deobf = [
        [
            # "A" & "B" -> "AB"
            "\\\"(?P<a>.*?)\\\"\\s+\\&\\s+\\\"(?P<b>.*?)\\\"",
            lambda x: f'f"{x.group("a")}{x.group("b")}"',
            0,
        ],
    ]

    changes = 1
    while changes:
        changes = 0

        for pattern, repl, flags in deobf:
            count = 1
            while count:
                code, count = re.subn(pattern, repl, code, flags=flags)
                changes += count

    return code

class OfficeDocument:

    def __init__(self, filepath):
        self._filepath = filepath

    def extract_eps(self):
        """Extract some information from Encapsulated Post Script files."""
        try:
            z = zipfile.ZipFile(self._filepath)
        except (ValueError, zipfile.BadZipFile, RuntimeError):
            return []

        ret = []
        eps_comments = "\\(([\\w\\s]+)\\)"
        try:
            for name in z.namelist():
                if name.lower().endswith(".eps"):
                    ret.extend(re.findall(eps_comments, z.read(name)))
        except (ValueError, zipfile.BadZipFile, RuntimeError):
            return []
        finally:
            z.close()

        return ret

    def get_macros(self):
        """Get embedded Macros if this is an Office document."""
        try:
            p = oletools.olevba.VBA_Parser(self._filepath)
        except (TypeError, oletools.olevba.FileOpenError, zlib.error):
            return

        # We're not interested in plaintext.
        if p.type == "Text":
            return

        try:
            for f, s, v, c in p.extract_macros():
                yield {
                    "stream": s,
                    "filename": v,
                    "orig_code": c,
                    "deobf": _deobfuscate(c),
                }
        except ValueError as e:
            pass

    def to_dict(self):
        return {
            "macros": list(self.get_macros()),
            "eps": self.extract_eps()
        }
