# State manager

**Part of main Cuckoo process**: yes

### What is it
The state manager is a component and is fully responsible for tracking new analyses, queueing work for an analysis or task, and updating the state of a analysis or task. 
It accepts IPC messages send to it and queues a function to execute with arguments from those messages.

Messages must be in JSON format separated by a newline character. A 'subject' key has to be present with a string value. This value determine what function will be queued by the controller.

All queued functions are executed by the controller worker. This is a thread that pops the queued functions from its queue and runs them.

Functions can also be queued by directly calling the controller from within the same process. An existing instance of the controller worker must be used to do so.

### The goal
The goal of the controller is to have a single point/thread/process where database writes are performed. This means it will be responsible for all analysis and task state updates.

### What it currently does

The controller currently:

* Creates new analysis rows in the database
* Update analysis states
* Queues work for each state update of a analysis
* Creates new tasks and task rows in the database for a analysis.
