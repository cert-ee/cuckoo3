# System (package) settings

This page contains settings/changes that need to be made to system (packages) before Cuckoo can be used.

!!! info "Assumptions"
    - All commands on this page assume you are running Cuckoo under the 'cuckoo' user.
    - The assumed operating system is Ubuntu 18.04 or higher.

### Tcpdump

Tcpdump requires root privileges, but Cuckoo should never run as root. This means you will have to 
set specific Linux capabilities to the binary.

1. Adding the Cuckoo user to the pcap group.

```bash
sudo groupadd pcap
sudo adduser cuckoo pcap
sudo chgrp pcap /usr/sbin/tcpdump
```

2. Allowing non-root users to create network captures using `setcap`.

!!! warning "Warning"
    Please keep in mind that the setcap method is not perfectly safe due to potential security vulnerabilities.
    If the system has other (potentially untrusted) users. We recommend to run Cuckoo on a dedicated system or a trusted environment where the privileged tcpdump execution is contained otherwise.


The `setcap` tool is part of the `libcap2-bin` package. 
```bash
sudo setcap cap_net_raw,cap_net_admin=eip /usr/sbin/tcpdump
```

3. Only perform this step if AppArmor is enabled. It allows tcpdump to write to Cuckoo's CWD. Not performing this step when AppArmor is enabled can result in 'Permission denied' error when Cuckoo starts tcpdump for network captures.

3.1 To allow tcpdump to write in Cuckoo's CWD, we should add the CWD location to the tcpdump AppArmor profile.
Open `/etc/apparmor.d/usr.sbin.tcpdump` and add the following line with your CWD.

`<Your CWD location>/storage/analyses/* rw`

3.1 Reload the tcpdump AppArmor profile

```bash
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.tcpdump
```
