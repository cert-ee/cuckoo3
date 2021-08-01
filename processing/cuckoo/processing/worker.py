# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common.dns import ResolveTracker
from cuckoo.common.strictcontainer import Task, Analysis, Identification
from cuckoo.common.storage import TaskPaths, AnalysisPaths, Paths
from cuckoo.common.startup import init_safelist_db
from cuckoo.common.errors import ErrorTracker
from cuckoo.common.log import AnalysisLogger, TaskLogger
from cuckoo.common.machines import Machine

from .errors import (
    PluginError, PluginWorkerError, CancelProcessing, CancelReporting,
    DisablePluginError
)

from cuckoo.processing.event.reader import NormalizedEventReader

from .family import FamilyTracker
from .tag import TagTracker
from .ttp import TTPTracker
from .signatures.signature import SignatureTracker
from .event.processtools import ProcessTracker

class ProcessingResult:

    def __init__(self):
        self._result = {}

    def store(self, key, result):
        if key in self._result:
            raise KeyError(f"{key} would overwrite existing result.")

        self._result[key] = result

    def get(self, key, default=None):
        return self._result.get(key, default)

    def __contains__(self, item):
        return item in self._result

class ProcessingContext:

    def __init__(self, analysis_id, logger):

        self.log = logger
        self.result = ProcessingResult()
        self.errtracker = ErrorTracker()

        self.analysis = Analysis.from_file(
            AnalysisPaths.analysisjson(analysis_id)
        )

        self.ttp_tracker = TTPTracker()
        self.tag_tracker = TagTracker()
        self.family_tracker = FamilyTracker()
        self.signature_tracker = SignatureTracker(
            tagtracker=self.tag_tracker, ttptracker=self.ttp_tracker,
            familytracker=self.family_tracker
        )
        self.completed = False

    def _errtracker_to_file(self):
        raise NotImplementedError

    def set_completed(self):
        self.completed = True

    def set_failed(self):
        self.completed = False

    def close(self):
        if self.errtracker.has_errors():
            self._errtracker_to_file()

        self.log.close()

class AnalysisContext(ProcessingContext):

    def __init__(self, stage, analysis_id):
        super().__init__(analysis_id, AnalysisLogger(__name__, analysis_id))

        self.stage = stage

        if stage == "pre":
            self.identification = Identification.from_file(
                AnalysisPaths.identjson(analysis_id)
            )
        else:
            self.identification = None

    def _errtracker_to_file(self):
        self.errtracker.to_file(
            AnalysisPaths.processingerr_json(self.analysis.id)
        )

class TLSSessionTracker:

    def __init__(self):
        self._sessions = {}

    @property
    def sessions(self):
        return self._sessions

    def add_session(self, client_random, server_random, master_secret):
        self._sessions[(client_random, server_random)] = master_secret

class NetworkContext:

    def __init__(self):
        self.dns = ResolveTracker()
        self.tls = TLSSessionTracker()

class TaskContext(ProcessingContext):

    def __init__(self, analysis_id, task_id):
        super().__init__(analysis_id, TaskLogger(__name__, task_id))

        self.stage = "post"
        self.task = Task.from_file(TaskPaths.taskjson(task_id))
        self.machine = Machine.from_file(TaskPaths.machinejson(self.task.id))
        self.process_tracker = ProcessTracker()
        self.network = NetworkContext()

    def _errtracker_to_file(self):
        self.errtracker.to_file(
            TaskPaths.processingerr_json(self.task.id)
        )


def make_plugin_instances(plugin_classes, ctx, *args, **kwargs):

    instances = []
    for plugin_class in plugin_classes:

        if not plugin_class.enabled():
            continue

        # If the plugin class has categories it supports, check if the
        # current analysis is of a supported category. Skip the plugin
        # otherwise.
        if plugin_class.CATEGORY:
            if ctx.analysis.category not in plugin_class.CATEGORY:
                continue

        try:
            instance = plugin_class(ctx, *args, **kwargs)
            instance.init()
            instances.append(instance)
        except DisablePluginError as e:
            ctx.log.warning(
                "Plugin usage disabled during initialization",
                plugin_class=plugin_class, error=e
            )
            continue
        except Exception as e:
            raise PluginError(
                f"Failed to initialize plugin: {plugin_class}. {e}"
            ).with_traceback(e.__traceback__)

    instances.sort(key=lambda plugin: plugin.ORDER)

    return instances

def run_plugin_cleanup(plugin_instances, ctx):
    for instance in plugin_instances:
        try:
            instance.cleanup()
        except Exception as e:
            ctx.log.exception(
                "Plugin cleanup failure", plugin=instance, error=e
            )

def _run_processing_instances(instances, ctx):
    for instance in instances:
        name = instance.__class__.__name__

        ctx.log.debug(
            "Running processing plugin.",  plugin=name, stage=ctx.stage
        )

        try:
            data = instance.start()
        except CancelProcessing as e:
            raise CancelProcessing(
                f"Analysis {ctx.analysis.id} {ctx.stage} processing cancelled "
                f"by plugin: {name}. Reason: {e}"
            )

        except Exception as e:
            raise PluginError(
                f"Failed to run plugin {name}. {e}"
            ).with_traceback(e.__traceback__)

        if data is not None and instance.KEY:
            try:
                ctx.result.store(instance.KEY, data)
            except KeyError:
                raise PluginWorkerError(
                    f"Plugin {name} tried to overwrite results. Key "
                    f"{instance.KEY}"
                )

