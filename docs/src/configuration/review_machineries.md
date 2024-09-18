# Supported machinery modules
This page lists all currently supported virtualization/machinery modules and the required steps for each of them.

!!! note "Note"
    Required Python packages must always be installed in the same virtualenv as Cuckoo.

### Configuring a chosen module

Cuckoo must be told what machinery modules to use. The chosen module(s) can be configured in `$CWD/conf/cuckoo.yaml` under the `machineries` list.
Values in this list must always be lowercase.

```yaml
# A YAML list of all machinery modules that should be enabled and Cuckoo will be using. Machines for
# each of the modules specified here have to be configured in their respective configuration file
# in the conf/machineries directory. It is only possible to run multiple machinery modules if their underlying
# virtualization layers do not interfere with each other.
# Example:
#
# machineries:
#   - machinery1
#   - machinery2
machineries:
- qemu
```

### Modules

All supported machinery modules are listed below


#### QEMU

QEMU is currently de default machinery module. Machines for it can be created with VMCloak. 
The minimum QEMU version is 2.11.

QEMU machine start arguments are read from a JSON file that contains a list of string arguments (devices, network args, etc).

Arguments that cannot be used are: `-incoming` `-monitor` `-qmp` `-loadvm` `-no-shutdown` `-qmp-pretty` `-snapshot`.

Example:

```json
{
  "machine": {
      "start_args": [
          "-thing", "value"
      ]
  }
}
```

Cuckoo assumes that interfaces/bridges of the QEMU machines are already up/will somehow be created. Cuckoo does not assign or 
create any network interfaces. Help on how interfaces can autoamtically be created can be found on [the QEMU wiki](https://wiki.qemu.org/Features/HelperNetworking){target=_blank}.

###### QEMU memory snapshot

Cuckoo uses migration to restore machine to a running state. It does not use disk snapshots. See [this page](https://www.linux-kvm.org/page/Migration){target=_blank} for help on how to create these.

###### QEMU disks

Cuckoo assumes QEMU disks are qcow2 and are created with the `lazy_refcounts=on,cluster_size=2M` options. Cuckoo creates a new disk with those options and
the configured machine disk as the backing disk.

###### Required system packages
- `qemu-system-x86_64`
- `qemu-utils`

```bash
sudo apt install qemu-system-x86_64 qemu-utils
```


#### KVM libvirt
KVM is supported by Cuckoo. Cuckoo speaks to KVM using [Libvirt](https://libvirt.org/docs.html){target=_blank}.

###### Required system packages
- `qemu-kvm`
- `libvirt-daemon` 
- `bridge-utils`
- `virt-manager` 
- `virtinst`

```bash
sudo apt install qemu-kvm libvirt-daemon bridge-utils virt-manager virtinst
```

###### Required Python packages
- `libvirt-python`

```bash
pip install libvirt-python
```
