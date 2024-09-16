# System dependencies

Here you can find all dependencies Cuckoo3 requires to run.  
We have an opinionated way of installing Cuckoo and these dependencies reflect that opinion.  

!!! note "Friendly reminder"
    For new systems or VM-s, don't forget to `sudo apt-get update` before 
    continuing.

## All-in-one

To install all system dependencies, run the following commands:
```console
sudo apt-get install -y build-essential \
    software-properties-common \
    curl \
    unzip \
    python3.10 python3.10-dev python3.10-venv \
    libhyperscan5 libhyperscan-dev \
    libjpeg8-dev zlib1g-dev p7zip-full rar unace-nonfree cabextract \
    yara \
    tcpdump \
    libssl-dev libcapstone-dev \
    genisoimage qemu-system-common qemu-utils qemu-system-x86 \
    uwsgi uwsgi-plugin-python3 \
    nginx
```

---

## Detailed dependencies

### Curl
To download and activate the quickstart install script, you need `curl` in your
machine.  

```console
sudo apt-get -y install curl
```

### Git
Quickstart uses git to download requined repositories.

```console
sudo apt-get -y install git
```

### Python dev and venv

Python3.10-venv and Python3.10-dev arerequired to create and activate virtual environments for
Cuckoo3 and VMCloak.

```console
sudo apt-get -y install python3.10-venv python3.10-dev
```

### Hyperscan

The pattern signature engine uses [Hyperscan](https://www.hyperscan.io/about/){target=_blank} to perform high performance pattern matching.

**System packages**

- `libhyperscan5`
    - Version: >=5.1, <5.3
- `libhyperscan-dev`
    - Version: >=5.1, <5.3

```console
sudo apt-get install -y libhyperscan5 libhyperscan-dev
```

### Sflock

Sflock is the library used by Cuckoo to perform all file unpacked and identification. It has multiple dependencies that it needs
to be able to unpack and identify a variety of archive and file types.

**System packages**

- `libjpeg8-dev`
- `zlib1g-dev`
- `p7zip-full`
- `rar`
- `unace-nonfree`
- `cabextract`

```console
sudo apt-get install -y libjpeg8-dev zlib1g-dev p7zip-full rar unace-nonfree cabextract
```

### Yara

[Yara](https://virustotal.github.io/yara/){target_blank} is used during static/pre-analysis and post-analysis processing on submitted and collected memory dumps.

**System packages**

- `yara`

```console
sudo apt-get install -y yara
```

### Tcpdump

[Tcpdump](https://www.tcpdump.org/){target_blank} is the network capture tool that Cuckoo uses to create network capture files (PCAPs). A few steps need to be taken before Cuckoo can use Tcpdump. 

**System packages**

- `tcpdump`

```console
sudo apt-get install -y tcpdump
```

**Configuration steps**

See [tcpdump configuration](../configuration/system.md#tcpdump) page for the steps to perform.
