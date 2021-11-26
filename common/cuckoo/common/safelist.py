# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import csv
import ipaddress
import re
import sqlalchemy
from sqlalchemy.ext.declarative import as_declarative

from cuckoo.common.db import DBMS
from cuckoo.common.utils import parse_bool


class SafelistError(Exception):
    pass

@as_declarative()
class SafelistTable:

    def to_dict(self):
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

class AlembicVersion(SafelistTable):
    """Database schema version. Used for automatic database migrations."""
    __tablename__ = "alembic_version"

    SCHEMA_VERSION = None

    version_num = sqlalchemy.Column(
        sqlalchemy.String(32), nullable=False, primary_key=True
    )

class SafelistEntry(SafelistTable):

    __tablename__ = "safelists"
    __table_args__ = sqlalchemy.Index("name_index", "name", unique=False),

    id = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True
    )
    name = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    valuetype = sqlalchemy.Column(sqlalchemy.String(32))
    value = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    regex = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
    platform = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    source = sqlalchemy.Column(sqlalchemy.Text, nullable=True)

    def __str__(self):
        return f"<id={self.id}, name={self.name}, value={self.value!r}, " \
               f"valuetype={self.valuetype}, regex={self.regex}, " \
               f"platform={self.platform!r}," \
               f" description={self.description!r}, source={self.source}>"

    def __repr__(self):
        return str(self)


safelistdb = DBMS(
    schema_version=AlembicVersion.SCHEMA_VERSION,
    alembic_version_table=AlembicVersion
)

class LoadedSafelistEntry:

    __slots__ = ("id", "name", "valuetype", "loadedvalue", "regex", "platform",
                 "description", "source")

    def __init__(self, name, valuetype, loadedvalue, platform, regex=False,
                 description="", source="", id=None):
        self.id = id
        self.name = name
        self.valuetype = valuetype
        self.loadedvalue = loadedvalue
        self.regex = regex
        self.platform = platform
        self.description = description
        self.source = source

    def __hash__(self):
        return hash(self.loadedvalue)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "valuetype": self.valuetype,
            "value": self.loadedvalue,
            "regex": self.regex,
            "platform": self.platform,
            "description": self.description,
            "source": self.source
        }

def get_entries(safelist_name="", platform=""):

    ses = safelistdb.session()
    try:
        q = ses.query(SafelistEntry)
        if safelist_name:
            q = q.filter_by(name=safelist_name)
        if platform:
            q = q.filter_by(platform=platform)

        return q.all()
    finally:
        ses.close()

def _matches_platform(entry, required_platform):
    """Returns the safelist entry if the platform matches, if no platform
    is set as required, or if the entry has no platform."""
    if not required_platform:
        return True
    if not entry.platform:
        return True

    if entry.platform == required_platform:
        return True

    return False


class Safelist:

    name = ""
    valuetype = ""
    description = ""

    def is_safelisted(self, value, platform=""):
        """Must return the the safelist entry object if safelisted and None
        if not safelisted"""
        raise NotImplementedError

    def load_safelist(self):
        """Performs any operations required to be able to query the
         safelist"""
        raise NotImplementedError

    @classmethod
    def validate(cls, value, regex, platform, description, source):
        """Verify if value is a valid example of 'valuetype' and check
        other potential constraints. Must raise SafelistError if invalid"""
        pass

    @classmethod
    def find_existing(cls, value, platform, regex):
        ses = safelistdb.session()
        try:
            return ses.query(SafelistEntry).filter(
                SafelistEntry.name==cls.name,
                SafelistEntry.valuetype==cls.valuetype,
                SafelistEntry.value==value,
                SafelistEntry.platform==platform,
                SafelistEntry.regex==regex
            ).first()
        finally:
            ses.close()

    @classmethod
    def add_entry(cls, value, platform, regex=False, description="",
                  source=""):
        cls.validate(
            value=value, platform=platform, regex=regex,
            description=description, source=source
        )

        existing = cls.find_existing(value, platform, regex)
        if existing:
            raise SafelistError(
                f"Value {value!r} for platform {platform!r} already exists. "
                f"Existing: {existing}"
            )

        ses = safelistdb.session()
        try:
            ses.add(SafelistEntry(
                name=cls.name, valuetype=cls.valuetype, value=value,
                regex=regex, platform=platform, description=description,
                source=source
            ))
            ses.commit()
        finally:
            ses.close()

    @classmethod
    def add_many(cls, dict_list):
        new_entries = []
        for entry in dict_list:
            try:
                value = entry["value"]
                platform = entry["platform"]
                regex = entry["regex"]
            except KeyError as e:
                raise SafelistError(
                    f"Missing one or more keys in {entry!r}. Error: {e}"
                )

            cls.validate(
                value=value, platform=platform,
                regex=regex, description=entry.get("description", ""),
                source=entry.get("source", "")
            )

            new_entries.append({
                "name": cls.name,
                "valuetype": cls.valuetype,
                "value": value,
                "platform": platform,
                "regex": regex,
                "description": entry.get("description", ""),
                "source": entry.get("source", "")
            })

        ses = safelistdb.session()
        try:
            ses.bulk_insert_mappings(SafelistEntry, new_entries)
            ses.commit()
        finally:
            ses.close()

    @classmethod
    def delete_entries(cls, ids=[]):
        for entry in ids:
            if not isinstance(entry, int):
                raise SafelistError(
                    "Safelist entry identifier must be an integer. "
                    f"Got {entry!r}"
                )

        ids = list(set(ids))

        ses = safelistdb.session()
        try:
            stmnt = SafelistEntry.__table__.delete().where(
                SafelistEntry.id.in_(ids)
            )
            safelistdb.engine.execute(stmnt)
        finally:
            ses.close()

    @classmethod
    def delete_all(cls):
        ses = safelistdb.session()
        try:
            stmnt = SafelistEntry.__table__.delete().where(
                SafelistEntry.name==cls.name
            )
            safelistdb.engine.execute(stmnt)
        finally:
            ses.close()


