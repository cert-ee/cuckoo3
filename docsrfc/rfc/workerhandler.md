# Processing Worker handler

**Part of main Cuckoo process**: Yes

### What is it?
The worker handler is a component that starts processing workers, has queues of processing tasks for each processing stage, and assigns tasks from these queues to the workers.

A state is kept track of for each worker. These states can be: SETUP, IDLE, or WORKING.

A worker can send the state messages: READY, FINISHED, WORK_FAIL, SETUP_FAIL.

The handlers starts a configured amount of dedicated worker processes for each stage of processing. It does this when Cuckoo starts. A good default still has to be determined. At the moment it starts 2 idenfitication workers, 1 pre worker, and 1 post worker.

**Worker setup**

The following steps are performed when starting a worker.

1. Determine the name for the worker. This is type+counter.
2. Create an instance of a worker and start the process.
3. Set the state of the worker to SETUP.
4. As soon as the unix socket path has been created by the worker, connect to it.
5. Set the state to IDLE when READY has been received.

Todo is: handle SETUP_FAIL.

**Work assignment**

The following steps are performed to assign queues jobs to workers.

1. Find queues that are not empty.
2. Search for a worker that has the IDLE state with the type of found queues.
3. Pop the work from the queue
4. Message the selected worker the analysis and task id, and the analysis path.
5. Set the worker state to WORKING.

**Finished work**

1. Receive a FINISH or WORK_FAILED message.
2. Queue a work done or fail handler in the controller handler.
3. Set the worker to IDLE


# Workers

**Part of main Cuckoo process**: No

### What is it?
A processing worker is a generic worker that can load processing plugins. The worker handler will tell it what stage of processing to dedicate to. It will load the plugins for that stage as a response.

A worker receives an analysis id and potentially a task number. This depends on the type of processing stage it dedicates itself to.

**Setup steps**

When a worker is started, the following steps are performed:

1. Import the plugins for its processing stage
2. Initialize each plugin class to load things that only need to be loaded once.
3. Create a unix socket identical to its name.
4. Accept one connection (Should be the worker handler)
5. If plugins were loaded and initilialized successfully, message the READY state, else SETUP_FAIL.


**Work steps**

For each new job it receives, the following steps are performed:

1. Create the correct analysis directory path for the received analysis id.
2. Determine the filepath to the target if the target is a file.
3. Create an instance of each plugin for this stage.
4. Load available stage information JSON files (analysis.json, identification.json, etc) from the analysis directory.
5. Pass paths and loaded information to plugins.
6. Run the processing plugins

    6.1 If a 'fatal error' occurs, stop running processing plugins.

7. Run reporting plugins

    7.1 If any errors occurred, include these in the JSON file for this stage.

8. Send a FINISHED or WORK_FAIL message to the worker handler depending on if the any fatal errors occurred.
