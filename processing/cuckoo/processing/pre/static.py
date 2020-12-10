# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common.storage import Paths, Binaries

from ..abtracts import Processor
from ..static.pe import PEFile
from ..static.office import OfficeDocument
from ..errors import StaticAnalysisError

class FileInfoGather(Processor):

    CATEGORY = ["file"]
    KEY = "static"

    _EXTENSION_HANDLER = {
        (".exe", ".dll"): (PEFile, "pe"),
        # Word
        (".doc", ".docm", ".wbk" ,".dotm", ".dotx",".docb", ".docx",
        # Hangul word processor
          ".hwp",
        # Powerpoint
          ".ppt", ".pptm", ".pptx", ".potm", ".ppam", ".ppsm", ".potx",
          ".ppsx", ".sldx", ".sldm",
        # Excel
          "xls", "xlsm", "xlsx", "xlm", "xlt", "xltx", "xltm",
          "xlsb", "xla", "xlam", "xll", "xlw",): (OfficeDocument, "office")
    }

    def start(self):
        target = self.ctx.result.get("target")

        file_path, _ = Binaries.path(Paths.binaries(), target.sha256)

        data = {}
        subkey = None

        for ext, handler_subkey in self._EXTENSION_HANDLER.items():

            if not target.filename.endswith(ext):
                continue

            handler, subkey = handler_subkey
            try:
                data = handler(file_path).to_dict()
            except StaticAnalysisError as e:
                self.ctx.log.warning(
                    "Failed to run static analysis handler",
                    handler=handler, error=e
                )

            break

        if data:
            return {
                subkey:data
            }

        return {}
