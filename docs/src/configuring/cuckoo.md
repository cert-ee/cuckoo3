# Configuring Cuckoo3

!!! warning "Incomplete"

    Not all configurations are yet documented.  
    We are reviewing all configurations and adding more as we go.

Cuckoo configurations can be found in `~/.cuckoocwd/` directory by default.  
It holds all Cuckoo related configuration files and these are the broad categories:


- **conf**: holds Cuckoo and Cuckoo module configurations
    - **machineries**: VM configurations
    - **node**: distributed configurations
    - **processing**: all analysis configurations
    - **web**: Django configurations
- **elasticsearch**: Elasticsearch configurations
- **log**: Cuckoo logs
- **monitor**: monitor, stager and other tools for analyses
- **operational**: information about nodes, taskque database and UNIX sockets
- **rooter**: scripts such as openvpn routes
- **safelist**: safelist database
- **signatures**: Cuckoo signatures
- **storage**: all generated assets related to analyses such as images, pcap files etc.
- **web**: API and web related configurations

---

## Cuckoo configurations

### cuckoo.yaml
Location: `conf/cuckoo.yaml`

Here we will point out the main ones that might require your attention.

- `machineries` -  this is a list of all machinery modules that Cuckoo will be using. By default this should be `qemu`
    
- `resultserver` - resultserver must be in the same network as analyses machines for them to communicate. In the case of our VMs we created that are in subnet `192.168.30.1/24`, the configuration would look like this:

- `tcpdump` - make sure this is enabled and pointing to `tcpdump` binary.

```yaml
# A YAML list of all machinery modules that should be enabled and Cuckoo will be using. Machines for
# each of the modules specified here have to be configured in their respective configuration file
# in the conf/machineries directory. It is only possible to run multiple machinery modules if their underlying
# virtualization layers do not interfere with each other.
# Example:
#
# machineries:
#   - machinery1
#   - machinery2
machineries:
  - qemu

# The resultserver is a Cuckoo component that running analysis machines upload their results to
# it should be reachable from the analysis machine. A resultserver will be started on the configured
# listen IP and port. Make sure the IP is off a network interface that is part of the analysis machine network or
# route/forward traffic between the analysis machines and the resultserver.
resultserver:
  listen_ip: 192.168.30.1
  listen_port: 2042

# Settings used by Cuckoo to find the tcpdump binary to use for network capture of machine traffic.
tcpdump:
  enabled: True
  path: /usr/bin/tcpdump

# Automatic per-task network routing. Before a task runs, the rooter
# is asked to apply a submitted or default network route. Cuckoo rooter
# must be running and its unix socket path must be configured here.
network_routing:
  enabled: False
  # Cuckoo rooter socket path. Must be writable and readable for the user
  # that runs Cuckoo.
  rooter_socket: null

platform:
  # Use the machine tags determined during the identification phase for machine selection.
  # Enabling this means your analyis machines have been configured with the tags
  # listed in conf/processing/identification.yaml
  autotag: False

state_control:
  # Cancel an analysis if the submitted file was not identified during the
  # identification stage.
  cancel_unidentified: False

processing:
  # Processing workers are the dedicated processes that perform the processing
  # of submitted target and collected data.
  worker_amount:
    # Identification is responsible for unpacking and identifying a submitted target.
    identification: 1
    # Pre workers are responsible for all pre-processing and more extensive static analysis.
    # that is performed before tasks are created.
    pre: 1
    # Post workers are responsible for the processing of data collected during each task.
    post: 1

# The Cuckoo 'long term storage' host that reported analyses should be moved to when
# starting 'cuckoocleanup remotestorage'. This host must have an import controller
# instance and the Cuckoo API running.
remote_storage:
  # The API url of a remote running Cuckoo API.
  api_url: null

  # API key needs to have administrator privileges to export to
  # a remote Cuckoo.
  api_key: null

# Settings used by Cuckoo submit
submit:
  # min_file_size for submit
  min_file_size: 133

  # max_file_size for submit, default 4gb
```
</br>

