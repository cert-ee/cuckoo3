## What is this config

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
