# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

existing = {
    "machine1": {
        "platform": "windows10",
        "tags": {"tag1", "tag2"},
        "ip": "192.168.56.101",
        "mac": "0a:00:27:00:00:00"
    },
    "machine2": {
        "platform": "windows7",
        "tags": {"tag1", "tag2"},
        "ip": "192.168.56.102",
        "mac": "0a:00:27:00:00:01"
    }
}

platforms = {
    "windows10": ["machine1"],
    "windows7": ["machine2"],
}

def exists(platform="", tags=[]):
    tags = set(tags)

    machines = []
    for machine in existing.values():
        if machine["platform"] == platform:
            if not tags:
                return True

            machines.append(machine)

    if not platform:
        machines = existing.values()

    for machine in machines:
        if tags.issubset(machine["tags"]):
            return True

    return False

def name_exists(machine):
    return machine in existing

def names_exist(machines):
    for m in machines:
        if m not in existing:
            return False
