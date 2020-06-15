# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import threading
import time
import queue
import socket
import json
import tempfile
import shutil
import os

from cuckoo.common.ipc import UnixSocketServer, ReaderWriter
from cuckoo.common.storage import TaskPaths, Paths
from cuckoo.common.config import cfg

from cuckoo.machineries.helpers import MachineStates, Machine
from cuckoo.machineries import errors

class MachineryManagerError(Exception):
    pass

class MachineDoesNotExistError(MachineryManagerError):
    pass

# Machine object instances mapping to their machine name. 'machine tracker'
# Is used to track if a machine is available.
_machines = {}

# This lock must be acquired when making any changes to the machines tracker
# or any of its members.
_machines_lock = threading.RLock()

# A name->instance mapping of all loaded machinery modules
_machineries = {}

# Is set to True if machine is disabled, its state changes, or is (un)locked.
# Must be true by default so a dump is created on startup of the MsgHandler.
_machines_updated = True

def _set_machines_updated():
    global _machines_updated
    _machines_updated = True

def _clear_machines_updated():
    global _machines_updated
    _machines_updated = False

def read_machines_dump(path):
    loaded = {}
    with open(path, "r") as fp:
        machines = json.load(fp)

    for name, machine_dict in machines.items():
        machine = Machine.from_dict(machine_dict)
        loaded[name] = machine

    return loaded

def set_machines_dump(dump):
    global _machines
    _machines = dump

def load_machineries(machinery_classes, machine_states={}):
    """Creates instances of each given machinery class, initializes the
    instances, and loads their machines from their configuration files.

    machinery_classes: a list of imported machinery classes
    machine_states: (Optional) a name:machine_obj dict returned by
    read_machines_dump. Used to restore machine states from previous runs
    to machines that are still used. See cuckoo.machineries.helpers.Machine
    for information about what states are restored.
    """
    for machinery_class in machinery_classes:
        machine_conf = cfg(machinery_class.name, subpkg="machineries")

        print(f"Loading machinery '{machinery_class.name}' and its machines.")
        try:
            machinery = machinery_class(machine_conf)
            machinery.init()
            machinery.load_machines()
        except errors.MachineryError as e:
            raise MachineryManagerError(
                f"Loading of machinery module {machinery.name} failed. {e}"
            )

        for machine in machinery.list_machines():
            if machine.name in _machines:
                raise MachineryManagerError(
                    f"Machine name {machine.name} of {machinery_class.name} "
                    f"is not unique. It already exists "
                    f"in {_machines[machine.name].machinery.name}"
                )

            # Load state information from a machine obj loaded from a
            # machinestates dump of a previous run.
            dumped_machine = machine_states.get(machine.name)
            if dumped_machine:
                machine.load_stored_states(dumped_machine)

            _machines[machine.name] = machine

        _machineries[machinery.name] = machinery

    print(f"Loaded {len(_machines)} analysis machines")

def _dump_machines_info(path):
    """Dump the json version of each loaded machine (_machines) to the given
    path"""
    dump = {}
    for name, machine in _machines.items():
        dump[name] = machine.to_dict()

    # First write to a tmp file and after that perform a move to ensure the
    # operation of replacing the machines json is atomic. This is required
    # to prevent the machine info dump from ever being empty.
    fd, tmppath = tempfile.mkstemp()
    with os.fdopen(fd, "w") as fp:
        json.dump(dump, fp)

    shutil.move(tmppath, path)

def find(platform="", platform_version="", tags=set()):
    """Find any machine that matches the given platform, version and
    has the given tags."""
    machines = _machines
    if not machines:
        return None

    if platform:
        machines = find_platform(
            machines, platform, platform_version
        )
        if not machines:
            return None

    if tags:
        machines = find_tags(machines, tags)
        if not machines:
            return None

    return machines[0]

def find_available(name="", platform="", platform_version="", tags=set()):
    """Find an available machine by name or platform, os_version, and tags.
    return None if no available machine is found."""
    if name:
        machine = get_by_name(name)
        if not machine.available:
            return None

        return machine

    machines = get_available()
    if not machines:
        return None

    if platform:
        machines = find_platform(
            machines, platform, platform_version
        )
        if not machines:
            return None

    if tags:
        machines = find_tags(machines, tags)
        if not machines:
            return None

    return machines[0]

