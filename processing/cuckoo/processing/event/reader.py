# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from cuckoo.common.storage import TaskPaths
from cuckoo.common.packages import enumerate_plugins
from cuckoo.processing.abtracts import LogFileTranslator, Safelist

class NormalizedEventReader:

    _translator_classes = enumerate_plugins(
        "cuckoo.processing.translate.threemon", globals(), LogFileTranslator
    )

    _safelist_instances = []

    def __init__(self, task_context):
        self.taskctx = task_context

    @classmethod
    def init_once(cls):
        safelist_classes = enumerate_plugins(
            "cuckoo.processing.safelist", globals(), Safelist
        )

        for safelist_class in safelist_classes:
            cls._safelist_instances.append(safelist_class())

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

            yield translator_class(filepath)

    def read_events(self):

        for translator in self._find_translators(self._find_task_logfiles()):

            with translator:
                for event in translator.read_events():

                    # Hand to safelist module instances.
                    for safelist in self._safelist_instances:
                        if event.kind in safelist.event_types:
                            safelist.check_safelist(event)

                    yield event
