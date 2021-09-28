# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.
import json

from cuckoo.common.storage import safe_json_dump
from cuckoo.common.machines import read_machines_dump_dict
from cuckoo.common.route import Routes
from datetime import datetime, timedelta


class NodeInfo:

    def __init__(self, name, version, machines_list, routes):
        self.name = name
        self.version = version
        self.machines_list = machines_list
        self.routes = routes

    @property
    def updated(self):
        return self.machines_list.updated

    def clear_updated(self):
        self.machines_list.clear_updated()

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "machines_list": self.machines_list.to_dictlist(),
            "routes": self.routes.to_dict()
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            name=d["name"], version=d["version"],
            machines_list=read_machines_dump_dict(d["machines_list"]),
            routes=Routes.from_dict(d["routes"])
        )

    def has_route(self, route):
        if not route or not route.type:
            return True

        return self.routes.has_route(route)

    def has_platform(self, platform):
        if not platform:
            return True

        if self.machines_list.find(
            platform=platform.platform, os_version=platform.os_version,
            tags=set(platform.tags)
        ):
            return True

        return False


def dump_nodeinfos(path, *args):
    nodes = []
    for info in args:
        nodes.append(info.to_dict())

    # This is required to prevent the machine info dump from ever being
    # empty. The function ensures the file is first being dumped and afterwards
    # replaces the existing dump.
    safe_json_dump(path, nodes, overwrite=True)

class NodeInfos:

    def __init__(self, min_dump_wait=300):
        self.nodeinfos = set()

        self._min_dump_wait = min_dump_wait
        self._last_dump = None
        self._changed = False

    @property
    def all_machine_lists(self):
        return [info.machines_list for info in self.nodeinfos]

    def has_nodes(self):
        return len(self.nodeinfos) > 0

    def get_platforms_versions(self):
        platforms_versions = {}
        for info in self.nodeinfos:
            p_vs = info.machines_list.get_platforms_versions()
            for platform, versions in p_vs.items():
                platforms_versions.setdefault(platform, set()).update(versions)

        return platforms_versions

    def get_routes(self):
        available_routes = Routes([])
        for info in self.nodeinfos:
            available_routes.merge_routes(info.routes)

        return available_routes.to_dict()

    def infos_changed(self):
        for info in self.nodeinfos:
            if info.updated:
                return True

        return False

    def dump_wait_reached(self):
        if not self._last_dump:
            return True

        if datetime.utcnow() - self._last_dump >= timedelta(
                seconds=self._min_dump_wait
        ):
            return True

        return False

    def should_dump(self):
        return self.dump_wait_reached() and self.infos_changed() \
               or self._changed

    def make_dump(self, path):
        dump_nodeinfos(path, *self.nodeinfos)
        self._last_dump = datetime.utcnow()

        self._changed = False
        for info in self.nodeinfos:
            info.clear_updated()

    def add_nodeinfo(self, info):
        self.nodeinfos.add(info)
        self._changed = True

    def remove_nodeinfo(self, info):
        self.nodeinfos.discard(info)
        self._changed = True

    @classmethod
    def from_dump(cls, dict_list):
        nodeinfos = cls()
        for info_dict in dict_list:
            nodeinfos.add_nodeinfo(NodeInfo.from_dict(info_dict))
        return nodeinfos

    def find_support(self, platform, route):
        """Search if the platform/route combination exists on one of the
        available nodes. Returns: has_platform(bool), has_route(bool),
        nodeinfo (NodeInfo). Nodeinfo will be None if one of the bools
        is false.
        """
        has_platform, has_route = False, False
        for info in self.nodeinfos:
            has_platform = info.has_platform(platform)
            has_route = info.has_route(route)
            if has_platform and has_route:
                return True, True, info

        return has_platform, has_route, None

def read_nodesinfos_dump(path):
    with open(path, "r") as fp:
        return NodeInfos.from_dump(json.load(fp))

class ExistingResultServer:

    def __init__(self, socket_path, listen_ip, listen_port):
        self.socket_path = socket_path
        self.listen_ip = listen_ip
        self.listen_port = listen_port

    def to_dict(self):
        return {
            "socket_path": str(self.socket_path),
            "listen_ip": self.listen_ip,
            "listen_port": self.listen_port
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            socket_path=d["socket_path"],
            listen_ip=d["listen_ip"], listen_port=d["listen_port"]
        )

    def __str__(self):
        return f"{self.listen_ip}:{self.listen_port}"

    def __eq__(self, other):
        return (self.listen_ip, self.listen_port) \
               != (other.listen_ip, other.port)

    def __hash__(self):
        return hash(self.listen_ip + str(self.listen_port))