def get_available():
    """Return a list of all machines that are available for analysis tasks"""
    available = []
    for machine in _machines.values():
        if machine.available:
            available.append(machine)

    return available


def get_by_name(name):
    """Return the machine that matches the machine name.
    Raises MachineDoesNotExistError if the machine is not found."""
    try:
        return _machines[name]
    except KeyError:
        raise MachineDoesNotExistError(
            f"Machine with name {name} does not exist."
        )

def find_platform(find_in, platform, version=""):
    """Find all machines with the specified platform and version in t
    he dictionary of name:machines given."""
    matches = []
    for _, machine in find_in.items():
        if machine.platform == platform:
            if version and machine.platform_version != version:
                continue

            matches.append(machine)

    return matches

def find_tags(find_in, tags):
    """Find all machines that have the specified tags in the dictionary
    of name:machines given. Tags must be a set."""
    if not isinstance(tags, set):
        if isinstance(tags, (list, tuple)):
            tags = set(tags)

        raise TypeError(f"tags must be a set of strings. Not {type(tags)}")

    matches = []
    for _, machine in find_in.items():
        if tags.issubset(machine.tags):
            matches.append(machine)

    return matches

def acquire_available(task_id, name="", platform="",
                      platform_version="", tags=set()):
    """Find and lock a machine for task_id that matches the given name or
    platform, os_version, and has the given tags."""
    with _machines_lock:
        machine = find_available(
            name, platform, platform_version, tags
        )

        if not machine:
            return None

        _lock(machine, task_id)
        return machine

def _unlock(machine):
    """Unlock the given machine to put it back in the pool of available
    machines"""
    with _machines_lock:
        if not machine.locked:
            raise MachineryManagerError(
                f"Cannot unlock machine {machine.name}. Machine is not locked."
            )

        machine.clear_lock()
    _set_machines_updated()

def _lock(machine, task_id):
    """Lock the given machine for the given task_id. This makes the machine
    unavailable for acquiring."""
    with _machines_lock:
        if not machine.available:
            raise MachineryManagerError(
                f"Machine {machine.name} is unavailable and cannot be locked. "
                f"{machine.unavailable_reason}"
            )

        machine.lock(task_id)
    _set_machines_updated()

def _mark_disabled(machine, reason):
    """Mark the machine as disabled. Causing it to no longer be available.
    Should be used if machines reach an unexpected state."""
    machine.disable(reason)
    _set_state(machine, MachineStates.ERROR)
    _set_machines_updated()

def _set_state(machine, state):
    """Set the given machine to the given state"""
    machine.state = state
    _set_machines_updated()

# These call the machines underlying machinery implementation of the called
# method. All of these cause the state to change. This change can take a while.
# We therefore return the expected state, a maximum waiting time, and a
# potential handler function that can be called if the timeout expires.
def stop(machine):
    """Stop the given machine"""
    machine.machinery.stop(machine)
    return MachineStates.POWEROFF, 60, None

def acpi_stop(machine):
    """Stop the machine using an ACPI signal. Normal stop is called when the
     timeout of 120 seconds expires.
    """
    machine.machinery.acpi_stop(machine)
    # Call the stop function if stop takes longer than the timeout.
    return MachineStates.POWEROFF, 120, stop

def restore_start(machine):
    """Restore the machine to its configured snapshot and start the machine"""
    machine.machinery.restore_start(machine)
    return MachineStates.RUNNING, 60, None

def norestore_start(machine):
    """Start the machine without restoring a snapshot"""
    machine.machinery.norestore_start(machine)
    return MachineStates.RUNNING, 60, None

def dump_memory(machine):
    """Create a memory dump for the given running machine in the task folder
    of the task that has currently locked the machine."""
    machine.machinery.dump_memory(
        machine, TaskPaths.memory_dump(machine.task_id)
    )
    return MachineStates.RUNNING, 60, None

