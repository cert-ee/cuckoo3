# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.


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


class ScreenshotName:
    regex = "[0-9]{0,14}\.(jpg|png)"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)


class Sha256Hash:
    regex = "[a-fA-F0-9]{64}"

    def to_python(self, value):
        return str(value)

    def to_url(self, value):
        return str(value)
