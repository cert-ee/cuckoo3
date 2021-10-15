# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import asyncio
from threading import Lock

from cuckoo.common.clients import (
    ClientError, NodeEventReader, ResultRetrieverClient
)
from cuckoo.common.importing import NodeWorkZipper, AnalysisImportError
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.node import NodeInfo
from cuckoo.common.storage import TaskPaths, UnixSocketPaths
from cuckoo.node.node import (
    NodeError, InfoStreamReceiver, NodeTaskStates, NodeMsgTypes
)

class NodeActionError(Exception):
    pass

class NodeUnavailableError(NodeActionError):
    pass

log = CuckooGlobalLogger(__name__)

class AssignedTasks:

    def __init__(self):
        self._taskid_startabletask = {}
        self._lock = Lock()
        self._history_lock = Lock()
        self._analysis_history = set()

    def in_history(self, analysis_id):
        with self._history_lock:
            return analysis_id in self._analysis_history

    def remove_history(self, analysis_id):
        with self._history_lock:
            self._analysis_history.discard(analysis_id)

    def have_task(self, task_id):
        return task_id in self._taskid_startabletask

    def track_assigned(self, startable_task):
        with self._lock:
            self._taskid_startabletask[startable_task.task.id] = startable_task

        with self._history_lock:
            self._analysis_history.add(startable_task.task.analysis_id)

    def get_assigned(self, task_id):
        with self._lock:
            return self._taskid_startabletask[task_id]

    def untrack_assigned(self, task_id):
        with self._lock:
            self._taskid_startabletask.pop(task_id)

    def requeue_all(self):
        """Untracks and requeues all tracked tasks. Returns the startable
        task objects for the task ids that have been requeued. These objects
        should no longer be used for anything else than reading their
        attributes."""
        tasks = []
        with self._lock:
            for task_id in list(self._taskid_startabletask.keys()):
                task = self._taskid_startabletask.pop(task_id)
                tasks.append(task)
                task.requeue()
                try:
                    task.close()
                except Exception as e:
                    log.exception(
                        "Failed to close started task context after cancel.",
                        task_id=task_id, error=e
                    )
        return tasks


class LocalStreamReceiver(InfoStreamReceiver):

    def __init__(self):
        self.node_client = None

    def set_client(self, localnodeclient):
        self.node_client = localnodeclient

    def task_state(self, task_id, state):
        if state == NodeTaskStates.TASK_FAILED:
            self.node_client.task_failed(task_id)
        elif state == NodeTaskStates.TASK_DONE:
            self.node_client.task_done(task_id)
        elif state == NodeTaskStates.TASK_RUNNING:
            pass
        else:
            log.error(
                "Unhandled task state update", task_id=task_id, state=state
            )

    def disabled_machine(self, machine_name, reason):
        log.warning(
            "Received machine disable event", machine=machine_name,
            reason=reason
        )
        try:
            machine = self.node_client.machines.get_by_name(machine_name)
        except KeyError:
            log.error(
                "Received machine disabled event for unknown machine",
                machine=machine_name, disable_reason=reason
            )
            return

        self.node_client.machines.mark_disabled(machine, reason)

