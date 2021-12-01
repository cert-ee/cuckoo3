# Submitting files/URLs

Submitting files/urls can be done in multiple ways: over command line, the web API, or the web UI.

This page will mostly be focusing on how command line submissions work. 
See the [web API page](../webapi/endpoints.md) for API submission help.

#### File identification

After submission, Cuckoo tries to automatically determine the type of file that was submitted. It uses this information for multiple purposes:

- To automatically choose a platform to run the sample on. (if no platform(s) are specified).
- To determine if it can run the sample at all.
- To determine how it should start the sample.

File identification can be tricky, and some files can be identified incorrectly. This mostly happens with script/text files.
This can result in failed tasks. You can tell Cuckoo to use the original file extension by using the `--orig-filename` flag or 'Use original filename' checkbox in the web UI.

#### Cuckoo analysis

An analysis in Cuckoo is created when a submission is made. It consists of one or more tasks, analysis settings, and per-task settings.

#### Cuckoo task

A task is part of an analysis. Cuckoo supports selecting multiple platforms for each analysis.
An example of this is choosing both Windows 10 and 7. Or two Windows 10 platforms with a different network route.
Each selected platform will result in a created task.

#### A platform

By platform we mean an OS name, OS version, and settings for this platform. Most settings are on analysis level. Some can be changed on a platform level.
Platform level settings override the settings on an analysis level.
Examples of the platform level settings are:

- `command`
  A command used to start the submitted sample. If none is specified, Cuckoo determines one automatically. An example of when to use this is when you want to run a specific function from a DLL.
- `route`
  A network route. Drop, A VPN, or 'dirty line'/internet routing. See [network routing](../../installation/routing.md#using-cuckoo-rooter) for more information.
- `browser`
  The browser to open a URL in. Browsers are discovered by search for machines with a `browser_browsername` tag.

#### Command line submission

Command line submissions are created using the `cuckoo submit` command.

The tools help message is:

```bash
Usage: cuckoo submit [OPTIONS] [TARGET]...

  Create a new file/url analysis. Use index,value of the used --platform
  parameter to specify a platform specific setting. No index given means the
  setting is the default for all platforms.

  E.G: --platform windows --browser 0,browsername

Options:
  -u, --url            Submit URL(s) instead of files.
  --platform TEXT      The platform and optionally the OS version the analysis
                       task must run on. Specified as platform,osversion or
                       just platform. Use <index of param>,value to specific
                       browser, command, and route settings.
  --timeout INTEGER    Analysis timeout in seconds.
  --priority INTEGER   The priority of this analysis. A higher number means a
                       higher priority.
  --orig-filename      Ignore auto detected file extension and use the
                       original file extension.
  --browser TEXT       The browser to use for a URL analysis. (Supports per
                       platform configuration).
  --command TEXT       The command/args that should be used to start the
                       target. Enclose in quotes. Use %PAYLOAD% where the
                       target should be in the command. (Supports per platform
                       configuration)
  --route-type TEXT    The route type to use. (Supports per platform
                       configuration)
  --route-option TEXT  Option for given route. Key=value format. (Supports per
                       platform configuration)
  --option TEXT        Option for the analysis. Key=value format.
  --help               Show this message and exit.

```

##### Submitting a file, simple

The following command will create an analysis and automatically choose a platform to run it on.

```bash  
$ cuckoo submit /tmp/file.exe
Submitted file: 20210501-GN3EIA -> /tmp/file.exe
```

##### Submitting a file, multi platform

The following command creates an analysis for multiple platforms. In the example we want to run a DLL twice, on the same OS, but run a different function.
Each platform setting must have an index number that indicates to what `--platform` argument it applies.

```bash
cuckoo submit --platform windows,10 --platform windows,10 --command "0,rundll32.exe %PAYLOAD%,func1" --command "1,rundll32.exe %PAYLOAD%,func2" /tmp/file.dll
```

The `--command` arguments start with a 0 and 1. These are the indexes that refer to first and second `--platform` arguments.

##### Submitting a file, multiple different routes

A route-type is the type of route, such as: vpn, drop, or internet. The route-option is an option to for a route. 
An example of this is the country for a vpn.

The following command creates an analysis with two platforms. 
One Windows 10, and a Windows 7. The first `--route-type` applies at analysis level. 
The second one on the index 1. This means the VPN route and option apply to the Windows 7 platform.

```bash
cuckoo submit --platform windows,10 --platform windows,7 --route-type internet --route-type 1,vpn --route-option 1,country=countryname /tmp/file.exe
```

##### Submitting a URL, multiple browsers.

The following command submits a URL and creates two tasks. One for the Internet Explorer browser, one for Edge.
This example assumes machines with the `browser_edge` and `browser_internet_explorer` exist.

```bash
cuckoo submit --url --platform windows,10 --platform windows,10 --browser "0,edge" --browser "1, internet explorer" http://example.com
```