def machine_state(machine):
    """Return a normalized machine state of the given machine."""
    return machine.machinery.state(machine)

def shutdown(machinery):
    """Shutdown all machines of the given machinery module"""
    machinery.shutdown()

def shutdown_all():
    """Shutdown the machines of all loaded machinery modules"""
    if _machineries:
        for name, module in _machineries.items():
            print(f"Shutting down machinery: {name}")
            shutdown(module)

class _MachineryMessages:

    @staticmethod
    def success(msg_id):
        return {"success": True, "msg_id": msg_id}

    @staticmethod
    def fail(msg_id):
        return {"success": False, "msg_id": msg_id}

    @staticmethod
    def invalid_msg(msg_id, reason):
        return {
            "success": False,
            "msg_id": msg_id,
            "reason": reason
        }

class MachineryWorker(threading.Thread):
    """Retrieves a WorkTracker from work_queue and runs it. Running
    it must cause the 'action' function to return an expected state,
    timeout in seconds, and an optional timeout action function that
    is called if the timeout expires.

    After the action function returns, the WorkerTracker instance is added to
    the state_waiters list. Before running a new work action, the
    MachineryWorker thread checks that state/progress of all entries
    in the state_waiters list.

    A machine is disabled if a timeout for a WorkTracker has been reached or
    an unexpected state is reached.
    Unexpected meaning an error state or unhandled state. Handled states are
    located in a machinery module's statemapping attribute.
    """

    def __init__(self, work_queue, state_waiters, waiter_lock):
        super().__init__()

        self._work_queue = work_queue
        self._state_waiters = state_waiters
        self._waiter_lock = waiter_lock
        self.do_run = True

    def stop(self):
        self.do_run = False

    def handle_waiters(self):
        if not self._waiter_lock.acquire(timeout=0.1):
            return

        try:
            for work in self._state_waiters[:]:
                print(f"Checking state for {work}")
                try:
                    state = machine_state(work.machine)
                except errors.MachineryUnhandledStateError as e:
                    print(
                        f"Unhandled machine state for {work.machine.name}. "
                        f"Disabling machine. {e}"
                    )
                    work.work_failed()
                    _mark_disabled(work.machine, str(e))

                    # Remove this work tracker from state waiting work trackers
                    # as we disabled the machine
                    work.stop_wait()
                    continue

                if state == work.expected_state:
                    print(
                        f"Updating state for {work.machine.name} to "
                        f"{work.expected_state}"
                    )
                    _set_state(work.machine, work.expected_state)
                    work.work_success()
                elif state == MachineStates.ERROR:
                    print(
                        f"Machine {work.machine.name} has an error state. "
                        f"Disabling machine"
                    )
                    work.work_failed()
                    _mark_disabled(work.machine, "Machine has error state")

                elif not work.timeout_reached():
                    # Timeout not reached. Continue with other state waiters.
                    continue
                else:
                    if work.has_fallback():
                        work.fall_back()
                    else:
                        err = f"Waiting for machine {work.machine.name} to " \
                              f"reach state {work.expected_state} exceeded " \
                              f"timeout. Disabling machine."
                        print(err)
                        work.work_failed()
                        _mark_disabled(work.machine, err)

                work.stop_wait()
        finally:
            self._waiter_lock.release()

    def run(self):
        while self.do_run:
            self.handle_waiters()

            work = self._work_queue.get_work()
            if not work:
                time.sleep(1)
                continue

            print(f"Performing work: {work}")

            try:
                work.run_work()
                work.start_wait()
            except NotImplementedError as e:
                print(
                    f"Machinery {work.machine.machinery.name} does not support"
                    f" work of type: {work.work_func}. {e}"
                )
                work.work_failed()

            except errors.MachineStateReachedError as e:
                # Machine already has the state the executed work should put
                # it in. Log as warning for now. These errors should only occur
                # when stopping a machine, not when starting.
                print(e)
                work.work_success()

            except errors.MachineUnexpectedStateError as e:
                # TODO add 'fixes' for specific unexpected states? Do we want
                # to stop and restore a machine if a user has left it running?
                # Or is this fully up to the user?
                print(
                    f"'{work.machine.machinery.name}' machine "
                    f"'{work.machine.name}' Unexpected machine state. {e}. "
                    f"Disabling machine."
                )
                _mark_disabled(work.machine, str(e))
                work.work_failed()

            except errors.MachineryUnhandledStateError as e:
                print(
                    f"{work.machine.machinery.name} machine "
                    f"'{work.machine.name}' has an unknown/unhandled state. "
                    f"Disabling machine. {e}"
                )
                _mark_disabled(work.machine, str(e))
                work.work_failed()

            except errors.MachineryError as e:
                print(
                    f"{work.machine.machinery.name} machine "
                    f"{work.machine.name} unhandled error. "
                    f"Disabling machine. {e}"
                )
                _mark_disabled(work.machine, str(e))
                work.work_failed()

            except Exception as e:
                print(
                    f"Unhandled error in machinery "
                    f"'{work.machine.machinery.name}' when performing "
                    f"action {work.work_func} for machine "
                    f"{work.machine.name}. {e}"
                )
                work.work_failed()
                # TODO mark this fatal error somewhere, so that it is clear
                # this happened.
                raise

