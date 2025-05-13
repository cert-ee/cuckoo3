import google.protobuf.message

from . import debug_pb2
from . import file_pb2
from . import inject_pb2
from . import mutant_pb2
from . import network_pb2
from . import notification_pb2
from . import process_pb2
from . import registry_pb2
from . import suspicious_pb2
from . import thread_pb2
from . import whois_pb2
from . import autogen_pb2
from . import dumped_pb2
from . import vminfo_pb2

messages = {
    1: process_pb2.Process,
    2: registry_pb2.Registry,
    3: suspicious_pb2.Suspicious,
    5: notification_pb2.Notification,
    6: inject_pb2.Inject,
    8: file_pb2.File,
    9: mutant_pb2.Mutant,
    10: thread_pb2.ThreadContext,
    12: network_pb2.NetworkFlow,
    13: dumped_pb2.Dumped,
    14: whois_pb2.Whois,
    15: vminfo_pb2.Vminfo,
    16: mutant_pb2.Event,
    100: autogen_pb2.Syscall,
    105: network_pb2.MasterSecret,
    126: debug_pb2.Debug,
    127: debug_pb2.Log,
}

def parse_event(kind, buf):
    msg = messages.get(kind)
    if not msg:
        return {"threemon": name, "error": "unknown message: %s" % kind}
    msg = msg()
    name = msg.__class__.__name__
    try:
        msg.ParseFromString(buf)
    except google.protobuf.message.DecodeError as e:
        return {"threemon": name, "error": str(e)}
    ret = {"threemon": name}

    # We can't use json_format sadly, because it messes with string types
    for descriptor in msg.DESCRIPTOR.fields:
        value = getattr(msg, descriptor.name)
        if descriptor.enum_type:
            value = descriptor.enum_type.values_by_number[value].name
        ret[descriptor.name] = value

    return ret
