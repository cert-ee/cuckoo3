# System dependencies

This page lists all system dependencies that must be installed. The required machinery module dependencies depend on the machinery
module you are using. See the [machineries](machineries.md) section for more information.

### Hyperscan

The pattern signature engine uses [Hyperscan](https://www.hyperscan.io/about/){target=_blank} to perform high performance pattern matching.

**System packages**

- `libhyperscan5`
    - Version: >=5.1, <5.3
- `libhyperscan-dev`
    - Version: >=5.1, <5.3

```bash
apt install libhyperscan5 libhyperscan-dev
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

```bash
apt install libjpeg8-dev zlib1g-dev p7zip-full rar unace-nonfree cabextract
```

### Yara

[Yara](https://virustotal.github.io/yara/){target_blank} is used during static/pre-analysis and post-analysis processing on submitted and collected memory dumps.

**System packages**

- `yara`

```bash
apt install yara
```

### Tcpdump

[Tcpdump](https://www.tcpdump.org/){target_blank} is the network capture tool that Cuckoo uses to create network capture files (PCAPs). A few steps need to be taken before Cuckoo can use Tcpdump. 

**System packages**

- `tcpdump`

```bash
apt install tcpdump
```

**Configuration steps**

See [tcpdump configuration](../configuration/system.md#tcpdump) page for the steps to perform.