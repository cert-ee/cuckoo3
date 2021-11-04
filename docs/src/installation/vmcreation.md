# Virtual machine creation

The virtual machines are environments in which samples are detonated. This page
describes the requirements that each created virtual machine must have.


## Generic steps and rules

**The Cuckoo agent**

The Cuckoo agent is a small http server that must be part of each analysis machine. It is used
to perform actions such as file uploads and process creation. Because of the actions it needs to perform, it should be run
by a user with administrator privileges.
The agent should be running when a snapshot is restored and must be accessible from outside the machine on TCP port 8000.

It can be downloaded [here](https://raw.githubusercontent.com/jbremer/agent/master/agent.py).

**VM network**

The analysis machine must have their own network and default gateway. The default gateway is where
Cuckoo will start the network capture for traffic from and to a specific machine.

Each machine must:

- Have a unique IP address within the network for a specific virtualization layer/hypervisor.
- Be able to reach the Cuckoo result server. There will be no results if it is not able to.
- Have the Cuckoo agent running and exposed on TCP port 8000.

**Network guidelines and advice**

- For the best analysis results, analysis machine should be able to reach the internet.
- Analysis VMs should not be able to reach other host ports than the result server one.

**Snapshot creation and restoring**

Each sample detonation starts out with the restoring of a snapshot.

The restoring of a snapshot must result into the following:

- The VM operating system is fully booted
- A user is logged in, so that a sample can be detonated.
- The logged in user must have administrator privileges.
- The Cuckoo agent being reachable on TCP port 8000 from outside the machine.

When creating a snapshot, mark it as the 'current' snapshot for the machine or later configure the
name of the snapshot to use in the machinery configuration for the machine.


## Guest OS specific steps

### Windows

#### Threemon (default)

Threemon is a kernel driver. Windows must be patched so that the stager (Tmstage) can actually load
the monitor before the sample detonation occurs. 

Threemon supports Windows 7 and 10 versions:

- Windows 7 with SP1. Build 1706 ([link](https://hatching.dev/hatchvm/win7ultimate.iso))
- Windows 10. Build 1703 ([link](https://hatching.dev/hatchvm/Win10_1703_English_x64.iso))

Download the patch tool [here](https://hatching.dev/hatchvm/patchandgo_amd64.exe)

Only perform these steps after all software has been installed. This should be the last step before
making snapshots.

**Steps**

1. Upload the patchandgo.exe tool to the vm via the agent

        curl "http://<vm ip>:8000/store" -F "file=@<path to patchandgo.exe>" -F "filepath=c:\\patchandgo.exe"

2. Run the patch tool through the agent or by running the executable through cmd.exe.

        curl "http://<vm ip>:8000/execute" -F "command=c:\\patchandgo.exe"

3. Check if there is any error output. If there is not, the analysis machine operating system is now patched.

4. Remove the patching tool.

        curl "http://<vm ip>:8000/remove" -F "path=c:\\patchandgo.exe"

5. Restart Windows, and boot into the patched version if a boot list is presented.

6. Log in to the user (must have administrator privileges) under which sample detonations should happen.

7. Create snapshot(s)

## Adding machines to Cuckoo

Adding machines to Cuckoo can be done with a helper tool or manually. The helper tool only allows for basic configuration.

Machines must be added to the correct/chosen machinery/virtualization layer configuration file. In this example we will be adding
machines for the QEMU machinery module.

Machinery config files can be found at `$CWD/config/machineries/`

### Machinery config machines fields

Each machinery module configuration file has a dictionary of configured machines. An example entry will always exist. This entry should be
removed when using the machinery module. Each entry consists of the following:

**Mandatory fields per machine entry (depends on the machinery module):**

- A unique name in the dictionary
    * The unique identifier that is used by Cuckoo. It is the name of the machine used in reports, the web interface, etc.
- The machine label (`label`)
    - This is the name/identifier of the machine that the virtualization layer/hypervisor/etc uses to refer to the machine. In the example, it is a name chosen by us. In some software this may be a UUID or something else.
- The machine IP (`ip`)
    - The static IP address that is configured inside the machine. This is used to communicated with the machine.
- The machine platform/operating system (`platform`)
    - The platform is required so that Cuckoo knows what machine to chose for a specific sample. Example value: windows
- The platform/operating system version (`os_version`)
    - This is the version of the platform supplied earlier. __This should only contain a version__. Not the full OS name. So "10", not "windows 10". Cuckoo uses this together with the platform to differentiate between machines of the same OS.
- The system architecture: amd64, arm, etc (`architecture`)
    - This is used to select the correct (build of) stager and monitor component for the machine
- The TCP port the agent is listening on (`agent_port`)
    - This is used to deliver and start the stager and the payload.

**Optional fields per entry (depends on the machinery module):**

- Snapshot name (`snapshot`)

    * The name of (or path to) the snapshot to use to restore the machine before sample detonation. This is optional because most
        virtualization layers/hypervisors allow a 'current' snapshot to be configured for a vm. If this is configured, this field can be left empty.

- Mac address (`mac_address`)

    * Currently unused, can be used in future features.

- Network interface (`interface`)
    * The network interface name that should be used to dump network traffic for this vm. If not supplied the interface that is configured for the machinery module will be used.

- Machine tags (`tags`)
    * Machine tags is a list of strings that are used to identify installed software/particular settings inside a vm. If .NET framework or Adobe PDF reader is installed, the tags should be: `dotnet` and `pdfreader`.
    * To populate the 'supported browser' list in the web UI or API, one or more machines with `browser_browsername` tags must exist. These tags are automatically translated to a list of browsers. Use `_` instead of spaces. An example would be
    `browser_internet_explorer`.
    
    * The tags are used by Cuckoo to find a machine that can detonate a submitted sample. The file identification stage of Cuckoo determines what dependencies are needed for specific file types. These dependency names are tied to tag names. This mapping can be found in `$CWD/conf/processing/identification.yaml`. Automated file dependency tag assigning only occurs if it is enabled in `$CWD/conf/cuckoo.yaml`.

#### Machine adding command


Adding machines to the machinery config using a helper tool: `cuckoo machine add`.
The tool will write a new entry to the machines dictionary of the specific machinery module.

The help output looks as follows:

```bash
Usage: cuckoo machine add [OPTIONS] MACHINERY_NAME MACHINE_NAME
                          [CONFIG_FIELDS]...

  Add a machine to the configuration of the specified machinery.
  config_fields be all non-optional configuration entries in key=value
  format.

Options:
  --tags TEXT  A comma separated list of tags that identify what
               dependencies/software is installed on the machine.

```

As an example, suppose we want to add a QEMU Windows 10 VM called win10x64_1 and has the IP 192.168.30.101. 
We will also assume it has .NET and Adobe pdf reader installed and add the tags for those.
We can add this machine using the following command:

```bash
cuckoo machine add qemu --tags dotnet,adobepdf win10x64_1 ip=192.168.30.101 qcow2_path=/home/cuckoo/.vmcloak/vms/qemu/win10_1/disk.qcow2 snapshot_path=/home/cuckoo/.vmcloak/vms/qemu/win10_1/memory.snapshot machineinfo_path=/home/cuckoo/.vmcloak/vms/qemu/win10_1/machineinfo.json platform=windows os_version=10 architecture=amd64 interface=br0

```

When opening the `$CWD/conf/machineries/qemu.yaml` config file, it will now look like this:

```yaml
# Specify the name of the network interface/bridge that is the default gateway
# for the QEMU machines.
# Example: br0
interface: br0

# Make disposable copies of machine disk images here. Copies are created each
# time the machine is restored. This directory path must be writable and
# readable. If this not specified, the directory of the 'qcow2_path' of each
# machine will be used.
disposable_copy_dir:

# The paths to binaries used to create disks, restore, and
# start virtual machines
binaries:
  # Path to qemu-img.
  qemu_img: /usr/bin/qemu-img
  # Path to qemu-system-x86_64
  qemu_system_x86_64: /usr/bin/qemu-system-x86_64

machines:
  example1:
    # The path to the QCOW2 disk image. This disk will be used as a backing
    # for each disposable copy when restoring and booting the machine. The parent
    # directory is used for disposable disk copies if no disposable_copy_dir
    # is given. This means the directory must be readable and writable.
    # Should be made with the 'lazy_refcounts=on,cluster_size=2M' options.
    qcow2_path: /home/cuckoo/.vmcloak/vms/qemu/win10_1/disk.qcow2
    # The filepath to the machine memory snapshot. A 'QEMU suspend to disk image'.
    # This is restored using the '-incoming' parameter. Restoring this should
    # result in a running machine with the agent listening on the specified port.
    snapshot_path: /home/cuckoo/.vmcloak/vms/qemu/win10_1/memory.snapshot
    # The filepath to a JSON dump containing information on how to start this
    # machine. This file is generated by VMCloak. It can be made by hand:
    # {'machine': {'start_args': []}}, where the start args value is a list of arguments
    # for qemu, using %DISPOSABLE_DISK_PATH% where the path to the qcow2 should
    # be inserted by Cuckoo.
    machineinfo_path: /home/cuckoo/.vmcloak/vms/qemu/win10_1/machineinfo.json
    # The static IP address that has been configured inside of the machine.
    ip: 192.168.30.101
    # The operating system platform installed on the machine.
    platform: windows
    # A string that specifies the version of the operating system installed.
    # Example: "10" for Windows 10, "7" for Windows 7, "18.04" for Ubuntu 18.04.
    os_version: "10"
    # The system architecture. Amd64, ARM, etc. This is used to
    # select the correct stager and monitor builds/component for the machine.
    architecture: amd64
    # The TCP port of the agent running on the machine.
    agent_port: 8000
    # (Optional) The MAC address of the network interface of the machine that is used to connect to
    # to the resultserver and the internet.
    mac_address: null
    # (Optional) Specify the name of the network interface that should be used
    # when dumping network traffic from this machine with tcpdump.
    interface: br0
    # Machine tags that identify the installed software and other characteristics of the machine.
    # These are used to select the correct machine for a sample that has dependencies. *Notice*: correct tags are
    # crucial in selecting machines that can actually run a submitted sample.
    # Existing automatic tags can be found in the conf/processing/identification.yaml config.
    tags:
    - dotnet
    - adobepdf            
```

#### Machine importing command

Cuckoo can also import machines created by VMCloak. To do this we first need to know the 'VMs path' of VMCloak.
This is located in at `VMCLOAK_CWD/vms/`. If we made the machines for qemu, they will be located in the `qemu` subdirectory (`VMCLOAK_CWD/vms/qemu).

The helper tool we can use to import machine is: `cuckoo machine import`.
The tool will write a new entry to the machines dictionary of the specific machinery module for each
discovered machine in the VMCloak vms machinery directory. 

The help output looks as follows:

```bash
Usage: cuckoo machine import [OPTIONS] MACHINERY_NAME VMS_PATH
                             [MACHINE_NAMES]...

  Import all or 'machine names' from the specified VMCloak vms path to the
  specified machinery module.

```

An an example situation: we create 10 machines with VMCloak for QEMU and the VMCloak CWD is at /home/cuckoo/.vmcloak.
We can run the following command to import all the machines.

```bash
cuckoo machine import qemu /home/cuckoo/.vmcloak/vms/qemu
```