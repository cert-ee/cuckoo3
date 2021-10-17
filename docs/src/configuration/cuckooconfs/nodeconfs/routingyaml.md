## What is this config

The `$CWD/conf/node/routing.yaml` is a configuration that contains all settings used by Cuckoo rooter. Cuckoo
rooter automatically applies per-task network routes and settings.

This file contains things such as:

- Outgoing interfaces and a routing table for internet routing.
- Existing VPN interfaces and routing tables for VPN routing.
- OpenVPN configuration files and up script paths for automatically starting VPNs.

### Default config example

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