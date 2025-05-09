# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: vminfo.proto

import sys

_b = sys.version_info[0] < 3 and (lambda x: x) or (lambda x: x.encode("latin1"))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor.FileDescriptor(
    name="vminfo.proto",
    package="threemon",
    syntax="proto3",
    serialized_options=_b("H\002"),
    serialized_pb=_b(
        '\n\x0cvminfo.proto\x12\x08threemon"K\n\x06Vminfo\x12\x15\n\rcomputer_name\x18\x01 \x01(\t\x12\x13\n\x0bvolume_name\x18\x02 \x01(\t\x12\x15\n\rvolume_serial\x18\x03 \x01(\rB\x02H\x02\x62\x06proto3'
    ),
)


_VMINFO = _descriptor.Descriptor(
    name="Vminfo",
    full_name="threemon.Vminfo",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    fields=[
        _descriptor.FieldDescriptor(
            name="computer_name",
            full_name="threemon.Vminfo.computer_name",
            index=0,
            number=1,
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
            name="volume_name",
            full_name="threemon.Vminfo.volume_name",
            index=1,
            number=2,
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
            name="volume_serial",
            full_name="threemon.Vminfo.volume_serial",
            index=2,
            number=3,
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
    serialized_end=101,
)

DESCRIPTOR.message_types_by_name["Vminfo"] = _VMINFO
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Vminfo = _reflection.GeneratedProtocolMessageType(
    "Vminfo",
    (_message.Message,),
    dict(
        DESCRIPTOR=_VMINFO,
        __module__="vminfo_pb2",
        # @@protoc_insertion_point(class_scope:threemon.Vminfo)
    ),
)
_sym_db.RegisterMessage(Vminfo)


DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
