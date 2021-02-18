# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import base64
import binascii
import codecs
import os.path
from datetime import datetime
from pathlib import Path

import pefile
import peutils
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization.pkcs7 import (
    load_der_pkcs7_certificates
)
from cryptography.x509 import extensions as x509extensions
from cuckoo.common.storage import Paths
from sflock import magic as sflockmagic

from ..errors import StaticAnalysisError

class PEStaticAnalysisError(StaticAnalysisError):
    pass


class _PEx509Cert:

    def __init__(self, cryptography_x509cert):
        self._cert = cryptography_x509cert

    def _cert_fingerprint_str(self, hashes_algo_instance):
        return binascii.hexlify(
            self._cert.fingerprint(hashes_algo_instance)
        ).decode()

    @property
    def md5(self):
        return self._cert_fingerprint_str(hashes.MD5())

    @property
    def sha1(self):
        return self._cert_fingerprint_str(hashes.SHA1())

    @property
    def sha256(self):
        return self._cert_fingerprint_str(hashes.SHA256())

    @property
    def serial_number(self):
        return str(self._cert.serial_number)

    @property
    def subject_dict(self):
        return {attr.oid._name: attr.value for attr in self._cert.subject}

    @property
    def issuer_dict(self):
        return {attr.oid._name: attr.value for attr in self._cert.issuer}

    def _ext_subjkeyidentifier(self, extension, extensions):
        # oid 2.5.29.14 - subjectKeyIdentifier
        extensions[extension.oid._name] = base64.b64encode(
            extension.value.digest
        ).decode()

    def _ext_authoritykeyidentifier(self, extension, extensions):
        # oid 2.5.29.35 - authorityKeyIdentifier
        extensions[extension.oid._name] =  base64.b64encode(
            extension.value.key_identifier
        ).decode()

    def _ext_certificatepolicies(self, extension, extensions):
        # oid 2.5.29.32 - certificatePolicies
        policies = {}
        for i, policy in enumerate(extension.value):
            if not policy.policy_qualifiers:
                continue

            qualifiers = []
            for qualifier in policy.policy_qualifiers:
                # This was skipped in the old Cuckoo 2 code. For now skip here
                # also until we figure out why. TODO
                if isinstance(qualifier, x509extensions.UserNotice):
                    continue

                qualifiers.append(qualifier)

            policies[policy.policy_identifier.dotted_string] = qualifiers

        extensions[extension.oid._name] = policies

    def _ext_crldistripoints(self, extension, extensions):
        # oid 2.5.29.31 - cRLDistributionPoints
        crl_points = []
        for i, point in enumerate(extension.value):
            for full_name in point.full_name:
                crl_points.append(full_name.value)

        extensions[extension.oid._name] = crl_points

    def _ext_authorityinfoaccess(self, extension, extensions):
        # oid 1.3.6.1.5.5.7.1.1 - authorityInfoAccess
        access_methods = {}
        for authority_info in extension.value:
            name = authority_info.access_method._name
            if name in ("OCSP", "caIssuers"):
                access_methods[name] = authority_info.access_location.value

        extensions[extension.oid._name] = access_methods

    def _ext_subjectaltname(self, extension, extensions):
        # oid 2.5.29.17 - subjectAltName
        altnames = []
        for i, name in enumerate(extension.value._general_names):
            if isinstance(name.value, bytes):
                altnames.append(base64.b64encode(name.value).decode())
            else:
                altnames.append(name.value)

        extensions[extension.oid._name] = altnames

    def _ext_keyusage(self, extension, extensions):
        # oid 2.5.29.15 - keyusage
        usages = {
            "digital_signature": extension.value.digital_signature,
            "content_commitment": extension.value.content_commitment,
            "key_encipherment": extension.value.key_encipherment,
            "data_encipherment": extension.value.data_encipherment,
            "key_agreement": extension.value.key_agreement,
            "key_cert_sign": extension.value.key_cert_sign,
            "crl_sign": extension.value.crl_sign
        }

        if extension.value.key_agreement:
            usages["encipher_only"] = extension.value.encipher_only
            usages["decipher_only"] = extension.value.decipher_only

        extensions[extension.oid._name] = usages

    def _ext_extendedkeyusage(self, extension, extensions):
        # oid 2.5.29.37 - extendedKeyUsage
        extensions[extension.oid._name] = [
            usage._name for usage in extension.value
        ]

    @property
    def extensions_dict(self):
        ext_helpers = {
            "authorityKeyIdentifier": self._ext_authoritykeyidentifier,
            "subjectKeyIdentifier": self._ext_subjkeyidentifier,
            "certificatePolicies": self._ext_certificatepolicies,
            "cRLDistributionPoints": self._ext_crldistripoints,
            "authorityInfoAccess": self._ext_authorityinfoaccess,
            "subjectAltName": self._ext_subjectaltname,
            "extendedKeyUsage": self._ext_extendedkeyusage,
            "keyUsage": self._ext_keyusage
        }

        extensions = {}
        for extension in self._cert.extensions:
            ext_helper = ext_helpers.get(extension.oid._name)
            if ext_helper:
                ext_helper(extension, extensions)

        return extensions

    def to_dict(self):
        return {
            "md5": self.md5,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "serial_number": self.serial_number,
            "subject": self.subject_dict,
            "issuer": self.issuer_dict,
            "extensions": self.extensions_dict
        }


