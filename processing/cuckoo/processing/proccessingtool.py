# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common.startup import init_global_logging
from cuckoo.common.storage import cuckoocwd

from cuckoo.processing.worker import PostProcessingRunner
from cuckoo.processing.worker import TaskContext

from cuckoo.processing.post.eventconsumer import patternsigs
from cuckoo.processing.reporting import disk

import logging

if __name__ == "__main__":
    import pprint
    cuckoocwd.set(cuckoocwd.DEFAULT)

    init_global_logging(logging.DEBUG, filepath="/tmp/cuckoo.log", use_logqueue=False)
    patternsigs.PatternFinder.init_once()

    analysis_id = "20201203-S42ZSZ"
    task_id = "20201203-S42ZSZ_1"
    taskctx = TaskContext(analysis_id, task_id)

    runner = PostProcessingRunner(taskctx, event_consumer_classes=[patternsigs.PatternFinder], reporting_classes=[disk.JSONDump], processing_classes=[])
    runner.start()

    pprint.pprint(taskctx.signature_tracker.signatures_to_dict())
