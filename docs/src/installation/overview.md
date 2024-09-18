# General
Cuckoo3 and VMCloak installations come in two flavors: quickstart and manual.

## Quickstart
This method installs Cuckoo3 and VMCloak in an opinionated manner.
This is best suited if you just want to check out Cuckoo3 and play around with it. For that, we recommend you run the script in a virtual environment. We recommend Vagrant for this.

For more in-depth information on what Quickstart installer does, please see [Quickstart](quickstart.md){:target="_blank"}  documentation.

!!! note "Important"
    Quickstart installation produces a single node setup.

## Manual

Manual installation allows you to be more flexible about how you set up your Cuckoo3.
You can choose which virtualization solution you want to use, which network bridge to use, how many nodes to run, and much more.

For more in-depth information, please see [Cuckoo3 installation](cuckoo.md){:target="_blank"} 

## Nodes

- Default/single node.
    - The main and task-running Cuckoo3 components run on the same machine. They are automatically started when starting Cuckoo3. This is the type of setup that fits the most scenarios.
- Distributed, one main node and one or more task-running nodes.
    - The main Cuckoo3 node runs on one machine. One or more task-running Cuckoo3 nodes run on other servers/locations. Each task running node may be reachable over a network.

## Why is VMCloak here?
Since we recommend using QEMU and VMCloak to handle creating the images and snapshots for Cuckoo3, we have dedicated a section for it in this documentation. Since a lot of Cuckoo3 configurations require the presents of VM configuration, we recommend you set up VMCloak and QEMU-related VM creation and snapshot creation before diving into installing Cuckoo3.
