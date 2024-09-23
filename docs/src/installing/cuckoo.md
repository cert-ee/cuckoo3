# Installing Cuckoo3

!!! note "Environment and requirements"

    Make sure you are logged in as your Cuckoo user (`cuckoo` in our context) and that you have:  

    - installed all system dependencies from the [Cuckoo3 dependencies section](dependencies.md#cuckoo3-dependencies){:target=_blank}
    - meet the requirements to [run Cuckoo3](../about/cuckoo.md#cuckoo3-requirements)
    - virtual machines made by VMCloak by following [Creating VMs with VMCloak](../creating/vms.md){:target=_blank}

## All-in-one install

```bash
git clone https://github.com/cert-ee/cuckoo3.git
cd cuckoo3
python3.10 -m venv venv
source venv/bin/activate
./install.sh
cuckoo createcwd
cuckoo getmonitor monitor.zip
unzip -o -d ~/.cuckoocwd/signatures/cuckoo signatures.zip
```

**Steps**

1. Clone the repository (replace the `<destination>` with the desired location).
        
        git clone https://github.com/cert-ee/cuckoo3.git <destination>

2. Create and activate Python virtual environment.
        
        python3.10 -m venv venv && source venv/bin/activate

3. Install Cuckoo Python dependencies using the install script.

        ./install.sh

4. Create Cuckoo configuration directory.

        cuckoo createcwd

5. Unpack monitor and stager, which are needed to gather behavioral data.

        cuckoo getmonitor monitor.zip

6. Unpack signatures.

        unzip -o -d ~/.cuckoocwd/signatures/cuckoo signatures.zip

---

## Configuring

For a full list of configurations, please see [Configuring Cuckoo3](../configuring/cuckoo.md){:target=_blank}.

### Importing virtual machines

```bash
cuckoo machine import qemu /home/cuckoo/.vmcloak/vms/qemu
cuckoo machine delete qemu example1
```

**Steps**

1. Imports VMs and snapshots you have made with VMCloak.
        
        cuckoo machine import qemu /home/cuckoo/.vmcloak/vms/qemu

2. Delete the default `example1` configuration in `~/.cuckoocwd/conf/machineries/qemu.yaml`.
        
        cuckoo machine delete qemu example

All machine configurations can be found in `~/.cuckoocwd/conf/machineries/`.  
All configuration files have comments above the fields if you wish to manually adjust them.

### Cuckoo3 
```bash
cuckoomigrate database all
```

Before you run Cuckoo, you need to migrate the databases.

---

## Start Cuckoo3
```bash
cuckoo
```

This command starts Cuckoo backend. To run in debug mode, use the `--debug` flag.

---

## Installing distributed mode

!!! warning "Unverified"

    This is from the old documentation.  
    We are currently reviewing and updating distributed installation.

The following steps are for a distributed Cuckoo setup. A distributed Cuckoo setup consists
of:

* One main node
    * This is the node to which submissions occur, it performs all result processing, and runs services such as the web interface and API.
    It keeps track of all created analyses. The analyses are scheduled to a task running node that fit the requirements of an analysis. It knows all
    task running nodes.

* One or more task running nodes
    * This node accepts, runs tasks, and stores the collected behavioral logs. It has an API that the main node uses to tell it to run a task or to download a result for a task. This node type is "dumb"; it does not know about other nodes or even the main node. This node is also where Cuckoo rooter should be running if automatic network routing is desired.

#### Task running node(s)

We start with setting up one or more task running nodes:

**1. Perform the following for each task running node.**

Follow steps 1 to 5 of the [BROKEN: Installing Cuckoo](#installing-cuckoo\) steps.

**2. Start the node(s) by running the following command**

    cuckoonode --host <listen ip> --port <listen port>

**3. Copy and store the node API key somewhere.**

Open `$CWD/conf/distributed.yaml` and find the `node_settings` section. It will have a generated key after the `api_key` field.
Write this key down, together with the IP and port of the node.

**3. Ensure the node API is reachable on the specified port.**

Communicate with the API by trying to reach the following API endpoint:

    curl "http://<node ip>:<node port>/machines" -H "Authorization: token <api key>"

It should return a list of available analysis machines.

#### The main node

**1. Perform the following steps.**

Follow steps 1 to 3 and 6 and 7 of the [BROKEN: Installing Cuckoo](#installing-cuckoo\) steps.

**2. Adding the task running nodes.**

Open `$CWD/conf/distributed.yaml` and find the `remote_nodes` section. This is a dictionary of remote task running nodes.
For each created/installed task running node, add an entry.

```yaml
<A node name>:
  api_url: http://<node ip>:<node port>
  api_key: <node api key>
```

**3. Start Cuckoo in distributed mode**

Starting Cuckoo in distributed mode will cause Cuckoo to request information from each node on startup. Any connection error with one of
the nodes will result in the stopping of startup.

If the startup is successful, the setup is ready for submission.

    cuckoo --distributed

---

## Usage

### cuckoo

```bash
cuckoo --help
```

``` { .bash .no-copy }
Usage: cuckoo [OPTIONS] COMMAND [ARGS]...

Options:
  --cwd TEXT          Cuckoo Working Directory
  --distributed       Start Cuckoo in distributed mode
  -v, --verbose       Enable debug logging, including for non-Cuckoo modules
  -d, --debug         Enable debug logging
  -q, --quiet         Only log warnings and critical messages
  --cancel-abandoned  Do not recover and cancel tasks that are abandoned and
                      still 'running'

Commands:
  api         Start the Cuckoo web API (development server)
  createcwd   Create the specified Cuckoo CWD
  getmonitor  Use the monitor and stager binaries from the given Cuckoo...
  importmode  Start the Cuckoo import controller.
  machine     Add machines to machinery configuration files.
  submit      Create a new file/url analysis.
  web         Start the Cuckoo web interface (development server)
```

### Machine adding command

```bash
cuckoo machine add --help
```

``` { .bash .no-copy }
Usage: cuckoo machine add [OPTIONS] MACHINERY_NAME MACHINE_NAME
                          [CONFIG_FIELDS]...

  Add a machine to the configuration of the specified machinery. config_fields
  be all non-optional configuration entries in key=value format.

Options:
  --tags TEXT  A comma separated list of tags that identify what
               dependencies/software is installed on the machine.
```

The tool will write a new entry to the `machines` dictionary of the specific machinery module.

**Example:**

Suppose we want to add a QEMU Windows 10 VM called win10x64_1 and has the IP 192.168.30.1.
We will also assume it has .NET and Adobe pdf reader installed and add the tags for those.
We can add this machine using the following command:

```bash
cuckoo machine add qemu --tags dotnet,adobepdf win10x64_1 ip=192.168.30.101 qcow2_path=/home/cuckoo/.vmcloak/vms/qemu/win10_1/disk.qcow2 snapshot_path=/home/cuckoo/.vmcloak/vms/qemu/win10_1/memory.snapshot machineinfo_path=/home/cuckoo/.vmcloak/vms/qemu/win10_1/machineinfo.json platform=windows os_version=10 architecture=amd64 interface=br0
```

This creates an entry into `~/.cuckoocwd/conf/machineries/qemu.yaml` config file with the following information:

``` { .yaml .no-copy }
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
    ip: 192.168.30.1
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

### Machine importing command

```bash
cuckoo machine import --help
```

``` { .yaml .no-copy }
Usage: cuckoo machine import [OPTIONS] MACHINERY_NAME VMS_PATH
                             [MACHINE_NAMES]...

  Import all or 'machine names' from the specified VMCloak vms path to the
  specified machinery module.

Options:
  --help  Show this message and exit.
```

Cuckoo can also import machines created by VMCloak. To do this, we first need to know the 'VMs path' of VMCloak.
This is located at `~/.vmcloak/vms/`. If we make the machines with QEMU, they will be located in the `qemu` subdirectory (`~/.vmcloak/vms/qemu`).

The helper tool we can use to import machines is: `cuckoo machine import`.
The tool will write a new entry to the machines dictionary of the specific machinery module for each
discovered machine in the VMCloak vms machinery directory.

**Example:**  

An example situation: we create 10 machines with VMCloak for QEMU and the VMCloak CWD is at /home/cuckoo/.vmcloak.
We can run the following command to import all the machines.

```bash
cuckoo machine import qemu /home/cuckoo/.vmcloak/vms/qemu
```
