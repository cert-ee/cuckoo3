# Installing VMCloak

!!! note "Environment and requirements"

    Make sure you are logged in as your Cuckoo user and that you have:  

    - installed all system dependencies form the [VMCloak dependencies section](dependencies.md#vmcloak-dependencies){:target=_blank}

Cuckoo uses virtual machines to execute for its analyses. VMCloak is a great tool to help create and configure such virtual machines.

## All-in-one install

```console
cd ~ && git clone https://github.com/cert-ee/vmcloak.git
cd vmcloak
python3.10 -m venv venv
source venv/bin/activate
python3.10 -m pip install .
```

**Steps**

1. Clone the repository to your home directory.
        
        cd ~ && git clone https://github.com/cert-ee/vmcloak.git

2. Create and activate Python virtual environment.
        
        cd vmcloak && python3.10 -m venv venv && source venv/bin/activate

3. Install Python dependencies.

        python3.10 -m pip install .

---

## Downloading an image

You can download iso files for VMCloak CERT-EE repository with `vmcloak isodownload` command.  
Replace the `--win10x64` with the appropriate option from [Supported sandbox environments](../about/cuckoo.md#supported-sandbox-environments){:target=_blank}.

You can download the desired image by running:
            
        vmcloak isodownload --win10x64 --download-to /home/cuckoo/win10x64.iso

---

## Configuring VMCloak
!!! note "Environment"

    This step requires you to switch to a privileged user to run the commands below.

### All-in-one configuration
```bash
sudo /home/cuckoo/vmcloak/bin/vmcloak-qemubridge br0 192.168.30.1/24
sudo mkdir -p /etc/qemu/ && echo "allow br0" | sudo tee /etc/qemu/bridge.conf
sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper
sudo mkdir -p /mnt/win10x64 && sudo mount -o loop,ro /home/cuckoo/win10x64.iso /mnt/win10x64
sudo adduser cuckoo kvm && sudo chmod 666 /dev/kvm
```

**Steps**  

1. Create a new subnet.

        sudo /home/cuckoo/vmcloak/bin/vmcloak-qemubridge br0 192.168.30.1/24

2. Add `allow br0` to qemu-bridge-helper ACL file (create at `/etc/qemu/bridge.conf`).
        
        sudo mkdir -p /etc/qemu/ && echo "allow br0" | sudo tee /etc/qemu/bridge.conf

3. Add setuid bit to `qemu-bridge-helper` (should be at `/usr/lib/qemu/qemu-bridge-helper`).

        sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper

4. Create a mount point for the iso image.

        sudo mkdir -p /mnt/win10x64 && sudo mount -o loop,ro /home/cuckoo/win10x64.iso /mnt/win10x64

5. Add user to kvm group and change kvm permissions.

          sudo adduser cuckoo kvm && sudo chmod 666 /dev/kvm

---

## Create virtual machines
!!! note "Environment"

    Switch back to your cuckoo user for the rest of this section.

To create virtual machines, run:
```bash
vmcloak --debug init --win10x64 --hddsize 128 --cpus 2 --ramsize 4096 --network 192.168.30.0/24 --vm qemu --vrde --vrde-port 1 --ip 192.168.30.2 --iso-mount /mnt/win10x64 win10base br0
vmcloak --debug install win10base --recommended
vmcloak --debug snapshot --count 1 win10base win10vm_ 192.168.30.10
```

For more detailed documentation, please see [Creating virtual machines](../creating/vms.md){:target=_blank}.

## Next Steps

1. If you don't have Cuckoo3 installed, proceed with [Installing Cuckoo3](cuckoo.md){:target=_blank}.  
2. If you have Cuckoo3 installed and need to import the virtual machines, please see [Importing virtual machines](cuckoo.md#importing-virtual-machines){:target=_blank}.

---

## Usage

### Download ISO-s

```bash
vmcloak isodownload --help
```

``` { .bash .no-copy}
Usage: vmcloak isodownload [OPTIONS]

  Download the recommended operating system ISOs for Cuckoo 3. These are
  specific OS versions/builds.

Options:
  --download-to TEXT  The 'filepath' to write the ISO to. Will go to
                      /home/cuckoo/.vmcloak/iso otherwise.
  --win7x64           The recommended Windows 7 x64 ISO for Cuckoo 3
  --win10x64          The recommended Windows 10 x64 ISO for Cuckoo 3
```

### Create images

```bash
vmcloak init --help
```

``` { .bash .no-copy }
Usage: vmcloak init [OPTIONS] NAME ADAPTER

  Create a new image with 'name' attached to network (bridge) 'adapter'.

Options:
  --python-version TEXT  Python version to install on VM.
  --product TEXT         Windows 7 product version.
  --serial-key TEXT      Windows Serial Key.
  --iso-mount TEXT       Mounted ISO Windows installer image.
  --win10x64             This is a Windows 10 64-bit instance.
  --win7x64              This is a Windows 7 64-bit instance.
  --vrde-port INTEGER    Specify the remote display port.
  --vrde                 Enable the remote display (RDP or VNC).
  --vm-visible           Start the Virtual Machine in GUI mode.
  --resolution TEXT      Screen resolution.  [default: 1024x768]
  --tempdir TEXT         Temporary directory to build the ISO file.  [default:
                         /home/cuckoo/.vmcloak/iso]
  --hddsize INTEGER      HDD size in GB  [default: 256]
  --ramsize INTEGER      Memory size
  --cpus INTEGER         CPU count.  [default: 1]
  --dns2 TEXT            Secondary DNS server.  [default: 8.8.4.4]
  --dns TEXT             DNS Server.  [default: 8.8.8.8]
  --gateway TEXT         Guest default gateway IP address (IP of bridge
                         interface)
  --network TEXT         The network to use in CIDR notation. Example:
                         192.168.30.0/24. Uses VM platform default if not
                         given.
  --port INTEGER         Port to run the Agent on.  [default: 8000]
  --ip TEXT              Guest IP address to use
  --iso TEXT             Specify install ISO to use.
  --vm TEXT              Virtual Machinery.  [default: qemu]
```

### Install software/dependencies

```bash
vmcloak install --help
```

``` { .bash .no-copy }
Usage: vmcloak install [OPTIONS] NAME [DEPENDENCIES]...

Install dependencies on an image. Dependency settings are specified using
name.setting=value. Multiple settings per dependency can be given.

Options:
  --vm-visible
  --vrde               Enable the VirtualBox Remote Display Protocol.
  --vrde-port INTEGER  Specify the VRDE port.
  --force-reinstall    Reinstall even if already installed by VMCloak.
  --no-machine-start   Do not try to start the machine. Assume it is somehow
                       already started and reachable.
  -r, --recommended    Install and perform recommended software and
                       configuration changes for the OS.
```

### Make manual changes

```bash
vmcloak modify --help
```

``` { .bash .no-copy }
Usage: vmcloak modify [OPTIONS] NAME

  Start the given image name to apply manual changes

Options:
  --vm-visible
  --vrde               Enable the VirtualBox Remote Display Protocol.
  --vrde-port INTEGER  Specify the VRDE port.
  --iso-path TEXT      Path to an iso file to attach as a drive to the
                       machine.
```

### Create snapshots
```bash
vmcloak snapshot --help
```

``` { .bash .no-copy }
Usage: vmcloak snapshot [OPTIONS] NAME VMNAME [IP]

  Create one or more snapshots from an image

Options:
  --resolution TEXT    Screen resolution.
  --ramsize INTEGER    Amount of virtual memory to assign. Same as image if
                       not specified.
  --cpus INTEGER       Amount of CPUs to assign. Same as image if not
                       specified.
  --hostname TEXT      Hostname for this VM.
  --vm-visible         Start the Virtual Machine in GUI mode.
  --count INTEGER      The amount of snapshots to make.  [default: 1]
  --vrde               Enable the VirtualBox Remote Display Protocol.
  --vrde-port INTEGER  Specify the VRDE port.
  --interactive        Enable interactive snapshot mode.
  --nopatch            Do not patch the image to be able to load Threemon
```