class SimpleSafelist(Safelist):

    def __init__(self):
        self._entries = {}
        self._entries_regex = []

    def _check_regex_safelist(self, value):
        for entry in self._entries_regex:
            if entry.loadedvalue.fullmatch(value):
                return entry

        return None

    def is_safelisted(self, value, platform=""):
        entry = self._entries.get(value)
        if entry and _matches_platform(entry, platform):
            return entry

        if self._entries_regex:
            entry = self._check_regex_safelist(value)
            if entry and _matches_platform(entry, platform):
                return entry

        return None

    def _load_regex_entry(self, entry):
        try:
            compiled_regex = re.compile(entry.value)
        except re.error as e:
            raise SafelistError(
                f"Failed to compile regex safelist entry {entry.id} and "
                f"value {entry.value} for safelist'{self.name}'. Error: {e}"
            )

        self._entries_regex.append(LoadedSafelistEntry(
            id=entry.id, name=entry.name, valuetype=entry.valuetype,
            loadedvalue=compiled_regex, regex=True,
            description=entry.description, source=entry.source,
            platform=entry.platform
        ))

    def _load_entry(self, entry):
        self._entries[entry.value] = LoadedSafelistEntry(
            id=entry.id, name=entry.name, valuetype=entry.valuetype,
            loadedvalue=entry.value, regex=False,
            description=entry.description,
            source=entry.source, platform=entry.platform
        )

    def load_safelist(self):
        for entry in get_entries(safelist_name=self.name):
            if entry.regex:
                self._load_regex_entry(entry)
            else:
                self._load_entry(entry)

    @classmethod
    def validate(cls, value, regex, platform, description, source):
        if not regex:
            return

        try:
            re.compile(value)
        except re.error as e:
            raise SafelistError(f"Regex compilation error: {e}")


class Domain(SimpleSafelist):

    name = "domain_global"
    valuetype = "domain"
    description = "Domains to and from which traffic should be ignored"

class FileHash(SimpleSafelist):

    name = "filehash_submission"
    valuetype = "filehash"
    description = "md5, sha1 or sha256 hashes of files that should be " \
                  "cancelled after submission"

    @classmethod
    def validate(cls, value, regex, platform, description, source):
        if regex:
            raise SafelistError("Regexes are not supported for file hashes")

        for hashlen in (r"^[a-f0-9]{32}$", r"^[a-f0-9]{40}$",
                        r"^[a-f0-9]{64}$"):
            if re.match(hashlen, value.lower()):
                return

        raise SafelistError("Value is not a valid md5, sha1 or sha256 hash")

    def load_safelist(self):
        # Do not load hash safelists in memory as safelisted hash sets
        # can multiple gigabytes.
        pass

    def is_safelisted(self, value, platform=""):
        # Query DB directly to reduce memory usage.
        ses = safelistdb.session()
        try:
            match = ses.query(SafelistEntry).filter_by(value=value).first()
        finally:
            ses.close()

        if match:
            return LoadedSafelistEntry(
                id=match.id, name=match.name, valuetype=match.valuetype,
                loadedvalue=match.value, regex=match.regex,
                platform=match.platform, description=match.description,
                source=match.source
            )

        return None

