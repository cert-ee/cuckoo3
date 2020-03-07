# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.


from ..helpers import Reporter

class Event(Reporter):

    def report_identification(self):
        # TODO implement this. Should send some form of 'event' so other
        # components known this is done. This event layer does not exist yet.
        print(
            f"Hello other components, {self.analysis.id} identification is "
            f"done!"
        )