class WorkTracker:

    def __init__(self, func, machine, readerwriter, msg_id, machinerymngr):
        self.work_func = func
        self.machine = machine
        self.readerwriter = readerwriter
        self.msg_id = msg_id
        self.machinerymngr = machinerymngr

        # Set by return values of the executed work
        self.expected_state = ""
        self.timeout = 0
        self.fallback_func = None

        # Set when wait starts
        self.waited = 0
        self.since = 0

    def lock_work(self):
        """Lock the machine action lock, so that no other queued
        actions for this machine can run until this action has released
        the lock"""
        return self.machine.action_lock.acquire(blocking=False)

    def unlock_work(self):
        """Release the action lock so that other queued work can acquire it
        and run its work for the machine"""
        self.machine.action_lock.release()

    def work_failed(self):
        self.unlock_work()
        self.machinerymngr.queue_response(
            self.readerwriter, _MachineryMessages.fail(self.msg_id)
        )

    def work_success(self):
        self.unlock_work()
        self.machinerymngr.queue_response(
            self.readerwriter, _MachineryMessages.success(self.msg_id)
        )

    def run_work(self):
        self.expected_state, self.timeout, self.fallback_func = self.work_func(
            self.machine
        )

    def has_fallback(self):
        return self.fallback_func is not None

    def requeue(self):
        """Creates a new entry in the msg handler work queue of the current
        work. Can be used if the work cannot be performed for some reason"""
        self.machinerymngr.work_queue.add_work(
            self.work_func, self.machine, self.readerwriter, self.msg_id,
            self.machinerymngr
        )

    def fall_back(self):
        """Queue a work instance of the fallback function in the work queue"""
        self.machinerymngr.work_queue.add_work(
            self.fallback_func, self.machine, self.readerwriter, self.msg_id,
            self.machinerymngr
        )

    def start_wait(self):
        """Adds this object to the MachineryManager instance state_waiters
        list."""
        self.since = time.time()
        self.machinerymngr.state_waiters.append(self)

    def stop_wait(self):
        """Remove this object from the MachineryManager instance state_waiters
        list."""
        self.machinerymngr.state_waiters.remove(self)

    def timeout_reached(self):
        waited = time.time() - self.since

        # If the system time changed or the check is quick, the
        # waiting duration can be less than a second.
        # Set it to 1 second as a minimum
        if waited < 0:
            waited = 1

        self.waited += waited
        if waited >= self.timeout:
            return True
        return False


class _WorkQueue:

    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()

    def add_work(self, work_action, machine, readerwriter, msg_id, msghandler):
        self._queue.append(
            WorkTracker(work_action, machine, readerwriter, msg_id, msghandler)
        )

    def get_work(self):
        """Only returns a work instance if the machine for this work is not
        currently being used in another work instance. Returns None if
        no work is available or can be performed.

        A return work instance MUST be released by calling its work_success
        or work_fail function."""
        ignore = []
        with self._lock:
            for work in self._queue[:]:
                if work.machine.name in ignore:
                    continue

                # If the machine is locked, ignore any other work for it
                # that may be in the queue to keep the execution order FIFO.
                if not work.lock_work():
                    ignore.append(work.machine.name)
                    continue

                self._queue.remove(work)
                return work

        return None

