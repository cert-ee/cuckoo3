# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from sys import getfilesystemencoding

def parse_bool(value):
    """Attempt to parse a boolean value."""
    if value in ("true", "True", "yes", "1", "on"):
        return True
    if value in ("false", "False", "None", "no", "0", "off"):
        return False
    return bool(int(value))

def bytes_to_human(num, suffix='B'):
    # Stolen from Stackoverflow. https://stackoverflow.com/a/1094933
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def fds_to_hardlimit():
    try:
        import resource
    except ImportError:
        return

    min_fds = 4096
    currlimit, hardlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
    startlimit = currlimit
    if currlimit < hardlimit:
        # A ValueError should never occur, since we ask the system to change
        # the soft value to the hard value. It might occur that some other
        # process just happens to edit the hard RLIMIT_NOFILE limit. We
        # are not handling that.
        resource.setrlimit(resource.RLIMIT_NOFILE, (hardlimit, hardlimit))
        currlimit = hardlimit

    if currlimit <= min_fds and currlimit != resource.RLIM_INFINITY:
        raise ResourceWarning(
            f"The current maximum amount of file descriptors is {currlimit}. "
            f"A low limit will likely into errors when the limit is reached. "
            f"The minimum recommended amount is {min_fds}. "
            f"This is largely a guess, as the required amount depends of the "
            f"amount of VMs and behavior being collected."
        )

    return startlimit < currlimit, currlimit

def force_valid_encoding(string):
    """Force file system encoding type by first encoding in as bytes
    with the replace handler, which will replace invalid chars. Then decode
    it back a string."""
    if isinstance(string, str):
        return string.encode(getfilesystemencoding(), "replace").decode()
    elif isinstance(string, bytes):
        return string.decode(getfilesystemencoding(), "replace")

    return str(string)

def browser_to_tag(browser):
    return f"browser_{browser.lower().replace(' ', '_')}"

def tag_to_browser(tag):
    if not tag.startswith("browser_"):
        return None

    parts = tag.split("browser_", 1)
    if len(parts) > 2:
        return None

    return parts[1].replace("_", " ").strip()

def getuser():
    try:
        import pwd
    except ImportError:
        return ""

    from os import getuid

    return pwd.getpwuid(getuid()).pw_name
