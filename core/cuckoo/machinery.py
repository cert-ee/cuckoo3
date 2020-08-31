# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import queue
import socket
import threading
import time

from cuckoo.common import machines
from cuckoo.common.config import cfg
from cuckoo.common.ipc import UnixSocketServer, ReaderWriter
from cuckoo.common.log import CuckooGlobalLogger
from cuckoo.common.storage import TaskPaths, Paths
from cuckoo.machineries import errors

class MachineryManagerError(Exception):
    pass

class MachineDoesNotExistError(MachineryManagerError):
    pass

log = CuckooGlobalLogger(__name__)

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

def load_machineries(machinery_classes, machine_states={}):
    """Creates instances of each given machinery class, initializes the
    instances, and loads their machines from their configuration files.

    machinery_classes: a list of imported machinery classes
    machine_states: (Optional) a name:machine_obj dict returned by
    read_machines_dump. Used to restore machine states from previous runs
    to machines that are still used. See cuckoo.common.machines.Machine
    for information about what states are restored.
    """
    for machinery_class in machinery_classes:
        machine_conf = cfg(machinery_class.name, subpkg="machineries")

        log.debug(
            f"Loading machinery and its machines.",
            machinery=machinery_class.name
        )
        try:
            machinery_class.verify_dependencies()
            machinery = machinery_class(machine_conf)
            machinery.init()
            machinery.load_machines()
        except errors.MachineryError as e:
            raise MachineryManagerError(
                f"Loading of machinery module {machinery_class.name} "
                f"failed. {e}"
            )

        for machine in machinery.list_machines():
            try:
                existing_machine = machines.get_by_name(machine.name)
                raise MachineryManagerError(
                    f"Machine name {machine.name} of {machinery_class.name} "
                    f"is not unique. It already exists "
                    f"in {existing_machine.machinery.name}"
                )
            except KeyError:
                pass

            # Load state information from a machine obj loaded from a
            # machinestates dump of a previous run.
            dumped_machine = machine_states.get(machine.name)
            if dumped_machine:
                machine.load_stored_states(dumped_machine)

            machines.add_machine(machine)
            log.debug(
                "Machinery loaded machine.",
                machinery=machinery.name, machine=machine.name
            )

        _machineries[machinery.name] = machinery

    log.info(f"Loaded analysis machines", amount=machines.count())

def acquire_available(task_id, name="", platform="", os_version="",
                      tags=set()):
    """Find and lock a machine for task_id that matches the given name or
    platform, os_version, and has the given tags."""
    with _machines_lock:
        machine = machines.find_available(
            name, platform, os_version, tags
        )

        if not machine:
            return None

        _lock(machine, task_id)
        return machine

def unlock(machine):
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
    _set_state(machine, machines.States.ERROR)
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
    try:
        machine.machinery.stop(machine)
    finally:
        try:
            stop_netcapture(machine)
        except errors.MachineNetCaptureError as e:
            log.error(e)

    return machines.States.POWEROFF, 60, None

def acpi_stop(machine):
    """Stop the machine using an ACPI signal. Normal stop is called when the
     timeout of 120 seconds expires.
    """
    try:
        machine.machinery.acpi_stop(machine)
    finally:
        try:
            stop_netcapture(machine)
        except errors.MachineNetCaptureError as e:
            log.error(e)
    # Call the stop function if stop takes longer than the timeout.
    return machines.States.POWEROFF, 120, stop

def restore_start(machine):
    """Restore the machine to its configured snapshot and start the machine"""
    try:
        start_netcapture(machine)
    except errors.MachineNetCaptureError as e:
        log.error(e)

    try:
        machine.machinery.restore_start(machine)
    except errors.MachineryError:
        try:
            stop_netcapture(machine)
        except errors.MachineNetCaptureError as e:
            log.error(e)
        raise

    return machines.States.RUNNING, 60, stop_netcapture

