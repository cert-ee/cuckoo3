# Quickstart installation

Cuckoo3 comes with an automation shell script that installs Cuckoo3, VMCloak and related dependencies with predefined configuration - the Quickstart.  

This configuration has been tested and is known to work for general use or experimentation for regular users.  
For more fine tuned installation, please refer to [Manual Installation](#manual-installation)

This is a semi guided installation and will ask for user name and password for
Cuckoo3 installation (Cuckoo3 will be run as non root-user) and Python related
prompts if current Python version does not meet the requirements.  


## Installed components

- Cuckoo3 will be installed with defaults.
- VMCloak will be installed for VM and snapshot creation.
- Qemu will be installed for VMCloak to use.
- Windows 10 will be downloaded for sandboxing.
- Standard Nginx configuration will be created for hosting Cuckoo3 web.

## Installation

For the Quickstart setup, run:
```console
curl -sSf https://cuckoo-hatch.cert.ee/static/install/quickstart | sudo bash
```

---

## Script structure

### Flight checks
Install script does few checks to make sure that is is run with correct user at
different steps and that Python requirements are met.

1. It checks if the script is run with sudo privileges. Some setup parts like
installing system dependencies, creating Cuckoo3 user and installing Python 
related dependencies or repositories.
2. It checks if installed Python version meets the supported version and offers
to install new version
3. It checks if Python venv is present and if not, installs venv for supported 
version.

### Setup options
The script will ask if a new Cuckoo3 user will be created and if VMs will be
created

#### User creation

If `y` is selected then:

- The script creates a new non-privileged user to run Cuckoo3.  
- Is asks for a username and password to create it.  

    !!! note "Remember!"
        Please don't forget the credentials. You need them later to use Cuckoo.

#### VM creation

If `y` is selected then:

- This scipt will download Win10 image
- Install software on it 
- Make snapshots
- Import the VMs to Cuckoo3

### Templates
The script uses "templates" to initiate commands under created Cuckoo3 user.

1. **VMCloak template** - installs VMCloak for VM creation in Cuckoo3 users home 
directory. It also creates VMCloak specific .vmcloak directory in users home for 
vm creation later on.
2. **Cuckoo3 template** - installs Cuckoo3 in Cuckoo3 users home directory. 
It also creates Cuckoo3 specific .cuckoocwd directory in users home for Cuckoo3 
related configurations later on.

---

## Detailed actions with accompanying configuration

### VMCloak
1. Script clones git repo from `https://github.com/cert-ee/vmcloak.git` and 
checkouts `main` branch
2. Script pip installs dependencies
3. VMCloak will create a new network bridge interface named `qemubr0` with 
subnet `192.168.30.1/24`
4. Script will create a new conf file in `/etc/qemu/bridge.conf` with content
`allow qemubr0`
5. setuid bit will be added to `/usr/lib/qemu/qemu-bridge-helper`
6. VMCloak will download Windows 10 image from CERT-EE repository to 
`/home/cuckoo/` as `win10x64.iso`
7. Script will create a mount at `/mnt/win10x64`
8. VMCloak will create a Windows 10 image with settings

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
    |Network adapter|qemubr0|

9. VMCloak will install default software and configuration to Windows 10
10. VMCloak will make 1 snapshot with IP address `192.168.30.10`
11. Delete default Cuckoo3 VM profile
11. Imported newly created VMs to Cuckoo3


