# System dependencies

!!! info "Environment and requirements"
    - All commands on this page assume you are running Cuckoo under the `cuckoo` user.
    - The assumed operating system is Ubuntu 22.04 or higher.

!!! warning "Warning"
    Please keep in mind that the setcap method is not perfectly safe due to potential security vulnerabilities.
    If the system has other (potentially untrusted) users. We recommend to run Cuckoo on a dedicated system or a trusted environment where the privileged tcpdump execution is contained otherwise.


## Tcpdump
```console
sudo groupadd pcap
sudo adduser cuckoo pcap
sudo chgrp pcap /usr/bin/tcpdump
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump
```

Cuckoo3 uses tcpdump to capture network traffic during malware analysis.  
By default it requires root privileges and Cuckoo should not be run under those privileges.  
To get past that, you can set `setcap` attributes `cap_net_raw` and `cap_net_admin` for `tcpdump`

**Steps**

1. Add a new group named `pcap`.

        sudo groupadd pcap

2. Adding the Cuckoo user to the pcap group.

        sudo adduser cuckoo pcap

3. Change the group ownership of `tcpdump` to `pcap` so that users in pcap group can run `tcpdump` with necessary permissions.

        sudo chgrp pcap /usr/bin/tcpdump

4. Grant `tcpdump` binary the capabilites to capture raw network packets and administer network interfaces.

        sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump

5. Disable `tcpdump` apparmor profile.

        sudo ln -s /etc/apparmor.d/usr.bin.tcpdump /etc/apparmor.d/disable/

6. Add `tcpdump` apparmor profile to disabled list.

        sudo ln -s /etc/apparmor.d/usr.bin.tcpdump /etc/apparmor.d/disable/

7. Remove loaded and active `tcpdump` profile from apparmor.

        sudo apparmor_parser -R /etc/apparmor.d/disable/usr.bin.tcpdump
The `setcap` tool is part of the `libcap2-bin` package.

---

## Apparmor
Perform these steps if you have apparmor enabled. To see if it is, run:
```console
sudo aa-status
```
If `tcpdump` is enabled, it will be among the loaded profiles and you can continue with the next section.

**Add permissions**
```console
echo "~/.cuckoocwd/storage/analyses/* rw" > /etc/apparmor.d/usr.bin.tcpdump
sudo apparmor_parser -r /etc/apparmor.d/usr.bin.tcpdump
```

**Steps**

1. Tcpdump profile by default will not grant permissions to hidden directories such as `.cuckoocwd`. A dirty hack to get around it is to disable default deny rule and add incremental deny rules to rule out all but `cuckoocwd` directory

        sudo sed -i 's|audit deny @{HOME}/.\*/\*\* mrwkl,|audit deny @{HOME}/.[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.c[^u]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cu[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuc[^k]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuck[^o]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cucko[^o]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoo[^c]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckooc[^w]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoocw[^d]\*/\*\* mrwkl,\n  audit deny @{HOME}/.cuckoocwd?\*/\*\* mrwkl,|g' /etc/apparmor.d/usr.bin.tcpdump

2. Add read write permissions to `tcpdump` apparmor profile.
    
        echo "~/.cuckoocwd/storage/analyses/* rw" > /etc/apparmor.d/usr.bin.tcpdump

3. Reload apparmor profile

        sudo apparmor_parser -r /etc/apparmor.d/usr.bin.tcpdump
