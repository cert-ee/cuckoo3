## Cuckoo installation

This page describes the steps required to install Cuckoo. Cuckoo can be set up in two ways:

* Default/single node.
    * The main and task running Cuckoo components run on the same machine. They are automatically started
    when starting Cuckoo. This is the type of setup that fits the most scenarios.

* Distributed, one main node and one or more task running nodes.
    * The main Cuckoo node runs on one machine. One or more task running Cuckoo nodes run on other servers/locations.
    Each task running node much be reachable over a network.


### Installing Cuckoo

The following steps are for a normal/generic Cuckoo setup. This is the type of setup fits the most scenarios.

**1. Install all [system dependencies](deps.md)**

!!! note "Note"
    `$A` is used as the location where the delivery archive was extracted.


**2. Installing Cuckoo 3 from a delivery archive.**

2.1 Create and activate a new Python >=3.6 virtualenv

2.2 Navigate to the `$A/cuckoo/cuckoo3` directory and run install.sh


    ./install.sh


!!! note "Note"
    When specifying `$CWD`, this refers to the Cuckoo working directory that is used.

**3. Creating the Cuckoo CWD.**

By default this will be in `$HOME/.cuckoocwd`. The CWD is where
Cuckoo stores all its results, configurations, and other files. The CWD will be referred to as $CWD.


    cuckoo createcwd

**4. Installing the stager and monitor binaries** 

The next step is to install the stager and monitor binaries. These are components that 
are uploaded to the analysis vm and perform the actual behavioral collection.

    cuckoo getmonitor $A/cuckoo/monitor.zip

**5. Choosing a machinery module and configuring machines.**

6.1 Choose the virtualization/machinery software from the [machineries modules page](machineries.md) and perform the required steps listed.

6.2 Create analysis VMs taking into account the [requirements listed here](vmcreation.md).

6.3 Add the VMs to the chosen machinery configuration as [described here](vmcreation.md#adding-machines-to-cuckoo).

**6. Installing the Cuckoo signatures**.

 Unpack everything from `$A/cuckoo/signatures.zip` to `$CWD/signatures/cuckoo`

**7. Start Cuckoo**

Cuckoo can now be started using the following command:

    cuckoo --cwd <cwd path>

Or with the default cwd:

    cuckoo


### Installing Cuckoo distributed

The following steps are for a distributed Cuckoo setup. A distributed Cuckoo setup consists
of:

* One main node
    * This is the node to which submissions occur, it performs all result processing, and runs services such as the web interface and API.
    It keeps track of all created analyses. The analyses are scheduled to a task running node that fit the requirements of an analysis. It knows all
    task running nodes.

* One or more task running nodes
    * This node accepts, runs tasks, and stores the collected behavioral logs. It has an API that the main node uses to tell it to run a task or to download a result for a task. This node type is "dumb" it does not know about other nodes or even the main node. This node is also where Cuckoo rooter should be running if automatic network routing is desired.

#### Task running node(s)

We start with setting up one or more task running nodes:

**1. Perform the following for each task running node.**

Follow steps 1 to 5 of the [Installing Cuckoo](#installing-cuckoo) steps.

**2. Start the node(s) by running the following command**

    cuckoonode --host <listen ip> --port <listen port>

**3. Copy and store the node API key somewhere.**

Open `$CWD/conf/distributed.yaml` and find the `node_settings` section. It will have a generated key after the `api_key` field.
Write this key down, together with the IP and port of the node.

**3. Ensure the node API is reachable on the specified port.**

Communicate with the API by trying to reach the following API endpoint:

    curl "http://<node ip>:<node port>/machines" -H "Authorization: token <api key>"

It should return a list of available analysis machines.

#### The main node

**1. Perform the following steps.**

Follow steps 1 to 3 and 6 and 7 of the [Installing Cuckoo](#installing-cuckoo) steps.

**2. Adding the task running nodes.**

Open `$CWD/conf/distributed.yaml` and find the `remote_nodes` section. This is a dictionary of remote task running nodes.
For each created/installed task running node, add an entry.

```yaml
<A node name>:
  api_url: http://<node ip>:<node port>
  api_key: <node api key>
```

**3. Start Cuckoo in distributed mode**

Starting Cuckoo in distributed mode will cause Cuckoo to request information from each node on startup. Any connection error with one of 
the nodes will result in the stopping of startup.

If the startup is successful, the setup is ready for submission.

    cuckoo --distributed
