# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: notification.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12notification.proto\x12\x08threemon\"D\n\x0cNotification\x12\n\n\x02ts\x18\x02 \x01(\r\x12(\n\x04type\x18\x01 \x01(\x0e\x32\x1a.threemon.NotificationType*,\n\x10NotificationType\x12\n\n\x06NoPids\x10\x00\x12\x0c\n\x08\x46inished\x10\x01\x42\x02H\x02\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'notification_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'H\002'
  _NOTIFICATIONTYPE._serialized_start=102
  _NOTIFICATIONTYPE._serialized_end=146
  _NOTIFICATION._serialized_start=32
  _NOTIFICATION._serialized_end=100
# @@protoc_insertion_point(module_scope)
