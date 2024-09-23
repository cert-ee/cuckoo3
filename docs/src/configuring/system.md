# System dependencies

!!! note "Environment and requirements"
    - All commands on this page assume you are running Cuckoo under the `cuckoo` user.
    - The assumed operating system is Ubuntu 22.04 or higher.

!!! warning "Warning"
    Please keep in mind that the setcap method is not perfectly safe due to potential security vulnerabilities.
    If the system has other (potentially untrusted) users. We recommend running Cuckoo on a dedicated system or a trusted environment where the privileged tcpdump execution is contained otherwise.


## Tcpdump
```console
sudo groupadd pcap
sudo adduser cuckoo pcap
sudo chgrp pcap /usr/bin/tcpdump
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump
```

Cuckoo3 uses `tcpdump` to capture network traffic during malware analysis.  
By default, it requires root privileges, and Cuckoo should not be run with escalated privileges.  
To get around that, you can set `setcap` attributes `cap_net_raw` and `cap_net_admin` for `tcpdump`

**Steps**

1. Add a new group named `pcap`.

        sudo groupadd pcap

2. Adding the Cuckoo user to the pcap group.

        sudo adduser cuckoo pcap

3. Change group ownership of `tcpdump` to `pcap` so that users in pcap group can run `tcpdump` with necessary permissions.

        sudo chgrp pcap /usr/bin/tcpdump

4. Grant `tcpdump` binary the capabilities to capture raw network packets and administer network interfaces. The `setcap` tool is part of the `libcap2-bin` package.

        sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump

---

## Apparmor
Perform these steps if you have apparmor enabled. To see if it is, run:
```console
sudo aa-status
```
If `tcpdump` is enabled, it will be among the loaded profiles, and you can continue with the next section.

**Add permissions**
```console
sudo sed -i 's|audit deny @{HOME}/.\*/\*\* mrwkl,|audit deny @{HOME}/.[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.c[^u]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cu[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuc[^k]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuck[^o]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cucko[^o]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoo[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckooc[^w]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoocw[^d]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoocwd?\*/\*\* mrwkl,|g' /etc/apparmor.d/usr.bin.tcpdump
sudo apparmor_parser -r /etc/apparmor.d/usr.bin.tcpdump
```

**Steps**

1. Tcpdump profile by default will not grant permissions to hidden directories such as `.cuckoocwd`. A dirty hack to get around it is to overwrite default deny rule `audit deny @{HOME}/.*/** mrwkl` in `/etc/apparmor.d/usr.bin.tcpdump` and add incremental deny rules to rule out all but `cuckoocwd` directory.

        sudo sed -i 's|audit deny @{HOME}/.\*/\*\* mrwkl,|audit deny @{HOME}/.[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.c[^u]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cu[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuc[^k]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuck[^o]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cucko[^o]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoo[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckooc[^w]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoocw[^d]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoocwd?\*/\*\* mrwkl,|g' /etc/apparmor.d/usr.bin.tcpdump

    It should look like this in the profile:

        audit deny @{HOME}/.[^c]*/** mrwkl,
        audit deny @{HOME}/.c[^u]*/** mrwkl,
        audit deny @{HOME}/.cu[^c]*/** mrwkl,
        audit deny @{HOME}/.cuc[^k]*/** mrwkl,
        audit deny @{HOME}/.cuck[^o]*/** mrwkl,
        audit deny @{HOME}/.cucko[^o]*/** mrwkl,
        audit deny @{HOME}/.cuckoo[^c]*/** mrwkl,
        audit deny @{HOME}/.cuckooc[^w]*/** mrwkl,
        audit deny @{HOME}/.cuckoocw[^d]*/** mrwkl,
        audit deny @{HOME}/.cuckoocwd?*/** mrwkl,

3. Reload apparmor profile

        sudo apparmor_parser -r /etc/apparmor.d/usr.bin.tcpdump
