# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os

import sflock

from ..helpers import Processor, bytes_to_str

def find_selected(f, tracklist):
    if f.selected:
        tracklist.append(f)

    if f.children:
        for child in f.children:
            find_selected(child, tracklist)

class Identify(Processor):

    ORDER = 1
    KEY = "identify"
    CATEGORY = ["file"]

    def start(self):
        if self.analysis.category !="file" or not self.submitted_file:
            return

        if not os.path.isfile(self.submitted_file):
            self.errtracker.fatal_error(
                f"Submitted file for analysis: {self.analysis.id} "
                f"does not exist"
            )

        # Retain the original file name. Instead of the hash that
        # originates from the filepath being a path to the binaries
        # folder.
        original_filename = self.analysis.submitted.filename.encode()

        # TODO properly handle and propagate as Sflock errors in Sflock.
        try:
            f = sflock.unpack(
                self.submitted_file.encode(), filename=original_filename
            )
        except Exception as e:
            self.errtracker.fatal_exception(f"Sflock unpacking failure. {e}")

        if f.children:
            tree = f.astree(sanitize=True, finger=True)
            self.write_filetree(tree)

        selected = []
        find_selected(f, selected)

        platforms = []
        if f.platform:
            platforms.append(f.platform)

        return {
            "selection": selected,
            "submitted": {
                "filename": f.filename,
                "platforms": platforms,
                "size": f.filesize,
                "package": f.package,
                "filetype": f.magic,
                "media_type": f.mime,
                "sha256": f.sha256,
                "extrpath": f.extrpath,
                "password": f.password,
                "container": len(f.children) > 0
            }
        }

    def write_filetree(self, tree):
        filetree_path = os.path.join(self.analysis_path, "filetree.json")
        with open(filetree_path, "w") as fp:
            json.dump(tree, fp, default=bytes_to_str, indent=2)

class SelectFile(Processor):

    ORDER = 999
    KEY = "selected"
    CATEGORY = ["file"]

    # PoC values. TODO replace with values from config etc later.
    PRIO_DEFAULT = [".exe", ".msi", ".docx", ".docm", ".pdf"]
    PRIO_CONTAINER = [".msi"] + PRIO_DEFAULT

    CONTAINER_TYPE_PRIO = {
        "archive": [".msi"] + PRIO_DEFAULT,
        "application/pdf": [".pdf"] + PRIO_DEFAULT
    }

    def start(self):
        if self.analysis.category != "file":
            return

        submitted = self.results.get("identify", {}).get("submitted", {})
        selection = self.results.get("identify", {}).get("selection", [])

        selected = None
        type_priority = []

        # Determine the type of container, as the order of prioritized files
        # might be different for each type of container.
        # E.g: mail, PDF, archive
        if submitted.get("type") == "container":
            prio_order = self.CONTAINER_TYPE_PRIO.get(
                submitted.get["media_type"]
            )
            if prio_order:
                type_priority = prio_order
            else:
                type_priority = self.PRIO_CONTAINER

        if not type_priority:
            type_priority = self.PRIO_DEFAULT

        for ext in type_priority:
            for f in selection:
                if f.filename.decode().endswith(ext):
                    selected = f
                    break

            if selected:
                break

        # If no file was selected of the prioritized file types. Select the
        # first file marked as selected by Sflock.
        if not selected:
            if selection:
                selected = selection[0]
            else:
                return {}

        platforms = []
        if selected.platform:
            platforms.append(selected.platform)

        return {
            "filename": selected.filename,
            "platforms": platforms,
            "size": selected.filesize,
            "package": selected.package,
            "filetype": selected.magic,
            "media_type": selected.mime,
            "sha256": selected.sha256,
            "extrpath": selected.extrpath,
            "password": selected.password or "",
            "container": len(selected.children) > 0
        }
