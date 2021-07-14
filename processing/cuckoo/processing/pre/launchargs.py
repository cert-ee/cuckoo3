# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from ..abtracts import Processor

class DetermineLaunchArgs(Processor):

    CATEGORY = ["file"]
    KEY = "command"

    ext_launchargs = {
        ".ps1": [
            "powershell.exe", "-ExecutionPolicy", "bypass", "-File",
            "%PAYLOAD%"
        ],
        ".jar": ["java", "-jar", "%PAYLOAD%"],
        ".dll": ["rundll32.exe", "%PAYLOAD%,#1"],
        ".msi": ["msiexec.exe", "/I", "%PAYLOAD%"],
        ".js": ["wscript.exe", "%PAYLOAD%"],
        ".cpl": ["control.exe", "%PAYLOAD"]
    }

    def start(self):
        target = self.ctx.result.get("target")

        if self.ctx.analysis.settings.orig_filename:
            name = target.orig_filename
        else:
            name = target.filename
        for ext, launchargs in self.ext_launchargs.items():
            if name.endswith(ext):

                return launchargs
