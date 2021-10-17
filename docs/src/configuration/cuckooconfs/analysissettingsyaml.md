
## What is this config

The `$CWD/conf/analysissettings.yaml` is a settings files that contains submission settings limits and defaults.

### Default config example

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