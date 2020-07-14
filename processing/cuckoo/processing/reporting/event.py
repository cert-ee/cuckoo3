# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from ..abtracts import Reporter

class Event(Reporter):

    def report_identification(self):
        # TODO implement this. Can be used to notify other components about
        # this identification stage state/result
        pass

    def report_pre_analysis(self):
        # TODO implement this. Can be used to notify other components about
        # this pre-analysis stage state/result
        pass
