# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import os

from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.storage import Paths, Binaries

from ..abtracts import Processor
from ..errors import PluginError
from ..signatures.yarasigs import YaraFile, YaraSignatureError

log = CuckooGlobalLogger(__name__)

class StaticYaraRules(Processor):

    CATEGORY = ["file"]

    compiled_rules = []

    @classmethod
    def enabled(cls):
        yarapath = Paths.yara_signatures("static")
        if not yarapath.is_dir():
            return False

        return len(os.listdir(yarapath)) > 0

    @classmethod
    def init_once(cls):
        yarapath = Paths.yara_signatures("static")
        if not os.path.isdir(yarapath):
            return

        for filename in os.listdir(yarapath):
            if not filename.endswith((".yar", ".yara")):
                continue

            try:
                rule_path = os.path.join(yarapath, filename)
                log.debug(
                    "Loading yara static signature file", filepath=rule_path
                )
                cls.compiled_rules.append(YaraFile(rule_path))
            except YaraSignatureError as e:
                raise PluginError(f"Error loading Yara rules. {e}")

    def start(self):
        if not self.compiled_rules:
            return

        matches = []
        filepath, _ = Binaries.path(
            Paths.binaries(), self.ctx.result.get("target").sha256
        )
        if not os.path.isfile(filepath):
            self.ctx.log.warning(
                "Cannot run yara rules, target path does not exist",
                filepath=filepath
            )
            return

        data = None
        if os.path.getsize(filepath) < 10 * 1024 * 1024:
            with open(filepath, "rb") as fp:
                data = fp.read()

        for rulefile in self.compiled_rules:
            if data:
                matches.extend(rulefile.match_data(data))
            else:
                matches.extend(rulefile.match_file(filepath))

        del data

        for match in matches:
            try:
                match.trigger_as_signature(
                    self.ctx.signature_tracker, "target file"
                )
            except YaraSignatureError as e:
                self.ctx.log.warning(
                    "Failed to trigger signature for Yara rule match", error=e,
                )
