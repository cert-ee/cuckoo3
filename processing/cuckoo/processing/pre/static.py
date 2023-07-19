# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import os.path

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
        (".doc", ".docm", ".wbk", ".dotm", ".dotx", ".docb", ".docx",
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
        if os.path.getsize(file_path) < 1:
            return {}

        data = {}
        subkey = None

        for ext, handler_subkey in self._EXTENSION_HANDLER.items():

            if not target.filename.lower().endswith(ext):
                continue

            handler, subkey = handler_subkey
            try:
                data = handler(file_path).to_dict()
            except StaticAnalysisError as e:
                self.ctx.log.warning(
                    "Failed to run static analysis handler",
                    handler=handler, error=e
                )
            except Exception as e:
                err = "Unexpected error while running static analysis handler"
                self.ctx.log.exception(err, handler=handler, error=e)
                self.ctx.errtracker.add_error(
                    f"{err}. Handler: {handler}. Error: {e}"
                )

            break

        if data:
            return {
                subkey:data
            }

        return {}