class MachineryManager(UnixSocketServer):
    """The Machinery manager accepts connections and reads message from a
    client. These messages must contain an 'action' and machine name
    for which to perform this action. The action is anything that performs
    an action on/using the specified machine.

    Supported actions are listed in 'machinery_worker_actions'.

    For each action, a WorkTracker is created. The trackers are queued in a
    work queue. Work is retrieved from the work queue and executed by
    MachineryWorker threads. The work_queue, state_waiters, and waiter_lock
    are shared amount all MachineryWorker threads.

    Each WorkTracker contains a ReaderWriter with an underlying socket
    that is connected to the client requesting the action. When an action
    has been executed and has either succeeded or fail, a response is queued
    in the MachineryManager responses queue by calling .work_success()
    or work_fail() on a WorkTracker.

    Starting the MachineryManager automatically starts NUM_MACHINERY_WORKERS
    of MachineryWorker threads.
    """

    machinery_worker_actions = {
        "restore_start": restore_start,
        "norestore_start": norestore_start,
        "stop": stop,
        "acpi_stop": acpi_stop
    }

    # TODO read number of MachineryWorkers from a configuration file?
    NUM_MACHINERY_WORKERS = 2

    def __init__(self, manager_sock_path):
        super().__init__(manager_sock_path)

        self.workers = []

        # These are passed to worker threads
        self.state_waiters = []
        self.waiter_lock = threading.Lock()

        self.work_queue = _WorkQueue()
        self.responses = queue.Queue()

    def start(self):

        for _ in range(self.NUM_MACHINERY_WORKERS):
            worker = MachineryWorker(
                self.work_queue, self.state_waiters, self.waiter_lock
            )
            self.workers.append(worker)
            worker.start()

        self.create_socket()
        self.start_accepting(select_timeout=1)

    def stop(self):
        if not self.do_run and not self.workers:
            return

        super().stop()
        for worker in self.workers:
            worker.stop()

        self.cleanup()

    def handle_connection(self, sock, addr):
        self.track(sock, ReaderWriter(sock))

    def queue_response(self, readerwriter, response, close=False):
        self.responses.put((readerwriter, response, close))

    def timeout_action(self):
        while not self.responses.empty():
            try:
                readerwriter, response, close = self.responses.get(block=False)
            except queue.Empty:
                break

            try:
                readerwriter.send_json_message(response)
            except socket.error as e:
                print(f"Failed to send response: {e}")
                self.untrack(readerwriter.sock)
                continue

            if close:
                self.untrack(readerwriter.sock)

        # If any machines were updated, make a json dump to disk.
        if _machines_updated:
            _dump_machines_info(Paths.machinestates())
            _clear_machines_updated()

    def handle_message(self, sock, msg):
        msg_id = str(msg.get("msg_id"))
        action = msg.get("action")
        machine_name = msg.get("machine")

        readerwriter = self.socks_readers[sock]

        # If no action or machine is given, send error and cleanup sock
        if not msg_id or not action or not machine_name:
            self.queue_response(
                readerwriter,
                _MachineryMessages.invalid_msg(
                    msg_id=None,
                    reason="Missing msg_id, action or machine name"
                ), close=True
            )
            return

        try:
            machine = get_by_name(machine_name)
        except MachineDoesNotExistError:
            # Send error if the machine does not exist.
            self.queue_response(
                readerwriter,
                _MachineryMessages.invalid_msg(
                    msg_id, reason="No such machine"
                )
            )
            return

        worker_action = self.machinery_worker_actions.get(action)

        # If the action does not exist, send error and cleanup sock
        if not worker_action:
            self.queue_response(
                readerwriter,
                _MachineryMessages.invalid_msg(
                    msg_id, reason="No such action"
                ),
                close=True
            )
            return

        self.work_queue.add_work(
            worker_action, machine, readerwriter, msg_id, self
        )
