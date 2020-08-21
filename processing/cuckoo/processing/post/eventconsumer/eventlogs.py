# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import json
import os

from cuckoo.common.storage import TaskPaths

from cuckoo.processing.abtracts import EventConsumer
from cuckoo.processing.translate.events import Kinds

class EventJSONFiles(EventConsumer):

    event_types = (Kinds.FILE, Kinds.REGISTRY, Kinds.PROCESS, Kinds.MUTANT)

    def init(self):
        self.fps = {}
        eventdir = TaskPaths.eventlog(self.taskctx.task.id)
        if not os.path.exists(eventdir):
            os.mkdir(eventdir)

    def use_event(self, event):
        if event.kind not in self.fps:
            self.fps[event.kind] = open(
                f"{TaskPaths.eventlog(self.taskctx.task.id, event.kind)}.json",
                "w"
            )

        self.fps[event.kind].write(
            f"{json.dumps(event.to_dict(), separators=(',', ':'))}\n"
        )

    def cleanup(self):
        for fp in self.fps.values():
            fp.close()
