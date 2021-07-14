# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import json
import logging
import os
import zipfile
from pathlib import Path
import sflock

from cuckoo.common.log import set_logger_level
from cuckoo.common.storage import AnalysisPaths, Binaries, InMemoryFile, Paths
from cuckoo.common.strictcontainer import TargetFile

from ..abtracts import Processor
from ..errors import CancelProcessing

set_logger_level("PIL.Image", logging.WARNING)

def find_target_in_archive(archive, extraction_paths):
    current = None
    for path in extraction_paths:
        temp = None
        if not current:
            temp = get_child(archive, path)
        else:
            temp = get_child(current, path)

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

def _make_ident_relapath(f):
    if not f.extension:
        return f.relapath

    relaparts = Path(f.relapath).parts
    filename = f.filename

    if not relaparts:
        return f.relapath

    if not f.filename.lower().endswith(f.extension):
        filename = f"{f.filename}.{f.extension}"

    return str(Path(*relaparts[:-1] + (filename,)))

def zipify_target(target_f, zip_path, original_filename=False):
    """Turns any type of archive into an equivalent .zip file."""
    z = zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED)

    target_relapath = target_f.relapath
    for child in target_f.parent.children:
        relapath = child.relapath

        # Create a relative archive path that uses the identified extension
        # in the file name.
        if child == target_f:
            if original_filename:
                target_relapath = relapath
            else:
                relapath = _make_ident_relapath(child)
                target_relapath = relapath

        z.writestr(relapath, child.contents)

    z.close()

    return target_relapath

def find_child_in_tree(file_dict, extraction_paths):
    current = None
    for path in extraction_paths:
        temp = None
        if not current:
            temp = get_child_tree(file_dict, path)
        else:
            temp = get_child_tree(current, path)

        if not temp:
            return None

        current = temp

    return current

def get_child_tree(file_dict, relapath):
    parents = []
    for child in file_dict.get("children", []):

        if child.get("relapath") == relapath:
            return child

        if child.get("children", []):
            parents.append(child)

    for parent in parents:
        return get_child_tree(parent, relapath)

class DetermineTarget(Processor):

    ORDER = 1
    KEY = "target"

    CATEGORY = ["file", "url"]

    def start(self):
        if self.ctx.analysis.category == "url":
            return self.ctx.identification.target

        extrpath = self.ctx.analysis.settings.extrpath
        if not extrpath:
            # Do not use the identified filename/extension for the selected file
            # if the orig_filename setting is set to True.
            if self.ctx.analysis.settings.orig_filename:
                name = self.ctx.identification.target.orig_filename
                self.ctx.identification.target.filename = name

            return self.ctx.identification.target

        # Find file info in filetree.json
        treepath = AnalysisPaths.filetree(self.ctx.analysis.id)
        if not os.path.isfile(treepath):
            raise CancelProcessing(
                "Filetree.json not found. Cannot continue."
            )

        with open(treepath, "r") as fp:
            target = find_child_in_tree(json.load(fp), extrpath)
            if not target:
                raise CancelProcessing(
                    f"Path: {extrpath} not found in file tree."
                )

        # Do not use the identified filename/extension for the selected file
        # if the orig_filename setting is set to True.
        if self.ctx.analysis.settings.orig_filename:
            filename = target["orig_filename"]
        else:
            filename = target["filename"]

        return TargetFile(
            filename=filename,
            orig_filename=target["orig_filename"],
            platforms=target["platforms"],
            machine_tags=target["machine_tags"], size=target["size"],
            filetype=target["finger"]["magic"],
            media_type=target["finger"]["mime"],
            extrpath=target["extrpath"],
            container=len(target["children"]) > 0,
            sha256=target["sha256"], sha1=target["sha1"], md5=target["md5"]
        )

class CreateZip(Processor):

    ORDER = 2
    CATEGORY = ["file"]

    def start(self):
        target = self.ctx.result.get("target")
        if not target.extrpath:
            return

        self.ctx.log.debug(
            "Finding child archive for selected file and normalizing to zip."
        )

        try:
            f = sflock.unpack(
                AnalysisPaths.submitted_file(self.ctx.analysis.id),
                password=self.ctx.analysis.settings.password
            )
        except Exception as e:
            self.ctx.log.exception(
                "Unexpected Sflock unpacking failure.", error=e
            )
            raise CancelProcessing(f"Sflock unpacking failure. {e}")

        if f.mode:
            raise CancelProcessing(
                f"Failed to unpack file: {f.error}. Unpacker: {f.unpacker}"
            )

        selected_file = find_target_in_archive(f, target.extrpath)
        if not selected_file:
            raise CancelProcessing(
                f"Path: {target.extrpath} not found in container. No file to "
                f"unpack"
            )

        # Store the unpacked file in the binaries folder so it can be retrieved
        # by hash when needed.
        Binaries.store(Paths.binaries(), InMemoryFile(selected_file.contents))

        # Normalize the lowest parent of the target to a zipfile. This
        # is the zipfile that will be uploaded to the analysis machine.
        # Also overwrite the extrpath path the target will be located at in the
        # newly created zip. This new path includes a filename+identified
        # file extension.
        # Re-zip file with original filename if this was specific in the
        # submission settings. This causes the identified file extension to
        # be ignored.
        target.extrpath = [zipify_target(
            selected_file, AnalysisPaths.zipified_file(self.ctx.analysis.id),
            original_filename=self.ctx.analysis.settings.orig_filename
        )]
