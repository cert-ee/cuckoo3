# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.


from string import ascii_lowercase

def normalize_winpath(path):
    if not path:
        return ""

    path = path.lower()
    if path[0] not in ascii_lowercase:
        return path

    if len(path) <= 9:
        return path

    if path[2:9] == "\\users\\":
        slashat = path[9:].find("\\")

        if slashat == -1:
            return path

        # Re-create a new path where the username is replaced with 'user'.
        return f"{path[:9]}user{path[9 + slashat:]}"

    if path[2:9] == "\\progra":
        slashat = path[3:].find("\\")

        if slashat == -1:
            slashat = len(path) - 3

        programdir = path[3:slashat + 3]

        # x64, x86 and 8dot3 paths AKA progra~2
        if slashat > 3 and programdir == "program files" or\
                programdir == "program files (x86)" or \
                programdir[:slashat - 1] == "progra~":
            return f"{path[:3]}program files{path[3 + slashat:]}"

    return path
