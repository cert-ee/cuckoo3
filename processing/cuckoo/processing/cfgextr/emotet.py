# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import roach
import socket
import struct
import yara

from ..abtracts import ConfigExtractor
from .cfgextr import ExtractedConfig, C2, Key

class Emotet(ConfigExtractor):

    FAMILY = "Emotet"
    YARA = """
    rule Emotet {
        strings:
            $rsakey = {
                33 C0                               //  0 xor     eax, eax
                89 0D ?? ?? ?? ??                   //  2 mov     ren_SYSTEMINFO, ecx
                C7 05 ?? ?? ?? ?? ?? ?? ?? ??       //  8 mov     RSAKEY1, offset RSAKEY
                40                                  // 18 inc     eax
                C7 05 ?? ?? ?? ?? 6A 00 00 00       // 19 mov     RSAKEYSIZE, 6Ah
                C3                                  // 29 retn
            }
            $enumips = {
                B8 ?? ?? ?? ??                      //  0 mov     eax, offset IPS
                A3 ?? ?? ?? ??                      //  5 mov     IPS_1, eax
                A3 ?? ?? ?? ??                      //    mov     CURRENT_IP, eax
                33 C0                               //    xor     eax, eax
                21 05 ?? ?? ?? ??                   //    and     ATTEMPTS, eax
                A3 ?? ?? ?? ??                      //    mov     NUMBEROFIPS, eax
                39 05 ?? ?? ?? ??                   //    cmp     IPS, eax
                74 ??                               //    jz      short loc_1116101
                40                                  //    inc     eax
                A3 ?? ?? ?? ??                      //    mov     NUMBEROFIPS, eax
                83 3C C5 ?? ?? ?? ?? 00             //    cmp     IPS[eax*8], 0
                75 ??                               //    jnz     short loc_11160E9
                51                                  //    push    ecx
                E8 ?? ?? ?? ??                      //    call    generate_aes_key
                59                                  //    pop     ecx
                C3                                  //    retn
            }
        condition:
            $rsakey and $enumips
    }"""

    @classmethod
    def search(cls, cfg_memdump, extracted_tracker):
        rule = yara.compile(source=cls.YARA)
        matches = rule.match(data=cfg_memdump.buf)

        if not matches:
            return

        config = cls._extract(matches, cfg_memdump)
        if config:
            extracted_tracker.add_config(config)

    @classmethod
    def _extract(cls, matches, cfg_memdump):
        extracted = ExtractedConfig(cls.FAMILY, cfg_memdump.name)
        for match in matches:
            for offset, name, data in match.strings:
                if name == "$rsakey":
                    cls._read_rsakey(data, cfg_memdump, extracted)
                elif name == "$enumips":
                    cls._read_enumips(data, cfg_memdump, extracted)

        if extracted.values:
            return extracted

        return None

    @classmethod
    def _read_rsakey(cls, data, cfg_memdump, extracted):
        try:
            rsakey_addr = struct.unpack("I", data[14:18])[0]
            rsakey = cfg_memdump.buf[rsakey_addr
                                     - cfg_memdump.base_address:][:106]
        except struct.error as e:
            raise UnexpectedDataError(
                f"Invalid rsakey address: {e}"
            )

        except IndexError:
            raise UnexpectedDataError(
                "rsakey address causes out of bounds read"
            )

        key = Key(
            keytype="rsa_pubkey",
            value=roach.rsa.import_key(rsakey).decode()
        )
        extracted.add_extracted(key)

    @classmethod
    def _read_enumips(cls, data, cfg_memdump, extracted):
        try:
            addr = struct.unpack("I", data[1:5])[0]
        except struct.error as e:
            raise UnexpectedDataError(
                f"Invalid enumips start address bytes: {e}"
            )

        ip_ports = set()
        for _ in range(1024):
            try:
                ip = socket.inet_ntoa(
                    cfg_memdump.buf[addr - cfg_memdump.base_address:][:4][::-1]
                )
                port = struct.unpack(
                    "H", cfg_memdump.buf[addr-cfg_memdump.base_address+4:][:2]
                )[0]
            except OSError:
                raise UnexpectedDataError("Invalid IPv4 address bytes")
            except IndexError:
                raise UnexpectedDataError(
                    "enumip address causes out of bounds read"
                )
            except struct.error as e:
                raise UnexpectedDataError(f"Invalid C2 port bytes: {e}")

            if ip == "0.0.0.0":
                break

            extracted.add_extracted(
                C2(address=f"{ip}:{port}", ip=ip, port=port)
            )

            addr += 8
