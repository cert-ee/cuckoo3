# Quickstart installation

Cuckoo3 comes with an automation shell script that installs Cuckoo3, VMCloak, and related dependencies with predefined configuration — the Quickstart.

This configuration has been tested and is known to work for general use or experimentation for regular users. For more fine-tuned installation, please refer to [Manual Installation](#manual-installation)

This is a semi-guided installation and will ask for user name and password for Cuckoo3 installation (Cuckoo3 will be run as non-root-user) and Python-related prompts if the current Python version does not meet the requirements.

## Quickstart will install:
- System dependencies

- Cuckoo3 will be installed with a custom configuration
- VMCloak will be installed for VM and snapshot creation
- Qemu will be installed for VMCloak to use
- Windows 10 will be downloaded for sandboxing
- Standard Nginx configuration will be created for hosting Cuckoo3 web.

## Installation

For the Quickstart setup, run:
```console
curl -sSf https://cuckoo-hatch.cert.ee/static/install/quickstart | sudo bash
```

---

## Script structure

### Flight checks
The install script does a few checks to make sure that it is run with the correct user at different steps and that Python requirements are met.

1. It checks if the script is run with sudo privileges. Some setup parts like installing system dependencies, creating Cuckoo3 users, and installing Python-related dependencies or repositories.
2. Checks if you are running the supported Ubuntu 22.04 release.

### Interactive part

#### User creation

If `y` is selected, then:

- The script creates a new non-privileged user to run Cuckoo3.
- It asks for a username and password to create it.

    !!! note "Remember!"
        Please don't forget the credentials. You need them later to use Cuckoo.

If `n` is selected, then:

- The script asks for the username and password for the previously created user.
**NOTE!** Make sure the user does not have sudo privileges.

#### VM creation

If `y` is selected, then:

- This script will download the Windows 10 image form cert-ee.
- Install software on it.
- Make snapshots.

### Templates
The script uses "templates", which are basically helper functions, to initiate commands under the created Cuckoo3 user.

- **install_vmcloak_with** - installs VMCloak for VM creation in Cuckoo3 users home directory. It also creates VMCloak-specific .vmcloak directory in users home for vm creation later on.
- **install_cuckoo_with** - installs Cuckoo3 in Cuckoo3 users home directory. It also creates .cuckoocwd directory in users home for Cuckoo3-related configurations later on.
- **configure_cuckoo_for** - Unpacks monitor and signatures to `cuckoocwd`. It also builds documentation, performs Django's `collectstatic` command, and generates uwsgi and nginx configurations into users cuckoo3 directory.
- **download_images_for** - Downloads Windows 10 image from cert-ee.
- **create_vms_for** - This command creates an iso image for Windows 10 with agent, installs software on it, and creates 3 snapshots.
- **configure_vms_for** - Imports VMs to Cuckoo3 and deletes the example machine. It also runs database migrations.
- **run_cuckoo_for** - This allows bash to run Cuckoo user specific commands.

---

## Detailed actions with accompanying configuration

### System dependencies
Quickstart installs the following dependencies for:

- building Python packages
    - build-essential
    - software-properties-common
- unpacking monitor and signatuers
    - unzip
- hyperscan
    - libhyperscan5
    - libhyperscan-dev
- Sflock
    - libjpeg8-dev
    - zlib1g-dev
    - p7zip-full
    - rar
    - unace-nonfree
    - cabextract
- Yara
    - yara
- Tcpdump
    - tcpdump
- Python dependencies
    - libssl-dev libcapstone-dev
- VM creation with VMCloak
    - genisoimage
    - qemu-system-common
    - qemu-utils
    - qemu-system-x86
- serving Cuckoo3 frontend
    -uwsgi
    - uwsgi-plugin-python3
    - nginx
- Python3
    - python3.10
    - python3.10-venv
    - python3.10-dev - required for python C headers

### VMCloak
Quickstart will:  

1. clone git repo from `https://github.com/cert-ee/vmcloak.git` and
checkout `main` branch
2. pip installs dependencies
3. create a new network bridge interface named `br0` with
subnet `192.168.30.1/24`
4. create a new conf file in `/etc/qemu/bridge.conf` with content
`allow br0`
5. set setuid bit for `/usr/lib/qemu/qemu-bridge-helper`
6. download Windows 10 image from CERT-EE repository to
`/home/cuckoo/` as `win10x64.iso`
7. create a mount at `/mnt/win10x64`
8. create a Windows 10 image with settings

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

9. install default software and configuration to Windows 10
10. make 3 snapshots with IP address starting from `192.168.30.10`
11. delete default Cuckoo3 VM qemu profile
11. import created VMs to Cuckoo3.

### User configuration
User will be added to kvm and pcap groups. First is to be able to create VMs with Qemu and second is to use tcpdump
Quickstart will also disable tcpdump apparmor profile.

### Cuckoo web
For Cuckoo3 frontend to work, Quickstart needs to change some configuration values:

1. it will add a new subnet 192.168.68.0/24 to allowed subnets
2. add STATIC_ROOT location
3. make directories for STATIC_ROOT and change ownership to Cuckoo3 user
4. add user to www-data group
5. remove uwsgi configuration if it exists and deliver a new configuration to `/etc/uwsgi/apps-available/`
6. symlinks uwsgi to `apps-enabled`
7. does the same for nginx
8. changes nginx listen port 8080
9. restarts `uwsgi` and `nginx` services
10. creates helper script in the home of user who ran the script. It helps bring up network interface and mount iso. `sudo ~/.helper_script.sh`.

Last step Quickstart takes in run `cuckoo --debug` which runs cuckoo in debug mode