class IP(Safelist):

    name = "ip_global"
    valuetype = "ip"
    description = "IP (networks) to and from which traffic should be ignored"

    def __init__(self):
        super().__init__()
        self._networks = set()
        self._tmp_networks = set()

    def clear_temp(self):
        self._tmp_networks = set()

    def add_temp_entry(self, ip_network, platform, description, source):
        self.validate(ip_network, False, platform, description, source)
        self._tmp_networks.add(LoadedSafelistEntry(
                id=None, name=self.name, valuetype=self.valuetype,
                loadedvalue=self._make_ip_network(ip_network), regex=False,
                platform=platform, description=description,
                source=source
            ))

    @classmethod
    def _make_ip_network(cls, ip_network_str):
        try:
            return ipaddress.ip_network(ip_network_str)
        except ValueError as e:
            raise SafelistError(
                f"Failed to load safelist: '{cls.name}' Not a valid IPv4 "
                f"or IPv6 network: {ip_network_str!r}. Error: {e}"
            )

    def _search_networks(self, ip, networks):
        for network in networks:
            if ip in network.loadedvalue:
                return network

    def is_safelisted(self, ip_address, platform=""):
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError as e:
            raise SafelistError(
                f"Invalid IP address: {ip_address!r}. Error: {e}"
            )

        network = self._search_networks(ip, self._networks)
        if network and _matches_platform(network, platform):
            return network

        network = self._search_networks(ip, self._tmp_networks)
        if network and _matches_platform(network, platform):
            return network

        return None

    def load_safelist(self):
        for entry in get_entries(safelist_name=self.name):
            self._networks.add(LoadedSafelistEntry(
                id=entry.id, name=entry.name, valuetype=entry.valuetype,
                loadedvalue=self._make_ip_network(entry.value), regex=False,
                platform=entry.platform, description=entry.description,
                source=entry.source
            ))

    @classmethod
    def add_entry(cls, value, platform, regex=False, description="",
                  source=""):
        if regex:
            raise SafelistError(
                f"Safelist {cls.name} with value type {cls.valuetype} does not"
                f" support regexes"
            )
        super().add_entry(
            value=value, platform=platform, regex=False,
            description=description, source=source
        )

    @classmethod
    def validate(cls, value, regex, platform, description, source):
        try:
            ipaddress.ip_network(value)
        except ValueError as e:
            raise SafelistError(f"Invalid IPv4 network {value}. Error: {e}")

class DNSServerIP(IP):

    name = "dns_server"
    description = "IPs of DNS servers that should not be considered a " \
                  "contacted host"

class DomainMisp(Domain):

    name = "domain_misp"
    description = "Domains that should not be reported to MISP"

class URLMisp(SimpleSafelist):

    name = "url_misp"
    description = "URLs that should not be reported to MISP"
    valuetype = "url"

class IPMisp(IP):

    name = "ip_misp"
    description = "IP (networks) that should not be reported to MISP"

class IPIntelMQ(IP):

    name = "ip_intelmq"
    description = "IP (networks) that should not be reported to IntelMQ"

class DomainIntelMQ(Domain):

    name = "domain_intelmq"
    description = "Domains that should not be reported to IntelMQ"

class URLIntelMQ(SimpleSafelist):

    name = "url_intelmq"
    description = "URLs that should not be reported to IntelMQ"
    valuetype = "url"


class SafelistName:
    ip_global = IP.name
    domain_global = Domain.name
    ip_dnsserver = DNSServerIP.name
    ip_misp = IPMisp.name
    domain_misp = DomainMisp.name
    url_misp = URLMisp.name
    filehash_submission = FileHash.name
    ip_intelmq = IPIntelMQ.name
    domain_intelmq = DomainIntelMQ.name
    url_intelmq = URLIntelMQ.name

name_safelist = {
    SafelistName.ip_global: IP,
    SafelistName.domain_global: Domain,
    SafelistName.ip_dnsserver: DNSServerIP,
    SafelistName.ip_misp: IPMisp,
    SafelistName.domain_misp: DomainMisp,
    SafelistName.url_misp: URLMisp,
    SafelistName.filehash_submission: FileHash,
    SafelistName.ip_intelmq: IPIntelMQ,
    SafelistName.domain_intelmq: DomainIntelMQ,
    SafelistName.url_intelmq: URLIntelMQ
}

def import_csv_safelist(csv_path, safelist_class):
    if not issubclass(safelist_class, Safelist):
        raise SafelistError("Safelist class must be subclass of Safelist")

    entries = []
    with open(csv_path, "r") as fp:
        reader = csv.DictReader(fp)
        min_keys = ("value", "regex", "platform")
        for key in min_keys:
            if key not in reader.fieldnames:
                raise SafelistError(
                    f"Safelist CSV file must have columns: {min_keys}. "
                    f"Missing: {key}"
                )

        for line in reader:
            value = line["value"]
            try:
                regex = parse_bool(line["regex"])
            except ValueError:
                raise SafelistError(
                    f"Regex must be False or True. "
                    f"Invalid value at line: {reader.line_num}"
                )
            if not value:
                raise SafelistError(
                    f"Value cannot be empty. Line {reader.line_num}"
                )

            entries.append({
                "value": value,
                "regex": regex,
                "platform": line.get("platform", ""),
                "description": line.get("description", ""),
                "source": line.get("source", "")
            })

    safelist_class.add_many(entries)

def dump_safelist_csv(csv_path, safelist_class):
    if not issubclass(safelist_class, Safelist):
        raise SafelistError("Safelist class must be subclass of Safelist")

    ses = safelistdb.session()
    try:
        entries = ses.query(
            SafelistEntry
        ).filter_by(name=safelist_class.name).all()
    finally:
        ses.close()

    with open(csv_path, "w") as fp:
        csvfile = csv.DictWriter(
            fp, fieldnames=list(SafelistEntry().to_dict().keys())
        )
        csvfile.writeheader()
        for entry in entries:
            csvfile.writerow(entry.to_dict())
