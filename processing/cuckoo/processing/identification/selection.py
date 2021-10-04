# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import json
import logging

import sflock
import sflock.exception

from cuckoo.common.config import cfg
from cuckoo.common.log import set_logger_level
from cuckoo.common.storage import AnalysisPaths

from ..abtracts import Processor
from ..errors import CancelProcessing

set_logger_level("PIL.Image", logging.WARNING)

def find_selected(f, tracklist):
    if f.selected:
        tracklist.append(f)

    if f.children:
        for child in f.children:
            find_selected(child, tracklist)

def find_unidentified(f, tracklist):
    if not f.identified:
        tracklist.append(f)

    if f.children:
        for child in f.children:
            find_unidentified(child, tracklist)

def _bytes_to_str(b):
    if isinstance(b, bytes):
        return b.decode()

def _write_filetree(analysis_id, tree):
    with open(AnalysisPaths.filetree(analysis_id), "w") as fp:
        json.dump(tree, fp, default=_bytes_to_str, indent=2)

def _write_filemap(analysis_id, filemap):
    with open(AnalysisPaths.filemap(analysis_id), "w") as fp:
        json.dump(filemap, fp)

def _make_ident_filename(f):
    if f.extension and not f.filename.lower().endswith(f.extension):
        return f"{f.filename}.{f.extension}"

    return f.filename

class Identify(Processor):

    ORDER = 1
    KEY = "identify"
    CATEGORY = ["file"]

    def start(self):

        submitted_file = AnalysisPaths.submitted_file(self.ctx.analysis.id)
        if not submitted_file.is_file():
            err = f"Submitted file for analysis: {self.ctx.analysis.id} " \
                  f"does not exist"
            raise CancelProcessing(err)

        # Retain the original file name. Instead of the hash that
        # originates from the filepath being a path to the binaries
        # folder.
        original_filename = self.ctx.analysis.submitted.filename

        settings_pass = self.ctx.analysis.settings.password
        try:
            f = sflock.unpack(
                submitted_file, filename=original_filename,
                password=settings_pass
            )
        except Exception as e:
            self.ctx.log.exception(
                "Unexpected Sflock unpacking failure", error=e
            )
            raise CancelProcessing(f"Unexpected Sflock unpacking failure. {e}")

        if f.mode:
            raise CancelProcessing(
                f"Failed to unpack file: {f.error}. Unpacker: {f.unpacker}"
            )

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

class SelectURL(Processor):

    ORDER = 999
    KEY = "selected"
    CATEGORY = ["url"]

    def start(self):
        return {
            "identified": True,
            "selected": True,
            "target": {
                "url": self.ctx.analysis.submitted.url,
                "platforms": [
                    {"platform": p, "os_version":""}
                    for p in sflock.identify.Platform.ANY
                ],
            }
        }


class SelectFile(Processor):
    """The SelectFile module must run as the last module that does anything
    with the list of sflock File objects created in the Identify module.
    Modules that run between those two are free to edit the list."""

    ORDER = 999
    KEY = "selected"
    CATEGORY = ["file"]

    def init(self):
        self.file_counter = 0
        self.tag_deps = cfg("identification", "tags", subpkg="processing")
        self.file_map = {}
        self.log_unidentified = cfg(
            "identification", "log_unidentified", subpkg="processing"
        )

        prio_exts = cfg(
            "identification", "selection", "extension_priority",
            subpkg="processing"
        )
        self.ext_priority = [x.strip(".") for x in prio_exts]

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

    def _determine_target(self, unpackedfile, selection):
        # If the submitted file is marked as selected. Return it as the
        # selected target. We want to prevent things such as PDFs/office docs
        # with embedded files to incorrectly be started, causing a fail of the
        # payload. This can happen if we select en embedded file.
        if unpackedfile.selected:
            return unpackedfile

        # Check if any of the selected files have an identified file extension
        # that is part of the priority list. Do this in order of the
        # extension priority list.
        for ext in self.ext_priority:
            for f in selection:
                if f.extension == ext:
                    return f

        # If no file was selected of the prioritized file types. Select the
        # first file marked as selected by Sflock.
        if selection:
            return selection[0]

        return None

    def start(self):
        selection = self.ctx.result.get("identify", {}).get("selection", [])
        unpackedfile = self.ctx.result.get("identify").get("unpacked")

        target = self._determine_target(unpackedfile, selection)
        # Deselect all files, except the chosen file.
        for f in selection:
            if f is not target:
                f.deselect()

        # Write a filetree of the unpacked submitted file to disk. Used during
        # "manual" selection and in the pre-stage to retrieve information
        # about a manually selected file.
        _write_filetree(
            self.ctx.analysis.id, unpackedfile.astree(
                sanitize=True, finger=True, child_cb=self._sflock_child_cb
            )
        )

        _write_filemap(self.ctx.analysis.id, self.file_map)

        if target:
            self.ctx.log.debug("File selected.", file=repr(target.filename))
        else:
            # If no file was selected, set the target as the submitted file. A
            # manual analysis or one that ignores identify still needs the
            # information such as the file extension.
            target = unpackedfile

        ident_filename = _make_ident_filename(target)
        if ident_filename != target.filename:
            self.ctx.log.debug(
                "Identify detected a different file type than extension "
                "indicates.", detected=target.extension,
                filename=repr(ident_filename)
            )

        if self.log_unidentified:
            unidentified = []
            find_unidentified(unpackedfile, unidentified)
            if unidentified:
                self.ctx.log.warning(
                    "Sflock did not identify all files.",
                    count=len(unidentified),
                    files=", ".join(f.filename for f in unidentified)
                )

        return {
            "identified": target.identified,
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
