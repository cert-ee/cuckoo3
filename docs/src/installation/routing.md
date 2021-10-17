## Network routing

Internet access for the analysis machines can be important for results. There are two ways of setting up
network routing that we will discuss here: 

- [Global routing](#global-routing)
- [Automatic per-task routing by Cuckoo rooter](#cuckoo-rooter)


#### Global routing

Instead of having Cuckoo rooter apply per-task routing, it is of course also possible
to simply provide internet access to the entire subnet of all your analysis machines.

In the following setup we arere assuming that the interface assigned to our
KVM VM is ``virbr0``, the IP address of our VM is ``192.168.122.100``
(in a ``/24`` subnet), and that the outgoing interface connected to the
internet is ``eth0``. With such a setup, the following ``iptables`` rules will
allow the VMs access to the Cuckoo host machine (``192.168.122.1`` in this
setup) as well as the entire internet as you would expect from any application
connecting to the internet.


    $ sudo iptables -t nat -A POSTROUTING -o eth0 -s 192.168.122.0/24 -j MASQUERADE

    # Default drop.
    $ sudo iptables -P FORWARD DROP

    # Existing and related connections.
    $ sudo iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT

    # Accept connections from VM(s) to the whole internet.
    $ sudo iptables -A FORWARD -s 192.168.122.0/24 -j ACCEPT

    # Internal traffic.
    $ sudo iptables -A FORWARD -s 192.168.122.0/24 -d 192.168.122.0/24 -j ACCEPT

These rules will not be doing any packet forwarding unless IP forwarding
is explicitly enabled in the kernel. To do so, there is a temporary method
that survives until a shutdown or reboot, and . Simply put, generally speaking you will
want to run both commands::

A temporary method that survives until a shutdown or reboot:

    $ echo 1 | sudo tee -a /proc/sys/net/ipv4/ip_forward

A permanent method that survives the reboot of the machine.

    $ sudo sysctl -w net.ipv4.ip_forward=1

Iptables rules are not persistent between reboots, if want to keep
them you should use a script or install ``iptables-persistent``.


#### Cuckoo rooter

Cuckoo rooter provides `root` access for various commands to Cuckoo. Rooter runs as a separate
service/process. Cuckoo, which must never run as root, can make requests to rooter for specific
types of network routing. This allows for the possibility to have **per-task routing**. 
See the [per-task routing](#automatic-per-task-routing-by-cuckoo-rooter) section for more information on the possible routing types.

Communication with rooter occurs over a Unix socket. The user running cuckoo must have read and write access 
to this socket, so it can query the available routes and request these. Anyone with access to this socket can make route requests.

Only routes configured and enabled in [routing.yaml](../configuration/cuckooconfs/nodeconfs/routingyaml.md) will be
available routing types. Each Cuckoo task runner node will automatically ask Cuckoo rooter what routes are available
when the node starts. This means that rooter and the node must be restarted before newly configured routes are available.

Cuckoo rooter is only available for Ubuntu and Debian-like systems.


##### Using Cuckoo rooter

The command to start Cuckoo rooter is `cuckoorooter`. An example of the help page is:


    $ cuckoorooter --help
    Usage: cuckoorooter [OPTIONS] [SOCKET]

    A unix socket server that applies and removes requested network routes
    for analysis machines. Must run with root permissions. Use --sudo or run
    command printed by --print-command. Routes are loaded from
    node/routing.yaml

    Options:
    --cwd TEXT        Cuckoo Working Directory
    -d, --debug       Enable verbose logging
    -g, --group TEXT  Unix socket group
    --iptables PATH   Path to the iptables(8) binary
    --ip PATH         Path to the ip(8) binary
    --sudo            Request superuser privileges
    --sudo-path PATH  Path to the sudo(8) binary
    --openvpn PATH    Path to the OpenVPN(8) binary
    --print-command   Dry run and print the starting command that can be used in
                        things such as systemd or supervisord. Correct
                        arguments/flags should be supplied so command can be
                        generated.
    --help            Show this message and exit.

Rooter needs the binary paths to multiple tools to be able to automatically
apply routes. 

Rooter must run with root permissions and can either be started using the `--sudo` flag or by using the 
output of `--print-command` on the root user. 

The `--cwd` should be used to supply rooter with the Cuckoo CWD path where the [routing.yaml](../configuration/cuckooconfs/nodeconfs/routingyaml.md) file it should use is located. This file contains the settings for available routes.

!!! Warning "Privilege escalation"
    Ideally, rooter has its own Cuckoo CWD and virtualenv with a Cuckoo installation. This prevents Python files that a non-privileged
    user can write to from being run with root permissions. This can prevent an accidental privilege escalation.

**Examples of running rooter**

* Running with `--sudo`

Sudo will prompt you for your password now. After this, rooter will start as the rooter user. 
The `/tmp/cuckoo3-rooter.sock` path will be created and the `cuckoouser` group will have read
and write access.

    $ cuckoorooter -d --cwd /path/to/cwd --group cuckoouser --sudo /tmp/cuckoo3-rooter.sock

* Running the command generated by `--print-command`

First, we generated the command with the options/settings we want.

    $ cuckoorooter -d --cwd /path/to/cwd --group cuckoouser --print-command /tmp/cuckoo3-rooter.sock

The output of this command will be:

    /home/cuckoo/venv/bin/cuckoorooter /tmp/cuckoo3-rooter.sock --cwd /path/to/cwd --iptables /sbin/iptables --ip /sbin/ip --openvpn /usr/sbin/openvpn --group cuckoouser --debug

The above command can be run directly by the root user or using `sudo`.

**Configuring the socket path and enabling rooter usage**

The usage of Cuckoo rooter must be enabled and the rooter socket path set in [cuckoo.yaml](../configuration/cuckooconfs/cuckooyaml.md) before Cuckoo nodes will use it.

Open [cuckoo.yaml](../configuration/cuckooconfs/cuckooyaml.md) and find the `network_routing` section.
Enable rooter usage and configure the socket path we used to start rooter.

```yaml
# Automatic per-task network routing. Before a task runs, the rooter
# is asked to apply a submitted or default network route. Cuckoo rooter
# must be running and its unix socket path must be configured here.
network_routing:
  enabled: True
  # Cuckoo rooter socket path. Must be writable and readable for the user
  # that runs Cuckoo.
  rooter_socket: /tmp/cuckoo3-rooter.sock
``` 

##### Automatic per-task routing by Cuckoo rooter

One or more routing types must be configured before rooter can actually apply routes. 

All supports routing types, except 'No route', will block analysis VMs from communicating with anything
else than the result server and the location their traffic is forwarded to (internet, a VPN, etc). 

Rooter currently supports the following types of routing:

| Routing type | Description |
|--------------|-------------|
| [No route](#no-route)|No route is applied, unless a default route for rooter is configured. |
| [Drop routing](#drop-routing)| All traffic is dropped, except traffic from and to the result server and agent. |
| [Internet routing](#internet-routing)| All non-result server and agent traffic is routed through the 'internet' interface. |
| [VPN routing](#vpn-routing)| All non-result server and agent traffic is routed through a VPN of a chosen country. |


###### No route

No route is the what happens if no other route is chosen. It means Cuckoo rooter will not receive any request by Cuckoo
to apply any routing. 'No route' is overridden by the default route configured in [analysissettings.yaml](../configuration/cuckooconfs/analysissettingsyaml.md).

###### Drop routing

Drops all traffic, except traffic to and from the result server and agent. Analysis machines cannot communicate
with each other. Drop routing is always available when rooter is running.

The name of this routing type in submission is `drop`.


###### Internet routing

By using the internet routing one may provide full internet access to analysis machines through one of the connected network interfaces.
This is accomplished by temporarily adding the analysis machine IP to a configured routing table and forwarding and NATting the traffic
from and to this machine to the configured 'internet' interface.

The name of this routing type in submission is `internet`.


!!! Warning "Malicious traffic"
    This type of routing routes allows potentially malicious samples to connect to the internet through the configured interface.

To configure this, open [routing.yaml](../configuration/cuckooconfs/nodeconfs/routingyaml.md) and find the `internet` section.

Enter an interface to which the malware traffic should be forwarded for internet access. Add a routing table that
contains routes for this interface. Cuckoo will be adding/removing source routing rules for analysis machine IPs to this table.

```yaml
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
```


###### VPN routing

VPN routing is similar to internet routing, except that the interfaces rooter forwards traffic over are interfaces of an (existing) 
VPN connection. An exit country must be specific for each configured VPN. This country is used to select one of the configured VPNs.

If VPN routing is chosen during sample submission, but no country is chosen, the first available VPN will be used.

The name of this routing type in submission is `vpn`. A optional `country` option is available to specify the country.

There are two ways of configuring VPN routing:

* Pre-configure VPNs

    Add one or more existing VPN interfaces and routing tables to the routing config. Rooter assumes the user has set these up and they are working.
    This works similarly to 'internet routing', except these interfaces have a 'country' field.

* VPN pool VPNs (OpenVPN only).

    Rooter can automatically start and stop VPNs on demand. This only works with OpenVPN VPNs.
    This type of VPN usage can be useful if you want support for many exit countries. Simply download the OpenVPN 
    config files for the countries you want to support from your VPN provider and these to the routing config.
    
    It is possible to add one ore more 'VPN providers', that each have one or more VPNs.
    Each VPN entry contains an OpenVPN config path, an 'up script' path (shipped with Cuckoo), and a country.

    Each provider entry has a 'maximum connections' setting. Rooter will never start more than this amount
    of VPNs for that provider.


**Using pre-configured VPNs**

Open [routing.yaml](../configuration/cuckooconfs/nodeconfs/routingyaml.md) and find the `vpn` section.
Under the vpn section, find the `preconfigured` section. Add one or more VPNs and set `enabled` to `True`.

The `vpns` key must contain a YAML dictionary of one or more of the following entries.

```yaml
 <label for vpn>:
   interface: # The existing VPN tun interface.
   routing_table: # The routing table for the existing VPN.
   country: # The country the VPN routes traffic through.
``` 

```yaml
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
      example_vpn2:
        # The existing VPN tun interface.
        interface: tun2
        # The routing table for the existing VPN.
        routing_table: vpn2
        # The country of that the VPN IP is identified as. Any string can be
        # used.
        country: country2
```

**Using VPN pool VPNs**

Open [routing.yaml](../configuration/cuckooconfs/nodeconfs/routingyaml.md) and find the `vpn` section.
Under the vpn section, find the `vpnpool` section. Add one or more providers with VPNs and set `enabled` to `True`.

The `providers` key must contain a YAML dictionary with one or more provider entries.

The `up_script` must contain a path to a script that is run after the VPN is started. It must be executable. This script
is passed to the OpenVPN `--route-up` parameter. The up script must perform the following actions:

* Use the path is `$CUCKOO_IP_PATH` (path to ip command) to add routes.
* Add a default route to the VPN gateway IP for interface `$dev` to `$CUCKOO_ROUTING_TABLE`.
    * $CUCKOO_ROUTING_TABLE will contain a number within the range of the `routing_tables` range in the routing config.
* Add a route for each `$remote_<n>` IP for interface `$dev` to `$CUCKOO_ROUTING_TABLE`.
* Create the file path `$CUCKOO_READY_FILE` when the script is done. This is to let rooter known the script has completed.
    * This file is automatically deleted by rooter.

Cuckoo is shipped with a script that performs all actions mentioned above.
The path to this script is `$CWD/rooter/scripts/openvpnroutes.sh`. It is recommended this script is used.


```yaml
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
