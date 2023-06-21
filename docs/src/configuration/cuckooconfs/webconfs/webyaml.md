
## What is this config

The `$CWD/conf/web/web.yaml` is configuration file that contains settings for the web API and UI. It contains
settings such as the enabling/disabling of sample downloading and statistics.

### Default config example

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
