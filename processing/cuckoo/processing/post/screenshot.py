# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import os

from cuckoo.common.storage import TaskPaths

from ..abtracts import Processor


class ScreenshotTiming(Processor):
    CATEGORY = ["file", "url"]
    KEY = "screenshot"

    def start(self):
        task_end = self.ctx.analysis.settings.timeout * 1000
        allshots = []
        for shot in os.listdir(TaskPaths.screenshot(self.ctx.task.id)):
            name, _ = os.path.splitext(shot)
            if not name.isdigit():
                continue

            allshots.append((int(name), shot))

        if not allshots:
            return

        # Sort by the ts of the screenshot
        allshots.sort(key=lambda k: k[0])

        # Use the last shot ts as the task end if it is larger than the
        # timeout. It might be larger because the shot ts starts as soon as
        # a task is mapped to the result server. Which happens before the
        # actual task payload starts.
        if allshots[-1][0] > task_end:
            task_end = allshots[-1][0]

        ordered_shots = []
        one = task_end / 100
        # Calculate the percentage of time of the total task time the screen
        # remained the same
        total_shots = len(allshots)
        for i in range(0, total_shots):
            cur = allshots[i]
            next_idx = i + 1
            if next_idx >= total_shots:
                percentage = (task_end - cur[0]) / one
            else:
                # Use the first screenshot as if its ts is 0. As this first
                # is always taken. The time this screen state remained
                # is the percentage of time until the second screenshot.
                if i == 0:
                    percentage = allshots[next_idx][0] / one
                else:
                    percentage = (allshots[next_idx][0] - cur[0]) / one

            ordered_shots.append({"name": cur[1], "percentage": percentage})

        return ordered_shots
