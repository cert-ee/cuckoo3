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

def _write_filemap(dir_path, filemap):
    filemap_path = os.path.join(dir_path, "filemap.json")
    with open(filemap_path, "w") as fp:
        json.dump(filemap, fp)


def _make_ident_filename(f):
    if f.extension and not f.filename.endswith(f.extension):
        return f"{f.filename}.{f.extension}"
    return f.filename

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
            self.errtracker.add_error(f"Sflock unpack error: {f.error}.", self)

        selected = []
        find_selected(f, selected)

        return {
            "unpacked": f,
            "selection": selected,
            "submitted": {
                "filename": f.filename,
                "platforms": f.platforms,
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
        self.file_counter = 0
        self.tag_deps = cfg("identification", "tags", subpkg="processing")
        self.file_map = {}

    def _get_tags_dep(self, dep):
        tags = []
        for tag, deplist in self.tag_deps.items():
            if dep in deplist:
                tags.append(tag)

        return tags

    def _sflock_child_cb(self, f, ret):
        self.file_counter += 1
        file_id = str(self.file_counter)
        ret["machine_tags"] = self._get_tags_dep(f.dependency)
        ret["orig_filename"] = f.filename
        ret["filename"] = _make_ident_filename(f)
        ret["id"] = file_id
        self.file_map[file_id] = ret["extrpath"]

    def start(self):
        if self.analysis.category != "file":
            return

        submitted = self.results.get("identify", {}).get("submitted", {})
        selection = self.results.get("identify", {}).get("selection", [])
        unpackedfile = self.results["identify"]["unpacked"]

        target = None
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
                    target = f
                    break

            if target:
                break

        # If no file was selected of the prioritized file types. Select the
        # first file marked as selected by Sflock.
        if not target and selection:
            target = selection[0]

        # Deselect all files, except the chosen file.
        for f in selection:
            if f is not target:
                f.deselect()

        # Write a filetree of the unpacked submitted file to disk. Used during
        # "manual" selection and in the pre-stage to retrieve information
        # about a manually selected file.
        _write_filetree(
            self.analysis_path, unpackedfile.astree(
                sanitize=True, finger=True, child_cb=self._sflock_child_cb
            )
        )

        _write_filemap(self.analysis_path, self.file_map)

        if target:
            self.analysislog.debug(
                "File selected.", file=repr(target.filename)
            )
        else:
            # If no file was selected, set the target as the submitted file. A
            # manual analysis or one that ignores identify still needs the
            # information such as the file extension.
            target = unpackedfile

        ident_filename = _make_ident_filename(target)
        if ident_filename != target.filename:
            self.analysislog.debug(
                "Identify detected a different file type than extension "
                "indicates.", detected=target.extension,
                filename=repr(ident_filename)
            )

        return {
            "selected": target.selected,
            "target": {
                "filename": ident_filename,
                "orig_filename": target.filename,
                "platforms": target.platforms,
                "size": target.filesize,
                "filetype": target.magic,
                "media_type": target.mime,
                "extrpath": target.extrpath,
                "password": target.password or "",
                "machine_tags": self._get_tags_dep(target.dependency),
                "container": len(target.children) > 0,
                "sha256": target.sha256,
                "sha1": target.sha1,
                "md5": target.md5,
            }
        }
