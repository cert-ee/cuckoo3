# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import zipfile

import sflock

from ..abtracts import Processor
from ..errors import CancelProcessing

def find_child(archive, extraction_paths):
    current = None
    for path in extraction_paths:
        temp = None
        if not current:
            temp = get_child(archive, path.encode())
        else:
            temp = get_child(current, path.encode())

        if not temp:
            return None

        current = temp

    return current

def get_child(f, path):

    parents = []
    for child in f.children:
        if child.relapath == path:
            return child

        if child.children:
            parents.append(child)

    for parent in parents:
        return get_child(parent, path)

def zipify(f, path):
    """Turns any type of archive into an equivalent .zip file."""
    z = zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED)

    for child in f.children:
        z.writestr(child.relapath.decode(), child.contents)

    z.close()

class CreateZip(Processor):

    ORDER = 1
    CATEGORY = ["file"]

    def start(self):
        if self.analysis.category != "file":
            return

        target = self.identification.target
        if not self.identification.parent and not target.container:
            return

        if not target.extrpath:
            return

        f = sflock.unpack(self.submitted_file.encode())

        selected_file = find_child(f, target.extrpath)
        if not selected_file:
            err = f"Path: {target.extrpath} not found in container. " \
                  f"No file to unpack"
            self.errtracker.fatal_error(err)
            raise CancelProcessing(err)

        zipify(
            selected_file.parent,
            os.path.join(self.analysis_path, "target.zip")
        )
