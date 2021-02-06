# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class CompareError(Exception):
    pass

class ComparedValue:

    def __init__(self, value, valuetype, description, task_ids):
        self.valuetype = valuetype
        self.description = description
        self.value = value
        self._tasks = {task_id:False for task_id in task_ids}

    def task_has_value(self, task_id):
        if not task_id in self._tasks:
            raise CompareError(
                f"Cannot set mark value as present for task {task_id} that "
                "is not part of comparison"
            )

        self._tasks[task_id] = True

    def to_dict(self):
        return {
            "value": self.value,
            "description": self.description,
            "tasks": self._tasks
        }

    def __eq__(self, other):
        return self.valuetype == other.valuetype and self.value == other.value

    def __hash__(self):
        return hash(self.valuetype + self.value)

class PostReportCompare:

    comparetype = ""

    def __init__(self, post_reports):
        self._posts = post_reports
        self.compared = set()
        self._compare()

    def _compare(self):
        raise NotImplementedError

    def to_dict(self):
        return [compared.to_dict() for compared in self.compared]

class TaskSignaturesCompare(PostReportCompare):

    comparetype = "signatures"

    def _make_comparedvalues(self):
        all_sigs = set()
        tasks = {p.task_id: set() for p in self._posts}
        for post in self._posts:
            for sig in post.signatures:
                compare = ComparedValue(
                    sig["short_description"], "signature", sig["description"],
                    list(tasks.keys())
                )
                all_sigs.add(compare)
                tasks[post.task_id].add(compare)

        return all_sigs, tasks

    def _compare(self):
        all_sigs, tasks_sigs = self._make_comparedvalues()
        self.compared = all_sigs

        for sig in all_sigs:
            for task_id, task_sigs in tasks_sigs.items():
                if sig in task_sigs:
                    sig.task_has_value(task_id)

class TaskFamilyCompare(PostReportCompare):

    comparetype = "family"

    def _make_comparedvalues(self):
        all_families = set()
        tasks = {p.task_id: set() for p in self._posts}
        for post in self._posts:
            for family in post.families:
                compare = ComparedValue(
                    family, "family", "", list(tasks.keys())
                )
                all_families.add(compare)
                tasks[post.task_id].add(compare)

        return all_families, tasks

    def _compare(self):
        all_families, tasks_families = self._make_comparedvalues()
        self.compared = all_families

        for family in all_families:
            for task_id, families in tasks_families.items():
                if family in families:
                    family.task_has_value(task_id)

class ComparePostReports:

    def __init__(self, post_reports):
        self._post_reports = post_reports
        self._compares = []

    def compare(self):
        if len(set(p.task_id for p in self._post_reports)) < 2:
            raise CompareError(
                "At least two different task post reports are required to "
                "perform a compare"
            )

        self._compares.append(TaskSignaturesCompare(self._post_reports))
        self._compares.append(TaskFamilyCompare(self._post_reports))

    def to_dict(self):
        d = {}
        for compare in self._compares:
            d[compare.comparetype] = compare.to_dict()

        return d
