# Machinery modules

!!! warning "Unverified"

    This is from the old documentation and needs verification.  
    It may contain errors, bugs or outdated information.

This page describes how to create new module
for not yet supported machineries.
Notably, Key steps that aren't apparent
or require extended reversing of the code base are discussed here.

This page can also be used to extend an existing module.

### How to create a machinery module

**1. Creating a basic Template**

To accomplish this step, first create a file like:
`$A/machineries/cuckoo/machineries/modules/<module_name>.py`.
In the python file, create a class which represents the machinery
you wish to implement.
The class must inherit the abstract class `Machinery`.

Additionally, the `machines` module, `cfg` function and `errors` module
must be imported, to get access to machines and configuration data
as well as machinery specific exceptions.
Importing `CuckooGlobalLogger` will also come in handy for logging behaviour.

Finally the basic class should look like this:

```python
from cuckoo.common import machines
from cuckoo.common.config import cfg
from cuckoo.common.log import CuckooGlobalLogger

from .. import errors
from ..abstracts import Machinery

log = CuckooGlobalLogger(__name__)

class Machinery_Name(Machinery):
    pass

```
!!! note "Note"
    The class won't be loaded by Cuckoo yet
    and will be make loadable at a later point of this Tutorial.

**2. Define configuration constrains**
!!! warning "Warning"
    This Step can't be skipped or an exception will occur while
    Cuckoo tries to load the configuration file corresponding to the module.

To enable Cuckoo to load the corresponding configuration file
of the new machinery module, an entry must be created in the `typeloaders`
Variable of the `cuckoo.machineries.config` module.
The `cuckoo.machineries.config` module is found in
`$A/machineries/cuckoo/machineries/config.py`.

It is a good idea to copy an existing entry and modify it
for ones own module.

An example can be seen here:
```python
...
typeloaders = {
    "qemu.yaml": {
        "interface": config.NetworkInterface(
            default_val="br0", must_exist=True, must_be_up=False
        ),
        "disposable_copy_dir": config.DirectoryPath(
            allow_empty=True, must_exist=True, writable=True
        ),
        "binaries": {
            "qemu_img": config.FilePath(
                "/usr/bin/qemu-img", readable=True, executable=True
            ),
            "qemu_system_x86_64": config.FilePath(
                default_val="/usr/bin/qemu-system-x86_64", readable=True,
                executable=True
            )
        },
        "machines": config.NestedDictionary("example1", {
                "qcow2_path": config.FilePath(default_val="/home/cuckoo/.vmcloak/vms/qemu/win10_1/disk.qcow2", readable=True),
                "snapshot_path": config.FilePath(default_val="/home/cuckoo/.vmcloak/vms/qemu/win10_1/memory.snapshot", readable=True),
                "machineinfo_path": config.FilePath("/home/cuckoo/.vmcloak/vms/qemu/win10_1/machineinfo.json", readable=True),
                "ip": config.String(default_val="192.168.30.101"),
                "mac_address": MACAddress(to_lower=True, allow_empty=True,
                                          required=False),
                "platform": config.String(
                    default_val="windows", to_lower=True
                ),
                "os_version": config.String(default_val="10"),
                "architecture": config.String(
                    default_val="amd64", to_lower=True
                ),
                "interface": config.NetworkInterface(
                    allow_empty=True, must_exist=True, must_be_up=False,
                    required=False
                ),
                "agent_port": config.Int(
                    default_val=8000, required=False, min_value=1,
                    max_value=2**16-1
                ),
                "tags": config.List(
                    config.String, ["exampletag1", "exampletag2"],
                    allow_empty=True
                )
        })
    }
}
...
```

**3. Making the module loadable**

To make the module loadable, one has to create a variable
called `name` in the machinery class
and initialize it with the name of the module.
Now the module looks like this:

```python
from cuckoo.common import machines
from cuckoo.common.config import cfg
from cuckoo.common.log import CuckooGlobalLogger

from .. import errors
from ..abstracts import Machinery

log = CuckooGlobalLogger(__name__)

class Machinery_Name(Machinery):
    name = "Machinery_Name"

```

**4. Populating the Module with the minimum functions to work**

The `Machinery` class suggest that the seven functions `restore_start`,
`norestore_start`, `stop`, `acpi_stop`, `state`, `dump_memory`
and `handle_paused` must be implemented for a machinery module to work.
This is not the case as can be seen in the given modules `QEMU`
and `kvm`.

The minimum functions to be implemented are: `restore_start`, `stop`
and `state`. This functions will be discuss in the following:

```python
def restore_start(self, machine):
    raise NotImplementedError
```

The `restore_start` function is called to revert to a VMs snapshot
and is used for the standard analysis routine.

In this function the status of the machine must be checked
and if the machine is turned off, the machine can be safely restored.

```python
def stop(self, machine):
    raise NotImplementedError
```

The `stop` function is called when the analysis concluded.
The VM will then be shut downed in an ungraceful manner.
This is equal to pulling the cord on your computer.
As the VM will be restored for the next analysis this isn't a problem.
Also a check must take place to figure out if the VM is running,
before stopping it.

```python
def state(self, machine):
    raise NotImplementedError
```

The `state` function is used to get a Cuckoo compatible state
of a given VM. This function is heavily used to ensure that
no invalid action are applied to VM. (e.g. Turning off a already
powered of machine)

!!! note "Note"
    For examples check the modules `QEMU` and `kvm`
    in `$A/machineries/cuckoo/machineries/abstracts`

### Config-Template

After fisnishing the machinery-module, you will want to create a Config-Template.
This will prevent `cuckoo createcwd` from producing an error and will create
an example config from installation on.

The Config-Template is a jinja2 document. It's name must chosen like this:
`<module-name>.yaml.jinja2` and be located in `cuckoo3/machineries/cuckoo/machineries/data/conftemplates`
The file must contain the configuration constrains defined earlier.

!!! note "Note"
    Using an existing Template is a great starting point for this step.

### Optional machinery functions

```python
def norestore_start(self, machine):
    raise NotImplementedError
```

As the name suggest, this function starts the VM like `restore_start`.
But unlike `restore_start` the given snapshot isn't restored.

```python
def acpi_stop(self, machine):
    raise NotImplementedError
```

The same as the `stop` function but shutdowns the machine
gracefully instead of virtually pulling the plug.

```python
def dump_memory(self, machine, path):
    raise NotImplementedError
```

Does exactly what the name suggest. This may not be possible with all
machineries. Prominently the `kvm` module does not support this function.

```python
def handle_paused(self, machine):
    raise NotImplementedError
```

Some machineries may restore the VM to a paused state, like the `QEMU`
machinery. This function is used to unpaused the machine.

!!! note "Note"
    It is also a good idea to override existing machinery functions
    if you need to alter their functionality. (e.g. `load_machines`
    gets overwritten by the `kvm` module)

