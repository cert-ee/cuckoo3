# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from .clients import MachineryManagerClient
from .storage import Paths

class TaskFlowError(Exception):
    pass

class TaskFlow:

    name = ""
    supports = []

    INTERVAL_CALL_WAIT = 1

    def __init__(self, machine, task, analysis, identification, agent,
                 result_ip, result_port):

        self.machine = machine
        self.task = task
        self.analysis = analysis
        self.identification = identification
        self.result_ip = result_ip
        self.result_port = result_port

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
