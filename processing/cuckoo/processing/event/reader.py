# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.storage import TaskPaths
from cuckoo.common.packages import enumerate_plugins
from cuckoo.processing.abtracts import LogFileTranslator

class NormalizedEventReader:

    _translator_classes = enumerate_plugins(
        "cuckoo.processing.event.translate.threemon", globals(),
        LogFileTranslator
    )

    def __init__(self, task_context):
        self.taskctx = task_context

    @classmethod
    def _find_translator(cls, logname):
        for translator_class in cls._translator_classes:
            if translator_class.handles(logname):
                return translator_class

    def _find_task_logfiles(self):
        logs_path = TaskPaths.logfile(self.taskctx.task.id)
        log_files = []
        for filename in os.listdir(logs_path):
            logfile_path = os.path.join(logs_path, filename)
            if os.path.isdir(logfile_path):
                continue

            log_files.append((filename, logfile_path))

        return log_files

    def _find_translators(self, logname_logpath):

        for filename, filepath in logname_logpath:
            translator_class = self._find_translator(filename)
            if not translator_class:
                self.taskctx.log.warning(
                    "No log translator found for log.",
                    task_id=self.taskctx.task.id, logname=repr(filename)
                )
                continue

            self.taskctx.log.debug(
                "Chose translator for logfile.", logfile=filename,
                translator_class=translator_class
            )

            yield translator_class(filepath, self.taskctx)

    def read_events(self):

        for translator in self._find_translators(self._find_task_logfiles()):

            with translator:
                for event in translator.read_events():
                    yield event