### analysissettings.yaml
Location: `conf/analysissettings.yaml`

It contains submission settings limits and defaults.

```yaml
# Limits on settings. Submissions will be denied if they exceed any
# of these limits.
limits:
  max_timeout: 300
  max_priority: 999
  # The maximum amount of platforms a submission can have.
  max_platforms: 3

# The default settings that will be used if these are not given.
default:
  # The timeout in seconds that will be used for each task.
  timeout: 120
  # The priority that will be used when in scheduling. A higher number
  # means a higher priority.
  priority: 1
  # The route that will be used for each task. Automatic network routing
  # must be enabled and rooter must be running for this feature to work.
  # See cuckoo.yaml.
  route:
    # The route type: internet, vpn, or drop.
    type: null
    # Route options such as 'country: somecountry' for a VPN route.
    options:

# Settings used to determine the platform to use if no platforms
# are provided on submission.
platform:
  # The OS versions of a platform that should be added to settings for an
  # identified platform. These versions are also used for the multi_platform
  # and fallback_platforms settings. Multiple versions will result in a
  # task for each version. Each platform must at least have a list of 1 version.
  versions:
    windows:
    - 10

  # Which of the supported platforms determined during the identification stage
  # should actually be used if a target can run on multiple platforms.
  # This should be a list of platform names.
  # The OS versions used are the ones specified in the 'versions' setting.
  multi_platform:
  - windows

  # Which platform(s) should be used if no platforms the target can run on were
  # identified and no platforms were provided on submission?
  # This should be a list of platform names.
  # The OS versions used are the ones specified in the 'versions' setting.
  fallback_platforms:
  - windows
```
</br>

### qemu.yaml
Location: `conf/machineries/qemu.yaml`

This configuration handles QEMU VMs for Cuckoo.

