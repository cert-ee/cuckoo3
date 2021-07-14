# Startup

All methods that setup/initialize/start one or more components must be in startup.py. Imports of components it starts must happen within the method. This is so startup
time is moved to runtime when something is actually started.

If something is started that must be stopped or cleaned up when Cuckoo stops, a shutdown/stop method must be registered. This can be done by importing shutdown.register_shutdown.

### Cuckoo startup and main process

When Cuckoo starts, it will first check if the given CWD (default .cuckoocwd) exists. If not, it will ask the user to create it with cuckoo createcwd.

If the CWD does exist. Cuckoo will start by loading configuration files and verifying its values. After this, the following components are started:

* Machinery manager (Thread with worker threads)
* Processing worker manager (Thread with worker processes)
* State controller (Main thread)