def _handle_processing(processing_classes, ctx):
    try:
        processing_instances = make_plugin_instances(processing_classes, ctx)
    except PluginError as e:
        ctx.set_failed()
        ctx.errtracker.fatal_exception(e)
        ctx.log.exception(
            "Processing cancelled. Failure during processing plugin "
            "initialization", error=e
        )
        return False

    try:
        _run_processing_instances(processing_instances, ctx)
    except CancelProcessing as e:
        ctx.set_failed()
        ctx.log.error("Processing cancelled", error=e)
        ctx.errtracker.fatal_exception(e)
        return False
    except Exception as e:
        ctx.set_failed()
        ctx.errtracker.fatal_exception(e)
        ctx.log.exception(
            "Failure during processing", error=e
        )
        return False

    finally:
        run_plugin_cleanup(processing_instances, ctx)

    return True

def _run_reporting_instances(instances, ctx):
    for instance in instances:
        name = instance.__class__.__name__
        stage_handler = instance.handlers.get(ctx.stage)
        if not stage_handler:
            continue

        ctx.log.debug(
            "Running reporting plugin.",  plugin=name, stage=ctx.stage
        )
        try:
            stage_handler()
        except CancelReporting:
            raise
        except Exception as e:
            raise PluginError(
                f"Failed to run reporting plugin: {name} "
                f"({ctx.stage}). {e}"
            ).with_traceback(e.__traceback__)

def _handle_reporting(reporting_classes, ctx):
    try:
        reporting_instances = make_plugin_instances(reporting_classes, ctx)
    except PluginError as e:
        ctx.set_failed()
        ctx.errtracker.fatal_exception(e)
        ctx.log.exception(
            "Reporting cancelled. Failure during processing plugin "
            "initialization", error=e
        )
        return False

    try:
        _run_reporting_instances(reporting_instances, ctx)
    except CancelReporting as e:
        ctx.set_failed()
        ctx.analysisctx.log.error("Reporting cancelled", error=e)
        ctx.analysisctx.errtracker.fatal_error(e)
        return False
    except Exception as e:
        ctx.set_failed()
        ctx.errtracker.fatal_exception(e)
        ctx.log.exception("Failure during reporting", error=e)
        return False

    finally:
        run_plugin_cleanup(reporting_instances, ctx)

    return True

class PreProcessingRunner:

    def __init__(self, analysis_context, processing_classes,
                 reporting_classes):
        self.analysisctx = analysis_context
        self.processing_classes = processing_classes
        self.reporting_classes = reporting_classes

    @classmethod
    def init_once(cls):
        TTPTracker.init_once(
            attack_json_path=Paths.signatures("mitreattack", "attack.json")
        )
        init_safelist_db()

    def start(self):
        if not _handle_processing(self.processing_classes, self.analysisctx):
            return

        if not _handle_reporting(self.reporting_classes, self.analysisctx):
            return

        self.analysisctx.set_completed()

def make_event_consumper_map(event_user_instances):

    consumer_map = {}
    for user in event_user_instances:
        for event_type in user.event_types:
            userlist = consumer_map.setdefault(event_type, [])
            userlist.append(user)

    for userlist in consumer_map.values():
        userlist.sort(key=lambda user: user.ORDER)

    return consumer_map


class PostProcessingRunner:

    def __init__(self, task_context, event_consumer_classes,
                 reporting_classes, processing_classes):
        self.taskctx = task_context
        self._consumers = self._init_consumers(event_consumer_classes)
        self._processing_classes = processing_classes
        self._reporting_classes = reporting_classes
        self.completed = False

    @classmethod
    def init_once(cls):
        TTPTracker.init_once(
            attack_json_path=Paths.signatures("mitreattack", "attack.json")
        )
        init_safelist_db()

    def _init_consumers(self, consumer_classes):
        instances = []
        for consumer_class in consumer_classes:
            try:
                instance = consumer_class(self.taskctx)
                instance.init()
                instances.append(instance)
            except Exception as e:
                self.taskctx.log.exception(
                    "Failed to initialize event consumer plugin",
                    plugin=consumer_class, error=e
                )
        return instances

    def _read_events(self):
        consumer_map = make_event_consumper_map(self._consumers)

        self.taskctx.log.debug(
            "Using event consumers.", event_consumers=self._consumers
        )
        reader = NormalizedEventReader(self.taskctx)

        # All events from all logs in logs/ will be received here.
        for event in reader.read_events():

            # Hand each event to the consumer/user of this event. The
            # map of consumers must already be sorted by event and the
            # consumer instances by their order attribute.
            for consumer in consumer_map.get(event.kind, []):
                consumer.use_event(event)

    def start(self):
        try:
            self._read_events()

            for consumer in self._consumers:
                consumer.finalize()
        except Exception as e:
            self.taskctx.log.exception(
                "Fatal error during event usage", error=e
            )
            self.taskctx.errtracker.fatal_exception(e)
            self.taskctx.set_failed()
            return
        finally:
            run_plugin_cleanup(self._consumers, self.taskctx)

        # Other modules such as dropped file users, memdump stuff, etc.
        if not _handle_processing(self._processing_classes, self.taskctx):
            return

        if not _handle_reporting(self._reporting_classes, self.taskctx):
            return

        self.taskctx.set_completed()