- `interface` - this needs to match the interface that was created using `vmcloak-qemubridge` in [Configuring VMCloak](../installing/vmcloak.md#configuring-vmcloak){:target=_blank}

```yaml
# Specify the name of the network interface/bridge that is the default gateway
# for the QEMU machines.
# Example: br0
interface: br0

# Make disposable copies of machine disk images here. Copies are created each
# time the machine is restored. This directory path must be writable and
# readable. If this not specified, the directory of the 'qcow2_path' of each
# machine will be used.
disposable_copy_dir: 

# The paths to binaries used to create disks, restore, and
# start virtual machines
binaries:
  # Path to qemu-img.
  qemu_img: /usr/bin/qemu-img
  # Path to qemu-system-x86_64
  qemu_system_x86_64: /usr/bin/qemu-system-x86_64

machines:
  win10vm_1:
    # The path to the QCOW2 disk image. This disk will be used as a backing
    # for each disposable copy when restoring and booting the machine. The parent
    # directory is used for disposable disk copies if no disposable_copy_dir
    # is given. This means the directory must be readable and writable.
    # Should be made with the 'lazy_refcounts=on,cluster_size=2M' options.
    qcow2_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_1/disk.qcow2
    # The filepath to the machine memory snapshot. A 'QEMU suspend to disk image'.
    # This is restored using the '-incoming' parameter. Restoring this should
    # result in a running machine with the agent listening on the specified port.
    snapshot_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_1/memory.snapshot
    # The filepath to a JSON dump containing information on how to start this
    # machine. This file is generated by VMCloak. It can be made by hand:
    # {'machine': {'start_args': []}}, where the start args value is a list of arguments
    # for qemu, using %DISPOSABLE_DISK_PATH% where the path to the qcow2 should
    # be inserted by Cuckoo.
    machineinfo_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_1/machineinfo.json
    # The static IP address that has been configured inside of the machine.
    ip: 192.168.30.12
    # The operating system platform installed on the machine.
    platform: windows
    # A string that specifies the version of the operating system installed.
    # Example: "10" for Windows 10, "7" for Windows 7, "18.04" for Ubuntu 18.04.
    os_version: "10"
    # The system architecture. Amd64, ARM, etc. This is used to
    # select the correct stager and monitor builds/component for the machine.
    architecture: amd64
    # The TCP port of the agent running on the machine.
    agent_port: 8000
    # (Optional) The MAC address of the network interface of the machine that is used to connect to
    # to the resultserver and the internet.
    mac_address: 00:19:3c:ce:71:e2
    # (Optional) Specify the name of the network interface that should be used
    # when dumping network traffic from this machine with tcpdump.
    interface: br0
    # Machine tags that identify the installed software and other characteristics of the machine.
    # These are used to select the correct machine for a sample that has dependencies. *Notice*: correct tags are
    # crucial in selecting machines that can actually run a submitted sample.
    # Existing automatic tags can be found in the conf/processing/identification.yaml config.
    tags:
    - adobepdf
    - vcredist
    - pdfreader
    - dotnet
    - browser_edge
    - browser_internet_explorer
  win10vm_3:
    # The path to the QCOW2 disk image. This disk will be used as a backing
    # for each disposable copy when restoring and booting the machine. The parent
    # directory is used for disposable disk copies if no disposable_copy_dir
    # is given. This means the directory must be readable and writable.
    # Should be made with the 'lazy_refcounts=on,cluster_size=2M' options.
    qcow2_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_3/disk.qcow2
    # The filepath to the machine memory snapshot. A 'QEMU suspend to disk image'.
    # This is restored using the '-incoming' parameter. Restoring this should
    # result in a running machine with the agent listening on the specified port.
    snapshot_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_3/memory.snapshot
    # The filepath to a JSON dump containing information on how to start this
    # machine. This file is generated by VMCloak. It can be made by hand:
    # {'machine': {'start_args': []}}, where the start args value is a list of arguments
    # for qemu, using %DISPOSABLE_DISK_PATH% where the path to the qcow2 should
    # be inserted by Cuckoo.
    machineinfo_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_3/machineinfo.json
    # The static IP address that has been configured inside of the machine.
    ip: 192.168.30.10
    # The operating system platform installed on the machine.
    platform: windows
    # A string that specifies the version of the operating system installed.
    # Example: "10" for Windows 10, "7" for Windows 7, "18.04" for Ubuntu 18.04.
    os_version: "10"
    # The system architecture. Amd64, ARM, etc. This is used to
    # select the correct stager and monitor builds/component for the machine.
    architecture: amd64
    # The TCP port of the agent running on the machine.
    agent_port: 8000
    # (Optional) The MAC address of the network interface of the machine that is used to connect to
    # to the resultserver and the internet.
    mac_address: e8:2a:ea:c3:5c:4c
    # (Optional) Specify the name of the network interface that should be used
    # when dumping network traffic from this machine with tcpdump.
    interface: br0
    # Machine tags that identify the installed software and other characteristics of the machine.
    # These are used to select the correct machine for a sample that has dependencies. *Notice*: correct tags are
    # crucial in selecting machines that can actually run a submitted sample.
    # Existing automatic tags can be found in the conf/processing/identification.yaml config.
    tags:
    - adobepdf
    - vcredist
    - pdfreader
    - dotnet
    - browser_edge
    - browser_internet_explorer
  win10vm_2:
    # The path to the QCOW2 disk image. This disk will be used as a backing
    # for each disposable copy when restoring and booting the machine. The parent
    # directory is used for disposable disk copies if no disposable_copy_dir
    # is given. This means the directory must be readable and writable.
    # Should be made with the 'lazy_refcounts=on,cluster_size=2M' options.
    qcow2_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_2/disk.qcow2
    # The filepath to the machine memory snapshot. A 'QEMU suspend to disk image'.
    # This is restored using the '-incoming' parameter. Restoring this should
    # result in a running machine with the agent listening on the specified port.
    snapshot_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_2/memory.snapshot
    # The filepath to a JSON dump containing information on how to start this
    # machine. This file is generated by VMCloak. It can be made by hand:
    # {'machine': {'start_args': []}}, where the start args value is a list of arguments
    # for qemu, using %DISPOSABLE_DISK_PATH% where the path to the qcow2 should
    # be inserted by Cuckoo.
    machineinfo_path: /home/cuckoo/.vmcloak/vms/qemu/win10vm_2/machineinfo.json
    # The static IP address that has been configured inside of the machine.
    ip: 192.168.30.11
    # The operating system platform installed on the machine.
    platform: windows
    # A string that specifies the version of the operating system installed.
    # Example: "10" for Windows 10, "7" for Windows 7, "18.04" for Ubuntu 18.04.
    os_version: "10"
    # The system architecture. Amd64, ARM, etc. This is used to
    # select the correct stager and monitor builds/component for the machine.
    architecture: amd64
    # The TCP port of the agent running on the machine.
    agent_port: 8000
    # (Optional) The MAC address of the network interface of the machine that is used to connect to
    # to the resultserver and the internet.
    mac_address: 00:17:a4:eb:bb:44
    # (Optional) Specify the name of the network interface that should be used
    # when dumping network traffic from this machine with tcpdump.
    interface: br0
    # Machine tags that identify the installed software and other characteristics of the machine.
    # These are used to select the correct machine for a sample that has dependencies. *Notice*: correct tags are
    # crucial in selecting machines that can actually run a submitted sample.
    # Existing automatic tags can be found in the conf/processing/identification.yaml config.
    tags:
    - adobepdf
    - vcredist
    - pdfreader
    - dotnet
    - browser_edge
    - browser_internet_explorer
```
</br>

### routing.yaml

Location: `conf/node/routing.yaml`
This configuration contains all settings used by Cuckoo rooter such as:

- Outgoing interfaces and a routing table for internet routing.
- Existing VPN interfaces and routing tables for VPN routing.
- OpenVPN configuration files and up script paths for automatically starting VPNs.

Cuckoo rooter automatically applies per-task network routes and settings.

```yaml
# This is the configuration file for Cuckoo rooter. Rooter performs
# automatic routing for analysis machines. This file contains the
# routes that will be available to each Cuckoo node. Cuckoo rooter must be
# running for these routes to work.

# Internet/dirty line routing routes machine traffic directly over the
# specified interface. The machine IP will be added to the specified
# routing table. Note that this will route the malicious traffic over the
# configured network. An example of internet route could be a preconfigured
# VPN interface and routing table.
internet:
  # Enable or disable internet routing.
  enabled: False
  # The interface the network should be forwarded to to reach the internet.
  interface: null
  # The routing table id/name rooter should add machine IPs to. This table
  # should have the routes that result in traffic being routed over the
  # specified interface.
  routing_table: main

# Rooter can use preconfigured VPN interfaces and routing tables and can also
# start OpenVPN VPNs if their configuration paths are specified. VPN
# routing is used when a country is specified as a routing option.
#
# If both preconfigured and VPN pool is enabled, Cuckoo will choose the first
# available VPN that matches the specified country or the first available
# VPN if no country is specified.
vpn:
  # Preconfigured and running VPN interfaces and their routing tables.
  preconfigured:
    # Disable or enable the use of preconfigured VPNs.
    enabled: False
    # A mapping of one or more preconfigured VPNs that Cuckoo rooter can use.
    vpns:
      # The VPN name that used in logging.
      example_vpn:
        # The existing VPN tun interface.
        interface: tun0
        # The routing table for the existing VPN.
        routing_table: vpn0
        # The country of that the VPN IP is identified as. Any string can be
        # used.
        country: country1

  # A pool of VPN providers with OpenVPN VPN configurations. Rooter can
  # automatically start and stop these VPNs when needed. This feature is
  # useful if you want to support a large amount of exit countries.
  vpnpool:
    # Disable or enable the automatic starting of available VPNs.
    enabled: False

    # The range of routing table IDs that rooter can use to pass to up scripts.
    # These tables *must not* interfere with other ranges/existing tables.
    # The size of the range limits the amount of automatically started VPNs
    # that can be active at the same time.
    routing_tables:
      start_range: 100
      end_range: 200

    providers:
      example_provider:
        # The maximum amount of connections/devices the VPN provider allows.
        # This is the maximum amount of configurations that rooter will
        # use simultaneously for this provider.
        max_connections: 5

        # A list of dictionaries with all the VPN configuration for this
        # provider that rooter can start.
        vpns:
          # The type of VPN. Only OpenVPN is currently supported.
        - type: openvpn
          # The VPN configuration file. OVPN file, for example.
          config_path: /path/to/ovpns/country1.ovpn
          # The up script that adds the required routes to the automatically
          # determine routing table. Do not change unless your custom script
          # also performs what the default script does.
          up_script: /home/cuckoo/.cuckoocwd/rooter/scripts/openvpnroutes.sh
          # The country of that the VPN IP is identified as. Any string can be
          # used.
          country: country1
```

### web.yaml
Location: `/conf/web/web.yaml` 
This configuration file contains settings for the web API and UI.  
It contains settings such as the enabling/disabling of sample downloading and statistics.

```yaml
# Remote storage usage is the retrieval of analysis reports etc from
# a remote Cuckoo 'long term storage' host.
remote_storage:
  enabled: False
  api_url: null

  # API key does not need administrator privileges
  api_key: null

elasticsearch:
  # The Elasticsearch settings must be configured to be able to use any of
  # the features in this section.

  # Enable or disable the Cuckoo web results search functionality
  web_search:
    enabled: False

  # Enable or disable Cuckoo web results statistics. Detected family, behavior
  # graphs, amount of submissions, etc.
  statistics:
    enabled: False

    # All enabled charts types and the time ranges over which they
    # should display data. Available range: daily, weekly, monthly, yearly.
    # Available chart examples: families_bar, families_line, targettypes_bar,
    # categories_bar, categories_line, submissions_line
    charts:
    - chart_type: submissions_line
      time_range: yearly
    - chart_type: submissions_line
      time_range: monthly
    - chart_type: families_bar
      time_range: weekly
    - chart_type: families_line
      time_range: weekly
    - chart_type: targettypes_bar
      time_range: monthly
    - chart_type: categories_bar
      time_range: monthly

  # The Elasticsearch hosts where results are reported to during processing.
  # Should be one ore more host:port combinations.
  hosts:
    - https://127.0.0.1:9200
  # The Elasticsearch auth and ssl cert
  user:
  password: 
  ca_certs: /etc/ssl/certs/ca-certificates.crt

  indices:
    # The names to use when searching Elasticsearch. Each name must be unique
    # and should also be used in reporting.
    names:
      analyses: analyses
      tasks: tasks
      events: events

  # The max result window that will be used in searches. The Elasticsearch default is 10000. This
  # window has impact in how far back you can search with queries that match a large amount of documents.
  max_result_window: 10000

# Specific web features that can be disabled/enabled
web:
  downloads:
    # Enable/disable submitted file downloading.
    submitted_file: True
    allowed_subnets: 127.0.0.0/8,10.0.0.0/8 

```

---

## Distributed

!!! error "Unverified"

    This is from the old documentation.  
    We are currently reviewing and updating distributed configurations.

The distributed.yaml config file is used to tell the main node what task running nodes are available. It also contains
the api key that is used if a node is a task running node.

```yaml
# A dictionary list of remote Cuckoo instances that are running in node mode.
# This is used in a distributed Cuckoo setup.
remote_nodes:
  example1:
    # The remote node API url. This is not the Cuckoo API.
    api_url: http://127.0.1:8090
    # Remote node API key.
    api_key: examplekey

# The settings used if the Cuckoo install is started as a Cuckoo node.
node_settings:
  # The node API key. This must be configured in the main Cuckoo's
  # remote_nodes configuration section.
  api_key: 53e13ee1f6fd99bd9dd3f982e1f4fe221847e6b19fbe47f078a4e1e7dca14a6e
```
