# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os

import sflock

from cuckoo.common.config import cfg

from ..abtracts import Processor
from ..errors import CancelProcessing

def find_selected(f, tracklist):
    if f.selected:
        tracklist.append(f)

    if f.children:
        for child in f.children:
            find_selected(child, tracklist)

def _bytes_to_str(b):
    if isinstance(b, bytes):
        return b.decode()

def _write_filetree(dir_path, tree):
    filetree_path = os.path.join(dir_path, "filetree.json")
    with open(filetree_path, "w") as fp:
        json.dump(tree, fp, default=_bytes_to_str, indent=2)


class Identify(Processor):

    ORDER = 1
    KEY = "identify"
    CATEGORY = ["file"]

    def start(self):
        if self.analysis.category !="file" or not self.submitted_file:
            return

        if not os.path.isfile(self.submitted_file):
            err = f"Submitted file for analysis: {self.analysis.id} " \
                  f"does not exist"
            self.errtracker.fatal_error(err)
            raise CancelProcessing(err)

        # Retain the original file name. Instead of the hash that
        # originates from the filepath being a path to the binaries
        # folder.
        original_filename = self.analysis.submitted.filename

        # TODO properly handle and propagate as Sflock errors in Sflock.
        try:
            f = sflock.unpack(
                self.submitted_file, filename=original_filename
            )
        except Exception as e:
            err = f"Sflock unpacking failure. {e}"
            self.errtracker.fatal_exception(err)
            raise CancelProcessing(err)


        if f.error:
            self.errtracker.add_error(f.error, self)

        if f.children:
            # Move tree writing to selection module. All 'selected' files
            # in the sflock tree should be set to False first, except the
            # actual chosen candidate for analysis.
            tree = f.astree(sanitize=True, finger=True)
            _write_filetree(self.analysis_path, tree)

        selected = []
        find_selected(f, selected)

        platforms = []
        if f.platforms:
            # TODO replace later when strictcontainer can handle lists of
            # strictcontainers
            for platform in f.platforms:
                platforms.append({
                    "platform": platform,
                    "os_version": ""
                })

        return {
            "selection": selected,
            "submitted": {
                "filename": f.filename,
                "platforms": platforms,
                "size": f.filesize,
                "filetype": f.magic,
                "media_type": f.mime,
                "sha256": f.sha256,
                "extrpath": f.extrpath,
                "password": f.password,
                "container": len(f.children) > 0
            }
        }



class SelectFile(Processor):
    """The SelectFile module must run as the last module that does anything
    with the list of sflock File objects created in the Identify module.
    Modules that run between those two are free to edit the list."""

    ORDER = 999
    KEY = "selected"
    CATEGORY = ["file"]

    # PoC values. TODO replace with values from config etc later.
    PRIO_DEFAULT = [".exe", ".msi", ".docm", ".docx", ".pdf"]
    PRIO_CONTAINER = [".msi"] + PRIO_DEFAULT

    CONTAINER_TYPE_PRIO = {
        "archive": [".msi"] + PRIO_DEFAULT,
        "application/pdf": [".pdf"] + PRIO_DEFAULT
    }

    def init(self):
        self.tag_deps = cfg("identification", "tags", subpkg="processing")

    def _get_tags_dep(self, dep):
        tags = []
        for tag, deplist in self.tag_deps.items():
            if dep in deplist:
                tags.append(tag)

        return tags

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
                if f.filename.endswith(ext):
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
        if selected.platforms:
            # TODO replace later when strictcontainer can handle lists of
            # strictcontainers
            for platform in selected.platforms:
                platforms.append({
                    "platform": platform,
                    "os_version": ""
                })

        self.analysislog.debug("File selected.", file=repr(selected.filename))
        ident_filename = selected.filename
        ident_ext = selected.extension
        if ident_ext and not ident_filename.endswith(ident_ext):
            ident_filename = f"{ident_filename}.{ident_ext}"
            self.analysislog.debug(
                "Identify detected a different file type than extension "
                "indicates.", detected=ident_ext, filename=repr(ident_filename)
            )

        return {
            "filename": ident_filename,
            "orig_name": selected.filename,
            "platforms": platforms,
            "size": selected.filesize,
            "filetype": selected.magic,
            "media_type": selected.mime,
            "sha256": selected.sha256,
            "extrpath": selected.extrpath,
            "password": selected.password or "",
            "machine_tags": self._get_tags_dep(selected.dependency),
            "container": len(selected.children) > 0
        }
