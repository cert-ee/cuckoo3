
## What is this config

The `$CWD/conf/cuckoo.yaml` is a "general" configuration file. It contains main settings such as
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

# Enable screenshots of analysis machines while running.
machinery_screenshots:
  enabled: False

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
  max_file_size: 4294967296
```
