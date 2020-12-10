# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

class AnalysisId:

    regex = "[0-9]{8}-[A-Z0-9]{6}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)

class TaskId:

    regex = "[0-9]{8}-[A-Z0-9]{6}_[0-9]{0,3}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)
