# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import zipfile
import json

import sflock

from cuckoo.common.strictcontainer import TargetFile

from ..abtracts import Processor
from ..errors import CancelProcessing

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

def zipify(f, path):
    """Turns any type of archive into an equivalent .zip file."""
    z = zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED)

    for child in f.children:
        z.writestr(child.relapath, child.contents)

    z.close()

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

    CATEGORY = ["file"]

    def start(self):
        if self.analysis.category == "url":
            return self.identification.target

        if self.analysis.category != "file":
            return

        if not self.analysis.settings.extrpath:
            return self.identification.target

        extrpath = self.analysis.settings.extrpath

        # Find file info in filetree.json
        treepath = os.path.join(self.analysis_path, "filetree.json")
        if not os.path.isfile(treepath):
            err = f"Filetree.json not found. Cannot continue."
            self.errtracker.fatal_error(err)
            raise CancelProcessing(err)

        with open(treepath, "r") as fp:
            target = find_child_in_tree(json.load(fp), extrpath)
            if not target:
                err = f"Path: {extrpath} not found in file tree. "
                self.errtracker.fatal_error(err)
                raise CancelProcessing(err)

        return TargetFile(
            filename=target["filename"],
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
        if self.analysis.category != "file":
            return

        target = self.results.get("target")
        if not target.extrpath:
            return

        self.analysislog.debug(
            "Finding child archive for selected file and normalizing to zip."
        )

        try:
            f = sflock.unpack(self.submitted_file)
        except Exception as e:
            err = f"Sflock unpacking failure. {e}"
            self.errtracker.fatal_exception(err)
            raise CancelProcessing(err)

        selected_file = find_target_in_archive(f, target.extrpath)
        if not selected_file:
            err = f"Path: {target.extrpath} not found in container. " \
                  f"No file to unpack"
            self.errtracker.fatal_error(err)
            raise CancelProcessing(err)

        # Normalize the lowest parent of the target to a zipfile. This
        # is the zipfile that will be uploaded to the analysis machine.
        zipify(
            selected_file.parent,
            os.path.join(self.analysis_path, "target.zip")
        )
