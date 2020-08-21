# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os

from importlib import import_module
from pkgutil import iter_modules

class NotACuckooPackageError(Exception):
    pass

def find_cuckoo_packages(do_import=True):
    """Returns a list of tuples containing the full package name,
    a subpackage name, and imported module (optional) of all
     packages part of the cuckoo namespace"""
    import cuckoo
    found = [("cuckoo", "", cuckoo)]

    module_iter = iter_modules(cuckoo.__path__)
    for _, name, is_package in module_iter:
        if is_package:
            fullname = f"cuckoo.{name}"
            if not do_import:
                found.append((fullname, name, None))
            else:
                found.append((fullname, name, import_module(fullname)))

    return found

def is_cuckoo_package(cuckoo_package):
    if not hasattr(cuckoo_package, "__path__"):
        return False

    path = os.path.join(cuckoo_package.__path__[0], "data", ".cuckoopackage")
    return os.path.isfile(path)

def get_data_dir(cuckoo_package):
    if not is_cuckoo_package(cuckoo_package):
        raise NotACuckooPackageError(
            f"{cuckoo_package} is not a Cuckoo package"
        )

    return os.path.join(cuckoo_package.__path__[0], "data")

def get_conftemplate_dir(cuckoo_package):
    return os.path.join(get_data_dir(cuckoo_package), "conftemplates")

def get_cwdfiles_dir(cuckoo_package):
    cwddata = os.path.join(get_data_dir(cuckoo_package), "cwd")
    if os.path.isdir(cwddata):
        return cwddata

    return ""

def has_conftemplates(cuckoo_package):
    return os.path.isdir(get_conftemplate_dir(cuckoo_package))

def get_conftemplates(cuckoo_package):
    if not has_conftemplates(cuckoo_package):
        return []

    path = get_conftemplate_dir(cuckoo_package)
    templates = {}
    for filename in os.listdir(path):
        if filename.endswith(".yaml.jinja2"):
            typeloaderkey = filename.replace(".jinja2", "")
            templates[typeloaderkey] = os.path.join(path, filename)

    return templates

def get_conf_typeloaders(cuckoo_package):
    if not is_cuckoo_package(cuckoo_package):
        raise NotACuckooPackageError(
            f"{cuckoo_package} is not a Cuckoo package"
        )

    pkgname = f"{cuckoo_package.__name__}.config"
    try:
        config = import_module(pkgname)
    except ModuleNotFoundError:
        return None

    if not hasattr(config, "typeloaders"):
        return None

    return config.typeloaders

def enumerate_plugins(package_path, namespace, class_, attributes={}):

    """Import plugins of type `class` located at `dirpath` into the
    `namespace` that starts with `module_prefix`. If `dirpath` represents a
    filepath then it is converted into its containing directory. The
    `attributes` dictionary allows one to set extra fields for all imported
    plugins. Using `as_dict` a dictionary based on the module name is
    returned."""

    try:
        dirpath = import_module(package_path).__file__
    except ImportError as e:
        raise ImportError(
            f"Unable to import plugins from package path: {package_path}. {e}"
        )
    if os.path.isfile(dirpath):
        dirpath = os.path.dirname(dirpath)

    for fname in os.listdir(dirpath):
        if fname.endswith(".py") and not fname.startswith("__init__"):
            module_name, _ = os.path.splitext(fname)
            try:
                import_module(f"{package_path}.{module_name}")
            except ImportError as e:
                raise ImportError(
                    "Unable to load the Cuckoo plugin at %s: %s. Please "
                    "review its contents and/or validity!" % (fname, e)
                )

    subclasses = class_.__subclasses__()[:]

    plugins = []
    while subclasses:
        subclass = subclasses.pop(0)

        # Include subclasses of this subclass (there are some subclasses, e.g.,
        # Libvirt machineries such as KVM. KVM<-Libvirt<-Machinery
        subclasses.extend(subclass.__subclasses__())

        # Check whether this subclass belongs to the module namespace that
        # we are currently importing. It should be noted that parent and child
        # namespaces should fail the following if-statement.
        if package_path != ".".join(subclass.__module__.split(".")[:-1]):
            continue

        namespace[subclass.__name__] = subclass
        for key, value in attributes.items():
            setattr(subclass, key, value)

        plugins.append(subclass)

    return sorted(plugins, key=lambda x: x.__name__.lower())
