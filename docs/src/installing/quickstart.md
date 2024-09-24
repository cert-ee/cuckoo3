# Quickstart

!!! note "Requirements"

    Before you run the Quickstart, make sure you meet the [requirements](../about/cuckoo.md#cuckoo3-requirements){:target=_blank}.

Cuckoo comes with an interactive and automated shell script that installs Cuckoo3, VMCloak, and related dependencies with predefined configuration.  
This configuration has been tested and is known to work for general use or experimentation for regular users. For more manual installation, please refer to [Installing Cuckoo3](cuckoo.md){:target=_blank}.  

Quickstart will:

- create:
    - New user and groups
    - A network interface
    - Mountpoint
    - Helper script
    - Directories
- modify:
    - Apparmor profile
- install:
    - System dependencies
    - Cuckoo with a custom configuration
    - VMCloak
    - QEMU
- download:
    - Windows 10
- generate:
    - Nginx configuration for serving Cuckoo

## Installation

For the Quickstart setup, run this command in your console:
```console
curl -sSf https://cuckoo-hatch.cert.ee/static/install/quickstart | sudo bash
```

---

## Script structure

### Flight checks
The install script does a few checks to make sure that it is run with the correct user at different steps and that host requirements are met. 

1. It checks if the script is run with sudo privileges. Some setup parts like installing system dependencies, creating Cuckoo user, creating network interfaces require elevated privileges. 
2. Checks if you are running the supported Ubuntu 22.04 release.

### Interactive part

#### User creation

If `y` is selected, then:

- The script creates a new non-privileged user to for Cuckoo.
- It asks for a username and password to create it.

    !!! tip "Don't forget"
        Please don't forget the credentials. You need them later to use Cuckoo.

If `n` is selected, then:

- The script asks for the username and password for the previously created user.
**NOTE!** Make sure the user does not have sudo privileges.

#### VM creation

If `y` is selected, then:

- This script will download the Windows 10 image form CERT-EE.
- Install software on it.
- Make 3 snapshots.

#### Web options

- The script will create a new directory and change ownership to Cuckoo user.
- Modify Cuckoo configuration so that Nginx can use correct location for static files.

### Templates
The script uses "templates", which are basically helper functions, to initiate commands under the created Cuckoo user.

- **install_vmcloak_with** - installs VMCloak for VM creation in Cuckoo users home directory. It also creates VMCloak-specific .vmcloak directory in users home for vm creation later on.
- **install_cuckoo_with** - installs Cuckoo in Cuckoo users home directory. It also creates .cuckoocwd directory in users home for Cuckoo-related configurations later on.
- **configure_cuckoo_for** - Unpacks monitor and signatures to `cuckoocwd`. It also builds documentation, performs Django's `collectstatic` command, and generates uwsgi and nginx configurations into users cuckoo3 directory.
- **download_images_for** - Downloads Windows 10 image from cert-ee.
- **create_vms_for** - This command creates an iso image for Windows 10 with agent, installs software on it, and creates 3 snapshots.
- **configure_vms_for** - Imports VMs to Cuckoo and deletes the example machine. It also runs database migrations.
- **run_cuckoo_for** - This allows bash to run Cuckoo user specific commands.

---

## Detailed actions with accompanying configuration

### System dependencies
Quickstart installs the following system dependencies

|Purpose|Packages|Comments|
|---|---||
|general|git||
|building Python packages|build-essential<br>software-properties-common||
|unpacking monitor and signatures|unzip||
|hyperscan|libhyperscan5<br>libhyperscan-dev||
|Sflock|libjpeg8-dev <br>zlib1g-dev <br>p7zip-full <br>rar <br>unace-nonfree <br>cabextract||
|Yara|yara||
|Tcpdump|tcpdump||
|Python dependencies|libssl-dev <br>libcapstone-dev||
|VM creation with VMCloak| genisoimage <br>qemu-system-common <br>qemu-utils <br>qemu-system-x86||
|serving Cuckoo frontend| uwsgi <br> uwsgi-plugin-python3 <br> nginx||
|Python3|python3.10 <br>python3.10-venv <br>python3.10-dev|-dev is required for python C headers|

### VMCloak
Quickstart will:  

1. Clone git repo from `https://github.com/cert-ee/vmcloak.git` and
checkout `main` branch.
2. Install dependencies with `pip`.
3. Create a new network bridge interface named `br0` with
subnet `192.168.30.1/24`.
4. Create a new conf file in `/etc/qemu/bridge.conf` with content
`allow br0`.
5. Set setuid bit for `/usr/lib/qemu/qemu-bridge-helper`.
6. Download Windows 10 image from CERT-EE repository to `/home/cuckoo/` as `win10x64.iso`.
7. Create a mount at `/mnt/win10x64`.
8. Create a Windows 10 image with settings.

    |Parameter|Value|
    |---|---|
    |Disk|128GB|
    |CPU|2|
    |RAM|4096|
    |Subnet|192.168.30.0/24|
    |Virtual Machinery|qemu|
    |Remote Display (RDP/VNC)|true|
    |Remote Display port|1 (offset 5900)|
    |Guest IP address|192.168.30.2|
    |Mount point|`/mnt/win10x64`|
    |VM name|win10base|
    |Network adapter|br0|

9. Install default software and configuration to Windows 10.
10. Make 3 snapshots with IP address starting from `192.168.30.10`.
11. Delete default Cuckoo VM qemu profile.
11. Import created VMs to Cuckoo.

### User configuration
Quickstart will add user to kvm and pcap groups.  
First is to be able to create VMs with Qemu and second is to use tcpdump.  

### Apparmor `tcpdump` profile
It will add an exception to `tcpdump` profile so that it has permissions to write to `~/.cuckoocwd` directory.

### Cuckoo web
For Cuckoo frontend to work, Quickstart needs to change some configuration values:

1. It will add a new subnet 192.168.68.0/24 to allowed subnets.
2. Add STATIC_ROOT location.
3. Make directories for STATIC_ROOT and change ownership to Cuckoo user.
4. Add user to www-data group.
5. Remove uWSGI configuration if it exists and deliver a new configuration to `/etc/uwsgi/apps-available/`.
6. Symlinks uwsgi to `apps-enabled`.
7. Does the same for Nginx.
8. Changes nginx to listen on port 8080.
9. Restarts `uwsgi` and `nginx` services.
10. Creates helper script in the home of user who ran the script. It helps bring up network interface and mount iso. `sudo ~/.helper_script.sh`.

Last step Quickstart takes in run Cuckoo in debug mode with `cuckoo --debug`.
