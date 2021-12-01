# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import shutil
import tempfile
from pathlib import Path

from cuckoo.common.storage import Paths
from cuckoo.common.config import (
    load_config, render_config_from_typeloaders, load_values,
    ConfigurationError
)
from cuckoo.common.packages import get_conftemplates

from .errors import MachineryError

def _get_existing_loaders(machinery_name):
    conf_path = Paths.config(f"{machinery_name}.yaml", subpkg="machineries")
    if not conf_path.is_file():
        raise MachineryError(
            f"Configuration file '{conf_path}' does not exist."
        )

    try:
        return load_config(conf_path, subpkg="machineries", cache_config=False, check_constraints=False)
    except ConfigurationError as e:
        raise MachineryError(
            f"Failed to load config file {conf_path}. {e}"
        )


def _add_machine(machinery_name, loaders, machine_name, machine_dict):

    if machine_name in loaders["machines"].value:
        raise MachineryError(
            f"Machine with name '{machine_name}' already exists configuration "
            f"file for {machinery_name}"
        )

    new_machine = {machine_name: machine_dict}
    nested_loaders = loaders["machines"].make_typeloaders(new_machine)
    try:
        load_values(new_machine, nested_loaders)
    except ConfigurationError as e:
        raise MachineryError(
            f"One or more configuration errors with '{machinery_name}' "
            f"machine '{machine_name}'. {e}"
        )
    loaders["machines"].value.update(nested_loaders)


def _update_machinery_config(machinery_name, updated_loaders):
    import cuckoo.machineries
    conf_name = f"{machinery_name}.yaml"
    conf_templates = get_conftemplates(cuckoo.machineries)
    machinery_template = conf_templates.get(conf_name)
    if not machinery_template:
        raise MachineryError(
            f"No machinery configuration template was found "
            f"for: {machinery_template}"
        )

    tmpdir = tempfile.mkdtemp()
    tmp_path = Path(tmpdir, conf_name)
    try:
        render_config_from_typeloaders(
            machinery_template, updated_loaders, tmp_path
        )
        shutil.move(tmp_path, Paths.config(conf_name, subpkg="machineries"))
    finally:
        shutil.rmtree(tmpdir)

def delete_machines(machinery_name, machine_names):
    loaders = _get_existing_loaders(machinery_name)
    deleted = []
    for name in machine_names:
        if loaders["machines"].value.pop(name, None):
            deleted.append(name)

    _update_machinery_config(machinery_name, loaders)
    return deleted

def add_machine(machinery_name, machine_name, machine_dict):
    loaders = _get_existing_loaders(machinery_name)
    _add_machine(machinery_name, loaders, machine_name, machine_dict)
    _update_machinery_config(machinery_name, loaders)

_VMCLOAK_MACHINEINFO_FUNC = "vmcloak_info_to_machineconf"
_MACHINEINFO_NAME = "machineinfo.json"

def import_vmcloak_machines(machinery_name, vms_path, machine_names=[]):
    from importlib import import_module

    try:
        machinery = import_module(
            f"cuckoo.machineries.modules.{machinery_name}"
        )
    except ImportError:
        raise MachineryError(
            f"No machinery module named '{machinery_name}' was found"
        )

    machineinfo_reader = getattr(machinery, _VMCLOAK_MACHINEINFO_FUNC, None)
    if not machineinfo_reader:
        raise MachineryError(
            f"Machinery module '{machinery_name}' does not support VMCloak "
            f"machine importing"
        )

    loaders = _get_existing_loaders(machinery_name)
    imported_machines = []
    for vm_path in Path(vms_path).iterdir():
        if machine_names and vm_path.name not in machine_names:
            continue

        machineinfo_path = vm_path.joinpath(_MACHINEINFO_NAME)
        if not machineinfo_path.is_file():
            continue
        try:
            machine_dict, name = machineinfo_reader(machineinfo_path)
        except MachineryError as e:
            raise MachineryError(
                f"Error importing machine from machine info "
                f"{machineinfo_path}. {e}"
            )
        _add_machine(machinery_name, loaders, name, machine_dict)
        imported_machines.append(name)

    if imported_machines:
        _update_machinery_config(machinery_name, loaders)

    return imported_machines