def norestore_start(machine):
    """Start the machine without restoring a snapshot"""
    try:
        start_netcapture(machine)
    except errors.MachineNetCaptureError as e:
        log.error(e)

    try:
        machine.machinery.norestore_start(machine)
    except errors.MachineryError:
        try:
            stop_netcapture(machine)
        except errors.MachineNetCaptureError as e:
            log.error(e)
        raise

    return machines.States.RUNNING, 60, stop_netcapture

def start_netcapture(machine):
    """Ask the machinery to start network capture for the given machine"""
    if not machine.locked_by:
        return 

    ignore_ip_ports = [
        (cfg("cuckoo", "resultserver", "listen_ip"),
         cfg("cuckoo", "resultserver", "listen_port")),
        (machine.ip, 8000)
    ]
    machine.machinery.start_netcapture(
        machine, TaskPaths.pcap(machine.locked_by),
        ignore_ip_ports=ignore_ip_ports
    )
    return None, 60, None

def stop_netcapture(machine):
    """Stop the network capture for a machine"""
    machine.machinery.stop_netcapture(machine)
    return None, 60, None

def dump_memory(machine):
    """Create a memory dump for the given running machine in the task folder
    of the task that has currently locked the machine."""
    machine.machinery.dump_memory(
        machine, TaskPaths.memory_dump(machine.locked_by)
    )
    return machines.States.RUNNING, 60, None

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
            log.info("Shutting down machinery.", machinery=name)
            shutdown(module)

