
## What is this config

The cuckoo.yaml is a "general" configuration file. It contains main settings such as
the chosen machinery module(s).

### Default config example

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
  - kvm

# The resultserver is a Cuckoo component that running analysis machines upload their results to
# it should be reachable from the analysis machine. A resultserver will be started on the configured
# listen IP and port. Make sure the IP is off a network interface that is part of the analysis machine network or
# route/forward traffic between the analysis machines and the resultserver.
resultserver:
  listen_ip: 192.168.122.1
  listen_port: 2042

# Settings used by Cuckoo to find the tcpdump binary to use for network capture of machine traffic.
tcpdump:
  enabled: True
  path: /usr/sbin/tcpdump

platform:
  # The default platform to use when no platforms are supplied on submission and no required platform is
  # identified during the identification stage.
  default_platform:
    platform: windows
    os_version: null

  # Which of the supported platforms determined during the identification stage should be used if a target
  # can run on multiple platforms. A task will be created for each of the specified platforms if it is present in the
  # determined platforms.
  multi_platform:
    - windows

  # Use the machine tags determined during the identification phase for machine selection.
  # Enabling this means your analyis machines have been configured with the tags
  # listed in conf/processing/identification.yaml
  autotag: False

state_control:
  # Cancel an analysis if the file was not identified during the identification stage.
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

remote_storage:
  api_url: null

  # API key needs to have administrator privileges to export to
  # a remote Cuckoo.
  api_key: null
```
