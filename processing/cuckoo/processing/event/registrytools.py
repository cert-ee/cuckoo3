# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

def normalize_winregistry(path):
    if not path or path[0] != "\\":
        return path

    path = path.lower()

    if path.startswith("\\registry\\machine\\"):
        path = path.replace("\\registry\\machine", "hklm", 1)

        if path[4:].startswith("\\software\\wow6432node\\"):
            return f"{path[:13]}{path[25:]}"
        elif path[4:].startswith("\\system\\currentcontrolset\\"):
            return path.replace("currentcontrolset", "controlset001", 1)
        elif path[4:].startswith("\\system\\controlset00"):
            if len(path) <= 24 or path[24] == "1" or "0" > path[24] > "9":
                return path
            if len(path) == 25:
                return f"{path[:24]}1"

            if len(path) >= 26 and path[25] == "\\":
                return f"{path[:24]}1{path[25:]}"

        return path

    if path.startswith("\\registry\\user\\"):
        userendslash = path[15:].find("\\")

        if userendslash != -1:
            userendslash += 15
            user_part = path[15:userendslash]
        else:
            # No slash after the user part.
            user_part = path[15:]


        if path[userendslash:].startswith("\\wow6432node\\"):
            path = f"{path[:userendslash]}{path[userendslash + 12:]}"

        if user_part.startswith("s-") and user_part.count("-") == 7:
            if user_part.endswith("_classes"):
                return f"hkcu\\software\\classes{path[15 + len(user_part):]}"

            return f"hkcu{path[15 + len(user_part):]}"

        return f"hku{path[14:]}"

    return path
