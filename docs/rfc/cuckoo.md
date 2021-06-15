# Cuckoo

This document describes principles that Cuckoo should adhere.

### Storing analysis and task information
Complex information structures such as dictionaries should be stored in a simple manner if possible. A preferred way is as a JSON file on disk.
These files can be served directly from disk if requested by an API. Storing redundant results should be prevented. An example of this would be storing the same results
on disk and in MongoDB, just because it is the easier solution.

### The central database
The central Cuckoo database should only be used to keep track of existing 'things' such as analyses, tasks, targets, and their relations. It should
not be used for results. If a qeueryable result database is needed, it should be a different database.

### Multiprocessing
A components work should happen in a subprocess, instead of in the main Cuckoo process when:

* A lot of CPU time is used
    * This is because it can otherwise cause important main components to get less CPU time.
* The work it performs should be scalable

Python multiprocessing is currently used to start subprocesses. At Cuckoo start, the process start method is set to 'spawn'. The default appear to be fork.

### IPC
The IPC the processes use must be abstracted in such a way that the underlying IPC method can be replaced without having to rewrite a large part
of the code.

We are currently using Unix sockets. This will likely change as we also have to support running Cuckoo on Windows. Windows does not support Unix sockets.

### Packaging


Currently, there are 4 packages:

* Cuckoo - Cuckoo core (Cuckoo itself)
* Cuckoo-common
    * Contains 'common' code that can be used in other packages. Examples: config generation and reading, IPC helpers, Cuckoo CWD logic, and Cuckoo package helpers
    * May NOT import anything from other Cuckoo packages.
* Cuckoo-processing
    * Contains all the processing and reporting modules.
    * Processing modules are sorted by subpackages: identification, post, and pre
    * Reporting is a single subpackage.
* Cuckoo-machineries
    * Contains all supported machinery modules.