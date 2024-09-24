# General
Cuckoo3 and VMCloak installations come in two flavors: Quickstart and manual.

## Quickstart
This method installs Cuckoo3 and VMCloak in an opinionated manner.
It is best suited if you just want to check out Cuckoo3 and play around with it. For that, we recommend you run the script in a virtual environment using [Vagrant](https://www.vagrantup.com/){:target="_blank"}.

For more in-depth information on what Quickstart installer does, please see our [Quickstart](quickstart.md){:target="_blank"}  documentation.

!!! note "Important"
    Quickstart installation produces a single node setup.

## Manual

Manual installation allows you to be more flexible about how you set up your Cuckoo3 and VMCloak.  
You can choose which virtualization solution you want to use, which network bridge, how many nodes to run, and much more.

We recommend you install everything in this order:

1. [System dependencies](dependencies.md){:target=_blank}
2. [VMCloak](vmcloak.md){:target=_blank}
2. [Cuckoo3](cuckoo.md){:target=_blank}

## Nodes

- Default/single node.
    - The main and task-running Cuckoo3 components run on the same machine. They are automatically started when starting Cuckoo3. This is the type of setup that fits most scenarios.
- Distributed, one main node and one or more task-running nodes.
    - The main node is a separate machine. One or more task-running nodes run on other servers/locations. Each task running node may be reachable over a network.

## Why is VMCloak here?
We recommend using QEMU and VMCloak to handle creating the images and snapshots for Cuckoo. That is why we have added VMCloak documentation into Cuckoo documentation.  
We recommend you install and configure VMcloak first, create virtual machines and snapshots after that, and then proceed to installing Cuckoo3.
