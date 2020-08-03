# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common.clients import ActionFailedError
from cuckoo.common.guest import find_stager, StagerError, PayloadExecFailed
from cuckoo.common.taskflow import TaskFlow, TaskFlowError

class StandardTask(TaskFlow):

    name = "standard"

    def start_machine(self):
        try:
            self.machinery_client.restore_start(
                self.machine.name, wait_response=True, timeout=120
            )
        except ActionFailedError as e:
            raise TaskFlowError(f"Failed to start machine: {e}")

    def stop_machine(self):
        try:
            self.machinery_client.stop(
                self.machine.name, wait_response=True, timeout=120
            )
        except ActionFailedError as e:
            raise TaskFlowError(f"Failed to stop machine: {e}")

    def machine_online(self):
        stager_cls = find_stager(self.machine.platform)
        if not stager_cls:
            raise TaskFlowError(
                f"No stager found for that supports {self.machine.platform}"
            )

        self.log.debug("Using stager.", stager=stager_cls.name)
        stager = stager_cls(
            self.agent, self.task, self.analysis, self.result_ip,
            self.result_port, self.log
        )

        try:
            self.log.debug("Preparing stager.")
            stager.prepare()
        except StagerError as e:
            stager.cleanup()
            raise TaskFlowError(f"Stager preparation failed: {e}")

        try:
            self.log.debug("Delivering and executing payload.")
            stager.deliver_payload()
        except PayloadExecFailed as e:
            raise TaskFlowError(f"Failed to execute payload on guest: {e}")
        except StagerError as e:
            raise TaskFlowError(f"Payload delivery failed: {e}")
        finally:
            stager.cleanup()

    def call_at_interval(self):
        pass
