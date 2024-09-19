# Configuring VMCloak

!!! note "Environment"
    Configuration commands require sudo permission so they should be run by
    priviledged user.

#### All-in-one configuration
```bash
sudo /home/cuckoo/vmcloak/bin/vmcloak-qemubridge br0 192.168.30.1/24 && \
sudo mkdir -p /etc/qemu/ && echo "allow br0" | sudo tee /etc/qemu/bridge.conf && \
sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper && \
sudo mkdir -p /mnt/win10x64 && sudo mount -o loop,ro /home/cuckoo/win10x64.iso /mnt/win10x64 && \
sudo adduser cuckoo kvm && sudo chmod 666 /dev/kvm
```


1. To create a new subnet, run:

        sudo /home/cuckoo/vmcloak/bin/vmcloak-qemubridge br0 192.168.30.1/24

2. Add the following line `allow br0` to qemu-bridge-helper ACL file (create at `/etc/qemu/bridge.conf`):
        
        sudo mkdir -p /etc/qemu/ && echo "allow br0" | sudo tee /etc/qemu/bridge.conf

3. Add setuid bit to `qemu-bridge-helper` (should be at `/usr/lib/qemu/qemu-bridge-helper`):

        sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper

4. Create a mount point for the iso image:

        sudo mkdir -p /mnt/win10x64 && sudo mount -o loop,ro /home/cuckoo/win10x64.iso /mnt/win10x64

5. Add user to kvm group and change kvm permissions:

          sudo adduser cuckoo kvm && sudo chmod 666 /dev/kvm