class PEFile:

    _peid_sigdb = None

    def __init__(self, filepath):
        self._path = Path(filepath)
        if not self._path.exists():
            raise PEStaticAnalysisError(f"Path {filepath} does not exist")

        try:
            self._pe = pefile.PE(filepath, fast_load=False)
        except pefile.PEFormatError as e:
            raise PEStaticAnalysisError(str(e))

    def _get_sec_dir_entry(self):
        secdir_index = pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]
        try:
            return self._pe.OPTIONAL_HEADER.DATA_DIRECTORY[secdir_index]
        except IndexError:
            return None

    def is_signed(self):
        sec_entry = self._get_sec_dir_entry()
        if not sec_entry or not sec_entry.VirtualAddress or not sec_entry.Size:
            return False

        return True

    def get_certificates(self):
        if not self.is_signed():
            return []

        sec_entry = self._get_sec_dir_entry()
        certdata = self._pe.write()[sec_entry.VirtualAddress + 8:]
        try:
            allcerts = load_der_pkcs7_certificates(bytes(certdata))
        except ValueError:
            return []

        return [_PEx509Cert(cert).to_dict() for cert in allcerts]

    def get_imported_symbols(self):
        """Return a list of dictionaries of imported symbols"""
        import_entries = getattr(self._pe, "DIRECTORY_ENTRY_IMPORT", [])
        if not import_entries:
            return []

        imports = []
        for entry in import_entries:
            symbols = []
            try:
                for symbol in entry.imports:
                    symbols.append({
                        "address": hex(symbol.address),
                        "name": "" if not symbol.name else symbol.name.decode()
                    })

                imports.append({
                    "dll": entry.dll.decode(),
                    "imports": symbols
                })
            except pefile.PEFormatError:
                # Do something with a format error? TODO
                continue

        return imports

    def get_exported_symbols(self):
        """Return a list of dictionaries of exported symbols"""
        if not hasattr(self._pe, "DIRECTORY_ENTRY_EXPORT"):
            return []

        exports = []
        for symbol in self._pe.DIRECTORY_ENTRY_EXPORT.symbols:
            exports.append({
                "address": hex(
                    self._pe.OPTIONAL_HEADER.ImageBase + symbol.address
                ),
                "ordinal": symbol.ordinal,
                "name": "" if not symbol.name else symbol.name.decode()
            })

        return exports

    def get_sections(self):
        """Return a list of dictonaries of sections"""
        sections = []
        for section in self._pe.sections:
            try:
                sections.append({
                    "name": section.Name.strip(b"\x00").decode(),
                    "virtual_address": f"{section.VirtualAddress:#010x}",
                    "virtual_size": f"{section.Misc_VirtualSize:#010x}",
                    "size_of_data": f"{section.SizeOfRawData:#010x}",
                    "entropy": section.get_entropy()
                })
            except pefile.PEFormatError:
                continue

        return sections

    def get_resources(self):
        """Return a list of resource dictionaries"""
        if not hasattr(self._pe, "DIRECTORY_ENTRY_RESOURCE"):
            return []

        resources = []

        for resource_entry in self._pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if not hasattr(resource_entry, "directory"):
                continue

            if resource_entry.name is not None:
                name = str(resource_entry.name)
            else:
                name = str(
                    pefile.RESOURCE_TYPE.get(resource_entry.struct.Id)
                )

            for resource_dir in resource_entry.directory.entries:
                if not hasattr(resource_dir, "directory"):
                    continue

                for resource_lang in resource_dir.directory.entries:
                    data_offset = resource_lang.data.struct.OffsetToData
                    data_size = resource_lang.data.struct.Size

                    try:
                        filetype = sflockmagic.from_buffer(
                            self._pe.get_data(data_offset, data_size)
                        )
                    except pefile.PEFormatError:
                        filetype = ""

                    resources.append({
                        "name": name,
                        "offset": f"{data_offset:#010x}",
                        "size": f"{data_size:#010x}",
                        "filetype": filetype,
                        "language": pefile.LANG.get(
                            resource_lang.data.lang, None
                        ),
                        "sublanguage": pefile.get_sublang_name_for_lang(
                            resource_lang.data.lang, resource_lang.data.sublang
                        )
                    })

        return resources

    def get_versioninfo(self):
        """Return a list of versioninfo dictionaries"""
        for required_attr in ("VS_VERSIONINFO", "FileInfo"):
            if not hasattr(self._pe, required_attr):
                return []

        infos = []
        for info_list in self._pe.FileInfo:

            for info_entry in info_list:
                if hasattr(info_entry, "StringTable"):
                    for row in info_entry.StringTable:
                        for col in row.entries.items():
                            infos.append({
                                "name": col[0].decode(),
                                "value": col[1].decode()
                            })
                elif hasattr(info_entry, "Var"):
                    for entry in info_entry.Var:
                        if hasattr(entry, "entry"):
                            infos.append({
                                "name": list(entry.entry.keys())[0],
                                "value": list(entry.entry.values())[0]
                            })

        return infos

    def get_imphash(self):
        """Return the imphash or None"""
        try:
            return self._pe.get_imphash()
        except AttributeError:
            return None

    def get_compile_timestamp(self):
        """Returns the compile timestamp or None"""
        try:
            pe_ts = self._pe.FILE_HEADER.TimeDateStamp
        except AttributeError:
            return None

        try:
            return datetime.fromtimestamp(pe_ts).isoformat()
        except ValueError:
            return str(pe_ts)

    def get_pdb_path(self):
        """Return the PDB path or None"""
        if not hasattr(self._pe, "DIRECTORY_ENTRY_DEBUG"):
            return None

        try:
             pdb_path = self._pe.DIRECTORY_ENTRY_DEBUG[0].entry.PdbFileName
             return pdb_path.strip(b"\x00").decode()
        except (pefile.PEFormatError, IndexError):
            return None

    @classmethod
    def _load_pe_sigdb(cls):
        if cls._peid_sigdb:
            return

        peid_sigs_path = Paths.signatures("peutils", "userdb.txt")
        if not os.path.isfile(peid_sigs_path):
            raise PEStaticAnalysisError(
                f"PEiD signatures file does not exist {peid_sigs_path}"
            )

        with codecs.open(peid_sigs_path, "r", errors="replace") as fp:
            cls._peid_sigdb = peutils.SignatureDatabase(data=fp.read())

    def get_peid_signatures(self):
        """Return a list of matched PEID signatures."""
        if not self._peid_sigdb:
            self._load_pe_sigdb()

        return self._peid_sigdb.match(self._pe, ep_only=True) or []

    def to_dict(self):
        return {
            "peid_signatures": self.get_peid_signatures(),
            "pe_imports": self.get_imported_symbols(),
            "pe_exports": self.get_exported_symbols(),
            "pe_sections": self.get_sections(),
            "pe_resources": self.get_resources(),
            "pe_versioninfo": self.get_versioninfo(),
            "pe_imphash": self.get_imphash(),
            "pe_timestamp": self.get_compile_timestamp(),
            "signatures": self.get_certificates(),
        }
