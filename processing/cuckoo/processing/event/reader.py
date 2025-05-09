# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.storage import TaskPaths
from cuckoo.common.packages import enumerate_plugins
from cuckoo.processing.abtracts import LogFileTranslator


class NormalizedEventReader:
    _translator_classes = enumerate_plugins(
        "cuckoo.processing.event.translate.threemon", globals(), LogFileTranslator
    )

    def __init__(self, task_context):
        self.taskctx = task_context

    @classmethod
    def _find_translator(cls, logname):
        for translator_class in cls._translator_classes:
            if translator_class.handles(logname):
                return translator_class

    def _find_task_logfiles(self):
        log_files = []
        for path in TaskPaths.logfile(self.taskctx.task.id).iterdir():
            if path.is_dir():
                continue

            log_files.append((path.name, path))

        return log_files

    def _find_translators(self, logname_logpath):
        for filename, filepath in logname_logpath:
            translator_class = self._find_translator(filename)
            if not translator_class:
                self.taskctx.log.warning(
                    "No log translator found for log.",
                    task_id=self.taskctx.task.id,
                    logname=repr(filename),
                )
                continue

            self.taskctx.log.debug(
                "Chose translator for logfile.",
                logfile=filename,
                translator_class=translator_class,
            )

            yield translator_class(filepath, self.taskctx)

    def read_events(self):
        for translator in self._find_translators(self._find_task_logfiles()):
            with translator:
                for event in translator.read_events():
                    yield event
