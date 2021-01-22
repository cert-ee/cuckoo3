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
                A1 ?? ?? ?? ??           // mov     eax, g_xor_constant
                8B ?? ?? ?? ?? ??        // mov     ebp, dword_42D8C4
                33 ??                    // xor     ebp, eax
                [20-50]                  //
                E8 ?? ?? ?? ??           // call    alloc_heap_space
                [1-10]                    //
                85 ??                    // test    eax, eax
                7? ??                    // jz      short loc_41D12E
                [0-4]                    // and     [esp+28h+var_14], ebx
                (
                BA ?? ?? ?? ??           // mov     edx, offset g_xored_rsa_key
                C1 ?? 02                 // shr     esi, 2
                |
                C1 ?? 02                 // shr     ebp, 2
                [0-4]                    // push    esi
                B? ?? ?? ?? ??           // mov     esi, offset g_xor_key
                )
                [0-7]
                8D ?? ?? ?? ?? ?? ??     // lea     ecx, g_xored_rsa_key[esi*4]
            }
            $enumips = {
                BE ?? ?? ?? ??      // mov     esi, offset unk_10021000
                [2-300]             // random opcodes
                E8 ?? ?? ?? ??      // call    sub_100157E8
                A3 ?? ?? ?? ??      // mov     dword_100221C0, eax
                5?                  // pop     ecx
                85 ??               // test    eax, eax
                7? ??               // jz      short loc_1001D46B
                89 [1-3]            // mov     [eax+4], esi
                89 [1-3]            // mov     [eax+18h], esi
                8B [1-5]            // mov     eax, [ebp+var_C]
                8B ?? ?? ?? ?? ??   // mov     ecx, dword_100221C0
                8B [1-5]            // mov     edx, [ecx+4]
                89 [1-3]            // mov     [ecx+40h], eax
                8B [1-5]            // mov     eax, [ecx+28h]
                EB ??               // jmp     short loc_1001D42F
                4?                  // inc     eax
                89 [1-3]            // mov     [ecx+28h], eax
                83 ?? ?? 00         // cmp     dword ptr [edx+eax*8], 0
            }
        condition:
            $rsakey and $enumips
    }"""

    @classmethod
    def search(cls, cfg_memdump):
        rule = yara.compile(source=cls.YARA)
        matches = rule.match(data=cfg_memdump.buf)
        if matches:
            return cls._extract(matches, cfg_memdump)

        return None

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
            rsakey_addr = struct.unpack("I", data[-4:])[0]
            xored_rsakey = cfg_memdump.buf[rsakey_addr
                                           - cfg_memdump.base_address:][:106]
            xorkey_addr = struct.unpack("I", data[1:5])[0]
            xorkey = cfg_memdump.buf[xorkey_addr
                                     - cfg_memdump.base_address:][:4]
        except struct.error as e:
            raise UnexpectedDataError(
                f"Invalid rsakey address or xorkey bytes: {e}"
            )

        except IndexError:
            raise UnexpectedDataError(
                "rsakey or xorkey address causes out of bounds read"
            )

        key = Key(
            keytype="rsa_pubkey",
            value=roach.rsa.import_key(
                roach.xor(xorkey, xored_rsakey)
            ).decode()
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
