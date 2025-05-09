# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from .clients import MachineryManagerClient
from .storage import Paths


class TaskFlowError(Exception):
    pass


class TaskFlow:
    name = ""
    supports = []

    INTERVAL_CALL_WAIT = 1

    def __init__(self, machine, task, analysis, agent, resultserver, tasklog):
        self.machine = machine
        self.task = task
        self.analysis = analysis
        self.resultserver = resultserver
        self.log = tasklog

        self.agent = agent
        self.machinery_client = MachineryManagerClient(
            Paths.unix_socket("machinerymanager.sock")
        )

    def initialize(self):
        pass

    def start_machine(self):
        raise NotImplementedError

    def stop_machine(self):
        raise NotImplementedError

    def machine_online(self):
        raise NotImplementedError

    def call_at_interval(self):
        pass