class _MachineryMessages:

    @staticmethod
    def success():
        return {"success": True}

    @staticmethod
    def fail():
        return {"success": False}

    @staticmethod
    def invalid_msg(reason):
        return {
            "success": False,
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
                try:
                    state = machine_state(work.machine)
                except errors.MachineryUnhandledStateError as e:
                    log.error(
                        "Unhandled machine state. Disabling machine.",
                        machine=work.machine.name, error=e
                    )
                    work.work_failed()
                    _mark_disabled(work.machine, str(e))

                    # Remove this work tracker from state waiting work trackers
                    # as we disabled the machine
                    work.stop_wait()
                    continue

                if state == work.expected_state:
                    log.debug(
                        "Updating machine state.",
                        machine=work.machine.name, newstate=work.expected_state
                    )

                    _set_state(work.machine, work.expected_state)
                    work.work_success()
                elif state == machines.States.ERROR:
                    log.error(
                        "Machinery returned error state for machine. "
                        "Disabling machine.", machine=work.machine.name
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
                        log.error(
                            "Timeout reached while waiting for machine to "
                            "reach expected state. Disabling machine.",
                            machine=work.machine.name,
                            expected_state=work.expected_state,
                            actual_state=state
                        )

                        work.work_failed()
                        _mark_disabled(
                            work.machine,
                            f"Timeout reached while waiting for machine to "
                            f"reach state: {work.expected_state}. Actual "
                            f"state: {state}"
                        )

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

            try:
                work.run_work()

                if work.expects_state_change():
                    work.start_wait()
                else:
                    work.work_success()
            except NotImplementedError as e:
                log.error(
                    "Machinery does not support work type.",
                    machine=work.machine.name,
                    machinery=work.machine.machinery.name,
                    action=work.work_func
                )
                work.work_failed()

            except errors.MachineStateReachedError as e:
                # Machine already has the state the executed work should put
                # it in. Log as warning for now. These errors should only occur
                # when stopping a machine, not when starting.
                log.debug(
                    "Machine already has expected state on action start.",
                    machine=work.machine.name,
                    expected_state=work.expected_state,
                    action=work.work_func
                )
                work.work_success()

            except errors.MachineUnexpectedStateError as e:
                log.error(
                    "Machine has unexpected state. Disabling machine.",
                    machine=work.machine.name,
                    machinery=work.machine.machinery.name,
                    error=e
                )
                _mark_disabled(work.machine, str(e))
                work.work_failed()

            except errors.MachineryUnhandledStateError as e:
                log.error(
                    "Machine has an unknown/unhandled state. "
                    "Disabling machine", machine=work.machine.name,
                    machinery=work.machine.machinery.name, error=e
                )
                _mark_disabled(work.machine, str(e))
                work.work_failed()

            except errors.MachineryError as e:
                log.error(
                    "Machinery module error. Disabling machine.",
                    machine=work.machine.name,
                    machinery=work.machine.machinery.name, error=e
                )
                _mark_disabled(work.machine, str(e))
                work.work_failed()

            except Exception as e:
                log.exception(
                    "Unhandled error in machinery module.",
                    machine=work.machine.name,
                    machinery=work.machine.machinery.name,
                    action=work.work_func, error=e
                )

                work.work_failed()
                # TODO mark this fatal error somewhere, so that it is clear
                # this happened.
                raise

class WorkTracker:

    def __init__(self, func, machine, readerwriter, machinerymngr):
        self.work_func = func
        self.machine = machine
        self.readerwriter = readerwriter
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

    def expects_state_change(self):
        if self.expected_state:
            return True
        return False

    def unlock_work(self):
        """Release the action lock so that other queued work can acquire it
        and run its work for the machine"""
        self.machine.action_lock.release()

    def work_failed(self):
        self.unlock_work()
        self.machinerymngr.queue_response(
            self.readerwriter, _MachineryMessages.fail()
        )

    def work_success(self):
        self.unlock_work()
        self.machinerymngr.queue_response(
            self.readerwriter, _MachineryMessages.success()
        )

    def run_work(self):
        log.debug(
            "Starting work.", machine=self.machine.name,
            action=self.work_func
        )
        self.expected_state, self.timeout, self.fallback_func = self.work_func(
            self.machine
        )

    def has_fallback(self):
        return self.fallback_func is not None

    def requeue(self):
        """Creates a new entry in the msg handler work queue of the current
        work. Can be used if the work cannot be performed for some reason"""
        self.machinerymngr.work_queue.add_work(
            self.work_func, self.machine, self.readerwriter, self.machinerymngr
        )

    def fall_back(self):
        """Queue a work instance of the fallback function in the work queue"""
        self.machinerymngr.work_queue.add_work(
            self.fallback_func, self.machine, self.readerwriter,
            self.machinerymngr
        )

    def start_wait(self):
        """Adds this object to the MachineryManager instance state_waiters
        list."""
        self.since = time.monotonic()
        self.machinerymngr.state_waiters.append(self)

    def stop_wait(self):
        """Remove this object from the MachineryManager instance state_waiters
        list."""
        self.machinerymngr.state_waiters.remove(self)

    def timeout_reached(self):
        self.waited += time.monotonic() - self.since
        if self.waited >= self.timeout:
            return True
        return False


class _WorkQueue:

    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()

    def add_work(self, work_action, machine, readerwriter, msghandler):
        log.debug(
            "Machine action request", machine=machine.name, action=work_action
        )
        self._queue.append(
            WorkTracker(work_action, machine, readerwriter, msghandler)
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
                log.debug("Failed to send response.", error=e)
                self.untrack(readerwriter.sock)
                continue

            if close:
                self.untrack(readerwriter.sock)

        # If any machines were updated, make a json dump to disk.
        if _machines_updated:
            machines.dump_machines_info(Paths.machinestates())
            _clear_machines_updated()

    def handle_message(self, sock, msg):
        action = msg.get("action")
        machine_name = msg.get("machine")

        readerwriter = self.socks_readers[sock]

        # If no action or machine is given, send error and cleanup sock
        if not action or not machine_name:
            self.queue_response(
                readerwriter,
                _MachineryMessages.invalid_msg(
                    reason="Missing action or machine name"
                ), close=True
            )
            return

        try:
            machine = machines.get_by_name(machine_name)
        except KeyError as e:
            # Send error if the machine does not exist.
            self.queue_response(
                readerwriter,
                _MachineryMessages.invalid_msg(reason=str(e))
            )
            return

        worker_action = self.machinery_worker_actions.get(action)

        # If the action does not exist, send error and cleanup sock
        if not worker_action:
            self.queue_response(
                readerwriter,
                _MachineryMessages.invalid_msg(reason="No such action"),
                close=True
            )
            return

        self.work_queue.add_work(worker_action, machine, readerwriter, self)
