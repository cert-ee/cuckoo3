# System dependencies

Here you will find all the dependencies Cuckoo and VMCloak requires to run.  

!!! tip "Friendly reminder"
    For new systems or VM-s, don't forget to `sudo apt-get update` before 
    continuing.

## All-in-one

To install all system dependencies, run the following commands:
```bash
sudo apt-get install -y build-essential \
    software-properties-common \
    unzip \
    curl \
    git \
    python3.10 python3.10-dev python3.10-venv \
    libhyperscan5 libhyperscan-dev \
    libjpeg8-dev zlib1g-dev p7zip-full rar unace-nonfree cabextract \
    yara \
    tcpdump \
    libssl-dev libcapstone-dev \
    uwsgi uwsgi-plugin-python3 \
    nginx \
    genisoimage qemu-system-common qemu-utils qemu-system-x86
```

---

## General dependencies

### Curl
To download and activate the quickstart install script, you need `curl` in your
machine.  

```bash
sudo apt-get install -y curl
```

### Git
Quickstart uses git to download required repositories.

```bash
sudo apt-get install -y git
```

### Python, dev and venv

Python3.10, Python3.10-venv and Python3.10-dev are required to create and activate virtual environments for
Cuckoo and VMCloak.

```bash
sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
```

---

## Cuckoo3 dependencies
### All-in-one
```bash
sudo apt-get install -y libhyperscan5 libhyperscan-dev \
    libjpeg8-dev zlib1g-dev p7zip-full rar unace-nonfree cabextract \
    yara \
    tcpdump \
    libssl-dev libcapstone-dev \
    uwsgi uwsgi-plugin-python3 \
    nginx \
```

### Hyperscan
```bash
sudo apt-get install -y libhyperscan5 libhyperscan-dev
```

The pattern signature engine uses [Hyperscan](https://www.hyperscan.io/about/){:target=_blank} to perform high performance pattern matching.

**System packages**

- `libhyperscan5`
    - Version: >=5.1, <5.3
- `libhyperscan-dev`
    - Version: >=5.1, <5.3

### Sflock
```bash
sudo apt-get install -y libjpeg8-dev zlib1g-dev p7zip-full rar unace-nonfree cabextract
```

Sflock is the library used by Cuckoo to perform all file unpacking and identification. 

### Yara
```bash
sudo apt-get install -y yara
```

[Yara](https://virustotal.github.io/yara/){:target=_blank} is used during static/pre-analysis and post-analysis processing on submitted and collected memory dumps.

### Tcpdump
```bash
sudo apt-get install -y tcpdump
```

[Tcpdump](https://www.tcpdump.org/){:target=_blank} is the network capture tool that Cuckoo uses to create network capture files (PCAPs). A few steps need to be taken before Cuckoo can use Tcpdump. 

For configuration, please see [Configuring Tcpdump](../configuring/system.md#tcpdump){:target=_blank}.

---

## VMCloak dependencies
### All-in-one
```bash
    sudo apt-get install -y genisoimage qemu-system-common qemu-utils qemu-system-x86
```

### Genisoimage
```bash
sudo apt-get install -y genisoimage
```

VMCloak uses `genisoimage` to produce ISO 9660 filesystem images.

### QEMU
```bash
    sudo apt-get install -y qemu-system-common qemu-utils qemu-system-x86
```
VMCloak uses QEMU to create and manage virtual machines.

| Package |  Description |
|---|---|
|`qemu-system-common`|common files for target-specific full system emulation (qemu-system-*)|
|`qemu-utils`|QEMU related image utilities|
|`qemu-system-x86`|full system emulation binaries to emulate the following x86 hardware: x86_64|

### Serving API and web
#### WSGI
```bash 
sudo apt-get install -y uwsgi uwsgi-plugin-python3 nginx
```

| Package |  Description |
|---|---|
|`uwsgi`|WSGI(WebServer Gateway Interface) server|
|`uwsgi-plugin-python3`|Python plugin for uWSGI|
|`nginx`|Webserver|

#### ASGI
Install Python dependencies inside Cuckoo virtual environment
```bash 
python3.10 -m pip install daphne
sudo apt-get install -y nginx
```

| Package |  Description |
|---|---|
|`daphne`|Django ASGI server|
|`nginx`|Webserver|


