# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.utils import browser_to_tag

from ..abtracts import Processor


class DetermineLaunchArgs(Processor):
    CATEGORY = ["file", "url"]
    KEY = "command"

    ext_launchargs = {
        "windows": {
            ".ps1": [
                "powershell.exe",
                "-ExecutionPolicy",
                "bypass",
                "-File",
                "%PAYLOAD%",
            ],
            ".jar": ["java", "-jar", "%PAYLOAD%"],
            ".dll": ["rundll32.exe", "%PAYLOAD%,#1"],
            ".msi": ["msiexec.exe", "/I", "%PAYLOAD%"],
            ".js": ["wscript.exe", "%PAYLOAD%"],
            ".cpl": ["control.exe", "%PAYLOAD"],
        }
    }

    browser_launchargs = {
        "windows": {
            "browser_internet_explorer": ["iexplore.exe", "%PAYLOAD%"],
            "browser_edge": ["cmd", "/c", "start", "microsoft-edge:%PAYLOAD%"],
            "browser_firefox": ["cmd", "/c", "start", "firefox", "%PAYLOAD%"],
            "browser_chrome": ["cmd", "/c", "start", "chrome", "%PAYLOAD%"],
        }
    }

    def _url_target_args(self):
        default_browser = self.ctx.analysis.settings.browser
        for platform in self.ctx.analysis.settings.platforms:
            browser = platform.settings.browser or default_browser
            # Never override a manually specified starting command.
            if not browser or platform.settings.command:
                continue

            launchargs = self.browser_launchargs.get(platform.platform)
            if not launchargs:
                continue

            tag = browser_to_tag(browser)
            command = launchargs.get(tag)
            # Set the launch args for this platform. This is needed to
            # correctly launch the browser.
            if command:
                platform.set_command(command)
                self.ctx.analysis.settings.set_updated()

        if not self.ctx.analysis.settings.browser:
            return {}

        # Build a map of the possible launch argument for each platform. This
        # is needed in case no platforms are specified and auto platform
        # selection is used.
        commands = {}
        tag = browser_to_tag(self.ctx.analysis.settings.browser)
        for platform, tags_launchargs in self.browser_launchargs.items():
            launchargs = tags_launchargs.get(tag)
            if launchargs:
                commands[platform] = launchargs

        return commands

    def _file_target_args(self):
        commands = {}
        target = self.ctx.result.get("target")

        if self.ctx.analysis.settings.orig_filename:
            name = target.orig_filename
        else:
            name = target.filename

        for platform in self.ctx.analysis.settings.platforms:
            # Never override a manually specified starting command.
            if platform.settings.command:
                continue

            platform_exts = self.ext_launchargs.get(platform)
            if not platform_exts:
                continue

            for ext, launchargs in platform_exts.items():
                if name.endswith(ext):
                    platform.set_command(launchargs)
                    self.ctx.analysis.settings.set_updated()
                    break

        # Build a map of the possible launch argument for each platform. This
        # is needed in case no platforms are specified and auto platform
        # selection is used.
        for platform, exts_launchargs in self.ext_launchargs.items():
            for ext, launchargs in exts_launchargs.items():
                if name.endswith(ext):
                    commands[platform] = launchargs
                    break

        return commands

    def start(self):
        # Do not determine any launch commands as a default one
        # was already given
        if self.ctx.analysis.settings.command:
            return {}

        if self.ctx.analysis.category == "file":
            return self._file_target_args()
        elif self.ctx.analysis.category == "url":
            return self._url_target_args()

        return {}
