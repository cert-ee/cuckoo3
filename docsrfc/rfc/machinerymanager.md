# Machinery manager

**Part of main Cuckoo process**: Yes

### What is it?
The machinery manager is component that can perform machine actions on loaded machinery modules. A machine can be started, stopped, etc by requesting a specific action for a given machine name.

The manager operates by receiving IPC messages from a machinery client (cuckoo.machineries.helpers.MachineryManagerClient) and queues these in a work queue. A number of worker threads (Currently 2) retrieve work from this queue.

Retrieved work is immediately executed. A work method will return an expected state, timeout, and an optional fallback action. When the work has been executed, it is added to a 'waiter' list.

The state of each entry in the waiters list is checked every time before a worker thread tries to retrieve work. If the state has not reached the expected state before the timeout, the fallback action is called. The machine is disabled (taken from pool of analysis machines. Resets during restart of Cuckoo) if no fallback action is specified.

A machine is disabled if work somehow fails: unexpected state, unhandled state, some unhandled exception, or the timeout is reached.

Whether work fails or succeeds (expected state reached before timeout), the MachineryManager will always send a reply to the requester of the action.


NOTE: different hypervisors act differently when perform actions on their VMs. Some APIs block, some do not. APIs that block should be handled by having multiple workers, but this might be something to think more about.

**Notes**

* When work is being performed for one machine, all other work for it is ignored until the first is completed.
