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
- kvm
```

### Modules

All supported machinery modules are listed below

#### KVM
KVM is supported by Cuckoo and is currently the default module. Cuckoo speaks to KVM using [Libvirt](https://libvirt.org/docs.html){target=_blank}.

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
