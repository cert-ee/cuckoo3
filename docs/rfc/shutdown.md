# Shutdown

Cuckoo shutdown is managed by logic in shutdown.py. The module allows other components to register a shutdown/stop method.
The module automatically registers signal handlers for SIGTERM and SIGINT when anything uses its register_shutdown method.

The order of calling of shutdown/stop methods is determined by the order argument given when it was registered. The order must be a positive number.
