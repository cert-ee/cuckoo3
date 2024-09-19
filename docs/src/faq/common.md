# Common errors

## VMCloak

### failed to create tun device: Operation not permitted

**Error message:**

    failed to create tun device: Operation not permitted
    qemu-system-x86_64: -netdev type=bridge,br=qemubr0,id=net0: bridge helper failed

**Solution**

Make sure that `qemu-bridge-helper` has setuid bit set

    sudo chmod u+s /usr/lib/qemu/qemu-bridge-helper

---

### Failed to create 'image_name'

**Error message:**

    vmcloak ERROR: Failed to create 'image_name':
    ...
    ValueError: Image /home/cuckoo/.vmcloak/image/win10base.qcow2 already exists

**Solution**

Delete the image and run `vagrant init` again

    rm /home/cuckoo/.vmcloak/image/win10base.qcow2
    vmcloak --debug init ...

---