class NodeClientLoop:

    def __init__(self, loop):
        self.loop = loop
        self._task_stopper = {}
        self._asynctasks = set()
        self._stopped = False

    async def _cancel_asynctasks(self):
        for task in list(self._asynctasks):
            try:
                stopper = self._task_stopper.pop(task, None)
                if stopper:
                    try:
                        await stopper()
                    except Exception as e:
                        log.exception(
                            "Exception in stopper for asynctask",
                            stopper=stopper, asynctask=task, error=e
                        )
            finally:
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    log.exception(
                        "Unexpected error during asyncio task cancel", error=e
                    )

    async def _stop(self):
        try:
            await self._cancel_asynctasks()
        finally:
            self.loop.stop()

    def _cleanup(self):
        try:
            self.loop.close()
        except Exception as e:
            log.exception(
                "Unexpected error when closing asyncio event loop", error=e
            )

    def stop(self):
        self._stopped = True
        asyncio.run_coroutine_threadsafe(self._stop(), self.loop)

    def newtask_threadsafe(self, coro, args=(), done_cb=None, stopper_cb=None):
        if self._stopped:
            log.debug(
                "New asynctask after loop stopped. Will never start",
                coro=coro, args=args
            )
            return

        asyncio.run_coroutine_threadsafe(
            self.newtask(
                coro, args=args, done_cb=done_cb, stopper_cb=stopper_cb
            ), self.loop
        )

    async def newtask(self, coro, args=(), done_cb=None, stopper_cb=None):
        if self._stopped:
            log.debug(
                "New asynctask after loop stopped. Will never start",
                coro=coro, args=args
            )
            return

        async_task = self.loop.create_task(coro(*args))
        self._asynctasks.add(async_task)
        if stopper_cb:
            self._task_stopper[async_task] = stopper_cb

        def _done_cb(task):
            try:
                exp = task.exception()
                if exp:
                    log.exception(
                        "Asyncio task ended in unexpected error",
                        error=exp, exc_info=exp
                    )
            except asyncio.CancelledError:
                pass

            try:
                if done_cb:
                    done_cb()
            finally:
                self._asynctasks.discard(task)
                self._task_stopper.pop(task, None)

        async_task.add_done_callback(_done_cb)

    def start(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            self._cleanup()

class NodeClient:

    @property
    def name(self):
        raise NotImplementedError

    @property
    def ready(self):
        raise NotImplementedError

    @property
    def info(self):
        raise NotImplementedError

    @property
    def routes(self):
        raise NotImplementedError

    @property
    def machines(self):
        raise NotImplementedError

    def task_failed(self, task_id):
        raise NotImplementedError

    def add_task(self, startable_task):
        raise NotImplementedError

    def delete_completed_analysis(self, analysis_id):
        pass

class RemoteNodeClient(NodeClient):

    def __init__(self, cuckooctx, nodeapi_client, loop_wrapper):
        self.ctx = cuckooctx
        self.client = nodeapi_client
        self.loop_wrapper = loop_wrapper
        self.assigned_tasks = AssignedTasks()
        self.events = None

        self._info = None
        self._events_open = False
        self._fatal_error = False
        self._resetting = False

    @property
    def name(self):
        return self.client.name

    @property
    def ready(self):
        return self._info and self._events_open and not self._fatal_error \
               and not self._resetting

    @property
    def machines(self):
        if not self._info:
            raise NodeActionError("Machines list not loaded")

        return self._info.machines_list

    @property
    def routes(self):
        if not self._info:
            raise NodeActionError("Available routes not loaded")

        return self._info.routes

    @property
    def info(self):
        if not self._info:
            raise NodeActionError("Node information not loaded")

        return self._info

    async def _handle_taskstate(self, task_id, state):
        log.debug("Received new task state", task_id=task_id, state=state)
        if state == NodeTaskStates.TASK_FAILED:
            await self.loop_wrapper.newtask(
                self._task_failed, args=(task_id, True)
            )
        elif state == NodeTaskStates.TASK_DONE:
            await self.loop_wrapper.newtask(
                self._task_done, args=(task_id,)
            )
        elif state == NodeTaskStates.TASK_RUNNING:
            pass
        else:
            log.error("Unhandled task state", state=state, task_id=task_id)

    async def _handle_disabled_machine(self, name, reason):
        log.warning(
            "Received machine disable event", node=self.name,
            machine=name, reason=reason
        )
        try:
            machine = self.machines.get_by_name(name)
        except KeyError:
            log.error(
                "Received machine disabled event for unknown machine",
                node=self.name, machine=name, disable_reason=reason
            )
            return

        self.machines.mark_disabled(machine, reason)

    async def _event_msg(self, msgdict):
        msgtype = msgdict.get("type")
        if msgtype == NodeMsgTypes.TASK_STATE:
            task_id = msgdict.get("task_id")
            state = msgdict.get("state")
            if not self.assigned_tasks.have_task(task_id):
                return

            await self._handle_taskstate(task_id, state)

        elif msgtype == NodeMsgTypes.MACHINE_DISABLED:
            name = msgdict.get("machine_name")
            reason = msgdict.get("reason", "")
            if not name:
                return

            await self._handle_disabled_machine(name, reason)
        else:
            log.error("Unhandled message type", msgtype=msgtype)
            return

    async def _nodereset_and_reopen(self):
        """Requeue all assigned tasks and re-init the node. Use only in case
        of event stream fail. This is meant to restore the node to a state
        where we can use it again."""
        log.warning(
            "Starting node reset. Node will be unavailable until this is "
            "complete.", node=self.name
        )
        self._resetting = True
        # First requeue all assigned tasks so that they can still be
        # scheduled to another node.
        log.info("Requeueing all tasks assigned to node", node=self.name)
        requeued = self.assigned_tasks.requeue_all()

        # Only re-open reader if the event reading client was created.
        # This won't be the cause when the remote node has the wrong state
        # when Cuckoo main starts.
        if self.events:
            log.debug("Trying to re-open event stream", node=self.name)
            # Reset event id counter and try to re-open the event stream. We
            # reset the counter because we do not care about missed events,
            # since we are performing a reset.
            self.events.reset_last_id()
            await self._reopen_eventreader()

        log.debug("Requesting remote node reset", node=self.name)
        # Ask the remote node to cancel all work and reset the states of
        # the machines to poweroff.
        try:
            await self.client.a_reset()
        except ClientError as e:
            log.error(
                "Failure during remote node reset request", node=self.name,
                error=e
            )
            raise NodeActionError(
                f"Failure during remote node reset request: {e}"
            )

        log.debug(
            "Deleting all cancelled analysis work on node", node=self.name
        )
        for task in requeued:
            try:
                await self.client.a_delete_analysis_work(task.task.analysis_id)
                self.assigned_tasks.remove_history(task.task.analysis_id)
            except ClientError as e:
                log.warning(
                    "Failure during deletion of analysis work",
                    node=self.name, error=e, task_id=task.task.analysis_id
                )

        # Create a new node info with the new available machines and routes
        # objects.
        log.debug(
            "Requesting available machine and routes for reset node",
            node=self.name
        )
        self.init()
        self._resetting = False

        log.info("Node reset completed", node=self.name)
        # Finally inform the nodes tracker that this node is ready to
        # be assigned tasks again.
        self.ctx.nodes.ready_cb(self)

    async def _reopen_eventreader(self):
        while not self.events.stopped:
            if self.events.opened:
                break

            try:
                await self.events.open()
                await self.loop_wrapper.newtask(
                    self.events.read_stream,
                    stopper_cb=self.events.stop_reading
                )
                break
            except ClientError as e:
                log.error(
                    "Failed to re-open event stream. Trying again in 10 "
                    "seconds", error=e, node=self.name
                )
                await asyncio.sleep(10, self.loop_wrapper.loop)

    async def _event_read_end(self):
        self._events_open = False
        log.error("Node event stream closed", node=self.name)
        self.ctx.nodes.notready_cb(self)
        if not self.events.stopped:
            await self.loop_wrapper.newtask(self._nodereset_and_reopen)

    def _event_conn_err(self, e):
        self._events_open = False
        log.error("Node event stream error", node=self.name, error=e)

    def _event_conn_opened(self):
        self._events_open = True
        log.debug("Node event stream opened", node=self.name)
        # Do not notify the node tracker that we are ready because
        # another handler is busy performing resetting steps. This handler
        # must tell the node tracker we are ready when it is done.
        if not self._resetting:
            self.ctx.nodes.ready_cb(self)

    async def start_reader(self):
        self.events = NodeEventReader(
            self.client, message_cb=self._event_msg,
            read_end_cb=self._event_read_end, conn_cb=self._event_conn_opened,
            connerr_cb=self._event_conn_err
        )

        try:
            await self.events.open()
        except ClientError as e:
            raise NodeActionError(f"Failed to open event reader. {e}")

        await self.loop_wrapper.newtask(
            self.events.read_stream, stopper_cb=self.events.stop_reading
        )

    def init(self):
        self._info = NodeInfo(
            name=self.name, version="",
            machines_list=self._retrieve_machine_list(),
            routes=self._retrieve_available_routes()
        )

    def _retrieve_machine_list(self):
        try:
            return self.client.machine_list()
        except ClientError as e:
            raise NodeActionError(f"Failed retrieving machine list: {e}")

    def _retrieve_available_routes(self):
        try:
            return self.client.available_routes()
        except ClientError as e:
            raise NodeActionError(f"Failed retrieving available routes: {e}")

    async def _start_task(self, startable_task):
        log.debug(
            "Asking node to start work for task",
            task_id=startable_task.task.id, node=self.name
        )
        try:
            await self.client.start_task(
                startable_task.task.id, startable_task.machine.name
            )
            log.debug(
                "Node has started task", task_id=startable_task.task.id,
                node=self.name
            )
        except ClientError as e:
            startable_task.log.error(
                "Failed to start remote task",
                task_id=startable_task.task.id, node=self.name,
                error=e
            )
            startable_task.errtracker.fatal_error(
                f"Failed to start remote task. {self.name}. {e}"
            )

            return False

        return True

    async def _upload_and_start(self, nodework, startable_task):
        log.debug(
            "Uploading task work to node", task_id=startable_task.task.id,
            node=self.name
        )
        with nodework:
            try:
                await self.client.upload_taskwork(nodework.path)
                log.debug(
                    "Upload task work complete",
                    task_id=startable_task.task.id, node=self.name
                )
            except ClientError as e:
                startable_task.log.error(
                    "Failed to upload work for task.",
                    task_id=startable_task.task.id, node=self.name,
                    error=e
                )
                startable_task.errtracker.fatal_error(
                    f"Failed to upload work to node. {self.name}. "
                    f"{e}"
                )
                return await self._task_failed(
                    startable_task.task.id, retrieve_result=False
                )
            finally:
                nodework.delete()

        if not await self._start_task(startable_task):
            return await self._task_failed(
                startable_task.task.id, retrieve_result=False
            )

    def add_task(self, startable_task):
        if not self.ready:
            raise NodeUnavailableError("Node not ready for usage")

        self.assigned_tasks.track_assigned(startable_task)
        try:
            nodework = NodeWorkZipper(
                startable_task.task.analysis_id, startable_task.task.id
            ).make_zip(TaskPaths.nodework_zip(startable_task.task.id))
        except AnalysisImportError as e:
            raise NodeActionError(f"Failed to create node work zip. {e}")

        log.debug(
            "Starting asyncio task for new task",
            task_id=startable_task.task.id, node=self.name
        )
        self.loop_wrapper.newtask_threadsafe(
            self._upload_and_start, args=(nodework, startable_task)
        )

    def task_failed(self, task_id):
        # This is only called by the scheduler in case of some fail during
        # assigning.
        self.loop_wrapper.newtask_threadsafe(
            self._task_failed, args=(task_id, False),
        )

    async def _retrieve_result(self, startable_task):
        log.debug(
            "Asking result retriever to get result",
            task_id=startable_task.task.id, node=self.name
        )
        try:
            await ResultRetrieverClient.retrieve_result(
                UnixSocketPaths.result_retriever(), startable_task.task.id,
                self.client.name
            )
        except ClientError as e:
            startable_task.log.error(
                "Failed to retrieve result for task.",
                task_id=startable_task.task.id, node=self.name,
                error=e
            )
            startable_task.errtracker.fatal_error(
                f"Failed to retrieve result {self.name}. "
                f"{e}"
            )
            return False

        return True

    async def _task_failed(self, task_id, retrieve_result=True):
        startable_task = self.assigned_tasks.get_assigned(task_id)
        startable_task.release_resources()
        if retrieve_result:
            await self._retrieve_result(startable_task)

        try:
            startable_task.close()
        except Exception as e:
            log.exception(
                "Failed to close started task context", task_id=task_id,
                error=e
            )
        finally:
            self.ctx.state_controller.task_failed(
                task_id=startable_task.task.id,
                analysis_id=startable_task.task.analysis_id
            )
            self.assigned_tasks.untrack_assigned(task_id)

    async def _task_done(self, task_id):
        startable_task = self.assigned_tasks.get_assigned(task_id)
        startable_task.release_resources()

        if not await self._retrieve_result(startable_task):
            return await self._task_failed(task_id, retrieve_result=False)

        try:
            startable_task.close()
        except Exception as e:
            log.exception(
                "Failed to close started task context", task_id=task_id,
                error=e
            )
        finally:
            self.ctx.state_controller.task_done(
                task_id=startable_task.task.id,
                analysis_id=startable_task.task.analysis_id
            )
            self.assigned_tasks.untrack_assigned(task_id)

    def delete_completed_analysis(self, analysis_id):
        if not self.assigned_tasks.in_history(analysis_id):
            return

        try:
            self.client.delete_analysis_work(analysis_id)
        except ClientError as e:
            log.warning(
                "Error while deleting analysis work on remote node",
                node=self.name, analysis_id=analysis_id, error=e
            )
            return

        self.assigned_tasks.remove_history(analysis_id)

class LocalNodeClient(NodeClient):

    def __init__(self, cuckooctx, localnode):
        self.ctx = cuckooctx
        self.node = localnode
        self._info = NodeInfo(
            name=self.name, version="",
            machines_list=localnode.ctx.machinery_manager.machines.copy(),
            routes=localnode.ctx.routes
        )
        self.assigned_tasks = AssignedTasks()
        self._lock = Lock()
        self.ctx.nodes.ready_cb(self)

    @property
    def name(self):
        return "local"

    @property
    def ready(self):
        return True

    @property
    def machines(self):
        return self._info.machines_list

    @property
    def routes(self):
        return self._info.routes

    @property
    def info(self):
        return self._info

    def add_task(self, startable_task):
        self.assigned_tasks.track_assigned(startable_task)
        with self._lock:
            try:
                self.node.add_work(
                    startable_task.task.id, startable_task.machine.name
                )
            except NodeError as e:
                raise NodeActionError(e)

    def task_failed(self, task_id):
        startable_task = self.assigned_tasks.get_assigned(task_id)
        startable_task.release_resources()
        try:
            startable_task.close()
        except Exception as e:
            log.exception(
                "Failed to close started task context", task_id=task_id,
                error=e
            )
        finally:
            self.ctx.state_controller.task_failed(
                task_id=startable_task.task.id,
                analysis_id=startable_task.task.analysis_id
            )
            self.assigned_tasks.untrack_assigned(task_id)

    def task_done(self, task_id):
        startable_task = self.assigned_tasks.get_assigned(task_id)
        startable_task.release_resources()
        try:
            startable_task.close()
        except Exception as e:
            log.exception(
                "Failed to close started task context", task_id=task_id,
                error=e
            )
        finally:
            self.ctx.state_controller.task_done(
                task_id=startable_task.task.id,
                analysis_id=startable_task.task.analysis_id
            )
            self.assigned_tasks.untrack_assigned(task_id)
