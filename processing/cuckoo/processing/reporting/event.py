# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.


from ..helpers import Reporter

class Event(Reporter):

    def report_identification(self):
        # TODO implement this. Can be used to notify other components about
        # this identification stage state/result
        print(
            f"Hello other components, {self.analysis.id} identification is "
            f"done!"
        )

    def report_pre_analysis(self):
        # TODO implement this. Can be used to notify other components about
        # this pre-analysis stage state/result
        print(
            f"Hello other components, {self.analysis.id} pre analysis is "
            f"done!"
        )
