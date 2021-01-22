# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common.packages import enumerate_plugins

from ..abtracts import ConfigExtractor

class ConfigExtractionError(Exception):
    pass

class UnexpectedDataError(ConfigExtractionError):
    pass

class ConfigMemdump:

    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.pid = None
        self.index = None
        self.base_address = None
        self.end_address = None
        self._buf = None
        self._parse_name()

    @classmethod
    def valid_name(cls, filepath):
        try:
            cls(filepath)
            return True
        except ConfigExtractionError:
            return False

    @property
    def name(self):
        return self.filepath.name

    @property
    def buf(self):
        if not self._buf:
            self._read_buf()

        return self._buf

    def _parse_name(self):
        vals = self.name.split("-", 4)
        if len(vals) != 5:
            raise ConfigExtractionError(
                "Memory dump file name does not have format: "
                "pid-counter-base_address-end_address-memory.dmp"
            )

        try:
            self.pid = int(vals[0])
            self.index = int(vals[1])
            self.base_address = int(vals[2], 0)
            self.end_address = int(vals[3], 0)
        except ValueError as e:
            raise ConfigExtractionError(
                "One of pid, index, base or end address is not a valid "
                f"number. {e}"
            )

    def _read_buf(self):
        with open(self.filepath, "rb") as fp:
            self._buf = fp.read()

    def clear(self):
        self._buf = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear()

    def __del__(self):
        self.clear()

class ExtractedDataType:

    KEY = ""
    TYPE = ""

    def to_dict(self):
        raise NotImplementedError

class C2(ExtractedDataType):

    KEY = "c2s"
    TYPE = "c2"

    def __init__(self, address, ip=None, port=None, domain=None):
        self.address = address
        self.ip = ip
        self.port = port
        self.domain = domain

    def to_dict(self):
        d = {
            "address": self.address
        }
        if self.ip:
            d["ip"] = self.ip
        if self.port:
            d["port"] = self.port

        if self.domain:
            d["domain"] = self.domain

        return d

    def __hash__(self):
        return hash(self.address)

class Key(ExtractedDataType):

    KEY = "keys"
    TYPE = "key"

    def __init__(self, keytype, value):
        self.keytype = keytype
        self.value = value

    def to_dict(self):
        return {
            "keytype": self.keytype,
            "value": self.value
        }

    def __hash__(self):
        return hash(self.keytype + self.value)

class ExtractedConfig:

    def __init__(self, family):
        self.family = family
        self.values = {}

    def add_extracted(self, extracted_data):
        self.values.setdefault(extracted_data.KEY, set()).add(extracted_data)

    def to_dict(self):
        return {
            key: list(values) for key, values in self.values.items()
        }

class Extractor:

    extractors = []

    @classmethod
    def init_once(cls):
        cls.extractors = enumerate_plugins(
            "cuckoo.processing.cfgextr", globals(), ConfigExtractor
        )

    @classmethod
    def search(cls, config_memdump):
        for extractor in cls.extractors:
            try:
                config = extractor.search(config_memdump)
            except UnexpectedDataError as e:
                raise UnexpectedDataError(
                    f"Unexpected data during extraction by {extractor}. {e}"
                )
            if config:
                return config
