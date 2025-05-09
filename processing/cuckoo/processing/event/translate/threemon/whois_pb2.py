# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: whois.proto

import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor.FileDescriptor(
    name="whois.proto",
    package="threemon",
    syntax="proto3",
    serialized_options=_b("H\002"),
    serialized_pb=_b(
        '\n\x0bwhois.proto\x12\x08threemon"\xb7\x01\n\x05Whois\x12$\n\x04\x61rch\x18\x01 \x01(\x0e\x32\x16.threemon.Architecture\x12\x18\n\x02os\x18\x02 \x01(\x0e\x32\x0c.threemon.OS\x12\x0e\n\x06\x61uthor\x18\x03 \x01(\t\x12\r\n\x05major\x18\x04 \x01(\r\x12\r\n\x05minor\x18\x05 \x01(\r\x12\r\n\x05\x62uild\x18\x06 \x01(\r\x12\x0e\n\x06\x63ommit\x18\x07 \x01(\t\x12\x0f\n\x07is64bit\x18\x08 \x01(\x08\x12\x10\n\x08\x66\x65\x61tures\x18\t \x01(\x04*\x1d\n\x0c\x41rchitecture\x12\x07\n\x03x86\x10\x00"\x04\x08\x01\x10\x05*\x9c\x01\n\x02OS\x12\x0b\n\x07Win7SP0\x10\x00\x12\x0b\n\x07Win7SP1\x10\x01\x12\n\n\x06Win8_0\x10\x02\x12\n\n\x06Win8_1\x10\x03\x12\x0e\n\nWin10_1507\x10\x04\x12\x0e\n\nWin10_1511\x10\x05\x12\x0e\n\nWin10_1607\x10\x06\x12\x0e\n\nWin10_1703\x10\x07\x12\x0e\n\nWin10_1709\x10\x08\x12\x0e\n\nWin10_1803\x10\t"\x04\x08\n\x10\nB\x02H\x02\x62\x06proto3'
    ),
)

_ARCHITECTURE = _descriptor.EnumDescriptor(
    name="Architecture",
    full_name="threemon.Architecture",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="x86", index=0, number=0, serialized_options=None, type=None
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=211,
    serialized_end=240,
)
_sym_db.RegisterEnumDescriptor(_ARCHITECTURE)

Architecture = enum_type_wrapper.EnumTypeWrapper(_ARCHITECTURE)
_OS = _descriptor.EnumDescriptor(
    name="OS",
    full_name="threemon.OS",
    filename=None,
    file=DESCRIPTOR,
    values=[
        _descriptor.EnumValueDescriptor(
            name="Win7SP0", index=0, number=0, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win7SP1", index=1, number=1, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win8_0", index=2, number=2, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win8_1", index=3, number=3, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win10_1507", index=4, number=4, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win10_1511", index=5, number=5, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win10_1607", index=6, number=6, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win10_1703", index=7, number=7, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win10_1709", index=8, number=8, serialized_options=None, type=None
        ),
        _descriptor.EnumValueDescriptor(
            name="Win10_1803", index=9, number=9, serialized_options=None, type=None
        ),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=243,
    serialized_end=399,
)
_sym_db.RegisterEnumDescriptor(_OS)

OS = enum_type_wrapper.EnumTypeWrapper(_OS)
x86 = 0
Win7SP0 = 0
Win7SP1 = 1
Win8_0 = 2
Win8_1 = 3
Win10_1507 = 4
Win10_1511 = 5
Win10_1607 = 6
Win10_1703 = 7
Win10_1709 = 8
Win10_1803 = 9


_WHOIS = _descriptor.Descriptor(
    name="Whois",
    full_name="threemon.Whois",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="arch",
            full_name="threemon.Whois.arch",
            index=0,
            number=1,
            type=14,
            cpp_type=8,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="os",
            full_name="threemon.Whois.os",
            index=1,
            number=2,
            type=14,
            cpp_type=8,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="author",
            full_name="threemon.Whois.author",
            index=2,
            number=3,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=_b("").decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="major",
            full_name="threemon.Whois.major",
            index=3,
            number=4,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="minor",
            full_name="threemon.Whois.minor",
            index=4,
            number=5,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="build",
            full_name="threemon.Whois.build",
            index=5,
            number=6,
            type=13,
            cpp_type=3,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="commit",
            full_name="threemon.Whois.commit",
            index=6,
            number=7,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=_b("").decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="is64bit",
            full_name="threemon.Whois.is64bit",
            index=7,
            number=8,
            type=8,
            cpp_type=7,
            label=1,
            has_default_value=False,
            default_value=False,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
        _descriptor.FieldDescriptor(
            name="features",
            full_name="threemon.Whois.features",
            index=8,
            number=9,
            type=4,
            cpp_type=4,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto3",
    extension_ranges=[],
    oneofs=[],
    serialized_start=26,
    serialized_end=209,
)

_WHOIS.fields_by_name["arch"].enum_type = _ARCHITECTURE
_WHOIS.fields_by_name["os"].enum_type = _OS
DESCRIPTOR.message_types_by_name["Whois"] = _WHOIS
DESCRIPTOR.enum_types_by_name["Architecture"] = _ARCHITECTURE
DESCRIPTOR.enum_types_by_name["OS"] = _OS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Whois = _reflection.GeneratedProtocolMessageType(
    "Whois",
    (_message.Message,),
    dict(
        DESCRIPTOR=_WHOIS,
        __module__="whois_pb2",
        # @@protoc_insertion_point(class_scope:threemon.Whois)
    ),
)
_sym_db.RegisterMessage(Whois)


DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
