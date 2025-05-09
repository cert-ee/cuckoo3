# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.startup import init_global_logging
from cuckoo.common.storage import cuckoocwd
from cuckoo.common.startup import load_configurations

from cuckoo.processing.worker import PostProcessingRunner
from cuckoo.processing.worker import TaskContext


from cuckoo.processing.post.eventconsumer import patternsigs, injection
from cuckoo.processing.post import network, misp
from cuckoo.processing.reporting import disk, misp as mispreporting

from cuckoo.processing.post.eventconsumer.patternsigs import PatternFinder
from cuckoo.processing.post.eventconsumer.injection import ProcessInjection

import logging

if __name__ == "__main__":
    import pprint

    cuckoocwd.set(cuckoocwd.DEFAULT)

    init_global_logging(logging.DEBUG, filepath="/tmp/cuckoo.log", use_logqueue=False)
    load_configurations()
    PostProcessingRunner.init_once()
    PatternFinder.init_once()
    # patternsigs.PatternFinder.init_once()
    # injection.ProcessInjection.init_once()
    # network.Pcapreader.init_once()
    # misp.MispInfoGather.init_once()
    # mispreporting.MISP.init_once()
    # PatternFinder.init_once()

    analysis_id = "20210607-8YDUC8"
    task_id = "20210607-8YDUC8_1"
    taskctx = TaskContext(analysis_id, task_id)

    runner = PostProcessingRunner(
        taskctx,
        event_consumer_classes=[PatternFinder],
        reporting_classes=[disk.JSONDump],
        processing_classes=[],
    )
    runner.start()

    pprint.pprint(taskctx.signature_tracker.signatures_to_dict())
