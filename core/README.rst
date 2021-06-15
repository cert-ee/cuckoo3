Cuckoo 3

Currently Cuckoo 3 only runs on Linux.

Perform the following steps to be able to run Cuckoo 3.
1. ./install.sh
2. apt install libvirt-dev
3. pip install libvirt-python
4. Run `cuckoo createcwd`

5. Configure your KVM vms in .cuckoocwd/conf/machineries/kvm.yaml
    * VMs must have a 'current' snapshot.
    * The snapshot must be made of a running and logged in administrator user.
    * The Cuckoo agent (min version 10) must be running on port TCP/8000 when the snapshot is restored.

6. Run `cuckoo getmonitor <monitor zip path>`

7. Run `cuckoo`

8. Run `cuckoo submit [OPTIONS] <target path>`
