# Cuckoo commands and tools
!!! warning "Unverified"

    This is from the old documentation.  
    We are currently reviewing and updating commands and tools.

This page lists available tools and commands.

#### cuckoo

The main Cuckoo command. Used to:

- Start Cuckoo
- Create and update working directories
- Start the web interface and api.
- Import a monitor zip
- Add machines to their configuration file
- Submit files/urls

##### Help

    $ cuckoo --help

    Usage: cuckoo [OPTIONS] COMMAND [ARGS]...

    Options:
    --cwd TEXT          Cuckoo Working Directory
    --distributed       Start Cuckoo in distributed mode
    -v, --verbose       Enable debug logging, including for non-Cuckoo modules
    -d, --debug         Enable debug logging
    -q, --quiet         Only log warnings and critical messages
    --cancel-abandoned  Do not recover and cancel tasks that are abandoned and
                        still 'running'
    --help              Show this message and exit.

    Commands:
    api         Start the Cuckoo web API (development server)
    createcwd   Create the specified Cuckoo CWD
    getmonitor  Use the monitor and stager binaries from the given Cuckoo...
    importmode  Start the Cuckoo import controller.
    machine     Add machines to machinery configuration files.
    submit      Create a new file/url analysis
    web         Start the Cuckoo web interface (development server)


#### cuckoonode

The Cuckoo node command is used to start a Cuckoo task running node. Only used if running Cuckoo in distributed mode.

##### Help

    $ cuckoonode --help

    Usage: cuckoonode [OPTIONS] COMMAND [ARGS]...

    Options:
    --cwd TEXT          Cuckoo Working Directory
    -h, --host TEXT     Host to bind the node API server on
    -p, --port INTEGER  Port to bind the node API server on
    -v, --verbose       Enable debug logging, including for non-Cuckoo modules
    -d, --debug         Enable verbose logging
    -q, --quiet         Only log warnings and critical messages
    --help              Show this message and exit.

    Commands:
    createcwd   Create the specified Cuckoo CWD
    getmonitor  Use the monitor and stager binaries from the given Cuckoo...

#### cuckoosafelist

This command/tool is used to manage Cuckoo safelists. The safelists are used
in modules such as network processing. 
A restart of Cuckoo is usually needed after adding entries.

##### Help

    $ cuckoosafelist --help

    Usage: cuckoosafelist [OPTIONS] COMMAND [ARGS]...

    Options:
    --cwd TEXT  Cuckoo Working Directory
    --help      Show this message and exit.

    Commands:
    add        Add a value to the specified safelist.
    clear      Delete all entries from the specified safelist.
    csvdump    Dump a safelist to a CSV file.
    csvimport  Import a safelist from a safelist CSV dump file.
    delete     Delete one or more safelist entries by ID.
    listnames  Show all existing safelists and their types.
    show       Print all entries of the specified safelist.

#### cuckoocleanup

This command/tool is used to export and deleted finished analyses older than the specified amount of
  days. This requires a remote Cuckoo setup running the API and running
  import mode. The API url and key to use here must be configured in the
  cuckoo.conf

##### Help

    $ cuckoocleanup --help

    Usage: cuckoocleanup [OPTIONS] COMMAND [ARGS]...

    Options:
    --cwd TEXT   Cuckoo Working Directory
    -d, --debug  Enable verbose logging
    --help       Show this message and exit.

    Commands:
    remotestorage  Export and deleted finished analyses older than the...

