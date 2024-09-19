# Installing VMCloak

!!! note "Environment and requirements"

    Make sure you are logged in as your Cuckoo user and that you have:  

    - installed all system dependencies form the [VMCloak dependencies section](dependencies.md#vmcloak-dependencies){:target=_blank}

You need VMs for Cuckoo to run analyses on. VMCloak is a great tool to help create and configure such VMs.

## All-in-one install

```console
git clone https://github.com/cert-ee/vmcloak.git && \
cd vmcloak && \
python3.10 -m venv venv && \
source venv/bin/activate && \
python3.10 -m pip install .
```

**Steps**

1. Clone the repository (replace the `<destination>` with desired location).
        
        git clone https://github.com/cert-ee/vmcloak.git <destination>

2. Create and activate Python virtual environment.
        
        python3.10 -m venv venv && source venv/bin/activate

3. Install Python dependencies.

        python3.10 -m pip install .

---

## Downloading an image

CERT-EE hosts images for VMCloak to download.  
Replace the `--win10x64` with the appropriate option form 
[Supported sandbox environments](../about/cuckoo.md#supported-sandbox-environments).  


Download the desired image, run:
            
        vmcloak isodownload --win10x64 --download-to /home/cuckoo/win10x64.iso

---

## Configuring VMCloak
!!! note "Environment"
    Configuration commands require sudo permission, so they should be run by a priviledged user.

### All-in-one configuration
```bash
sudo /home/cuckoo/vmcloak/bin/vmcloak-qemubridge br0 192.168.30.1/24 && \
sudo mkdir -p /etc/qemu/ && echo "allow br0" | sudo tee /etc/qemu/bridge.conf && \
sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper && \
sudo mkdir -p /mnt/win10x64 && sudo mount -o loop,ro /home/cuckoo/win10x64.iso /mnt/win10x64 && \
sudo adduser cuckoo kvm && sudo chmod 666 /dev/kvm
```

**Steps**  

1. To create a new subnet, run:

        sudo /home/cuckoo/vmcloak/bin/vmcloak-qemubridge br0 192.168.30.1/24

2. Add `allow br0` to qemu-bridge-helper ACL file (create at `/etc/qemu/bridge.conf`):
        
        sudo mkdir -p /etc/qemu/ && echo "allow br0" | sudo tee /etc/qemu/bridge.conf

3. Add setuid bit to `qemu-bridge-helper` (should be at `/usr/lib/qemu/qemu-bridge-helper`):

        sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper

4. Create a mount point for the iso image:

        sudo mkdir -p /mnt/win10x64 && sudo mount -o loop,ro /home/cuckoo/win10x64.iso /mnt/win10x64

5. Add user to kvm group and change kvm permissions:

          sudo adduser cuckoo kvm && sudo chmod 666 /dev/kvm

---

## VM creation
For detailed information about VM creation with VMCloak, please refer to [Creating virtual machines](../creating/vms.md).

---

## Usage

### ISO download

    vmcloak isodownload --help

    Usage: vmcloak isodownload [OPTIONS]

      Download the recommended operating system ISOs for Cuckoo 3. These are
      specific OS versions/builds.

    Options:
      --download-to TEXT  The 'filepath' to write the ISO to. Will go to
                          /home/cuckoo/.vmcloak/iso otherwise.
      --win7x64           The recommended Windows 7 x64 ISO for Cuckoo 3
      --win10x64          The recommended Windows 10 x64 ISO for Cuckoo 3

### Image creation and OS installation

    vmcloak init --help

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

### Installing software/dependencies

    vmcloak install --help
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

### Manual changes

    vmcloak modify --help
    Usage: vmcloak modify [OPTIONS] NAME

      Start the given image name to apply manual changes

    Options:
      --vm-visible
      --vrde               Enable the VirtualBox Remote Display Protocol.
      --vrde-port INTEGER  Specify the VRDE port.
      --iso-path TEXT      Path to an iso file to attach as a drive to the
                           machine.

### Snapshot creation
    vmcloak snapshot --help
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
