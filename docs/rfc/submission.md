# Analyses and tasks

Analyses are created for a submitted target. Zero or more tasks are created after target has been through the identification phase. The amount of tasks depend on the identified required platforms, if a target is selected (determined by Sflock), or if a target type is safelisted/ignored. The created tasks are tied to an analysis.


# Submission

**Part of main Cuckoo process**: No

Submission consists of four steps:

1. Accepting the settings and target for analysis
2. Creating a new file in the binary storage if not already present
3. Creating a analysis directory and subdirectories
4. Writing a analysis.json file containing the settings and information about the target
5. Notifying the controller of the new analysis.

Analyses are untracked until the 'controller' creates them in the database. Tasks are only created after the identification phase has run.

### 1. Accepting the settings and target

The accepting of settings and a target to analyse can happen through multiple endpoints: command line, web API and web interface. The source of the settings and target should not have any impact for the implementation.

Available settings are:

- timeout (integer)
    * The timeout of all created tasks in seconds
- priority (integer)
    * The priority can be used to move tasks to infront of queued tasks with a lower priority.
- platforms (list of strings) TODO: rename this? Do we want to include the os_version here or in a different field?
    * A list of dictionaries with 'platform' and 'os_version' keys. os_version can only be specified if platform is specified. Both values must be strings. Platform names and os_versions will be used to choose the machines of the specified platforms.
- manual (boolean)
    * A boolean that determines if the next state after identification is 'WAITING_MANUAL', to allow a user to select a file and change settings such as chosen platforms.

Settings must be accepted accepted and verified through a StrictContainer. These verify the type of a field and can check field constraints.

Available settings in the future:

- enforce_timeout (boolean)
    * A boolean determining if the tasks must run until the timeout, even if a target exits before that.
- dump_memory (boolean)
    * A boolean determining if the machine memory should be dumped at the end of a task.
- options (dictionary)
    * A dictionary containing additional settings.

```python
"timeout": int,
"enforce_timeout": bool,
"dump_memory": bool,
"priority": int,
"options": dict,
"platforms": list,
"machines": list,
"manual": bool

```

### 2. Storing the submitted file

If the submitted target is a file, it will be stored in a central binaries storage folder. All files
are only stored once. If the file has already been submitted before, the already existing copy will be used.

**Storing a file**

Files are stored with their sha256 hash as a filename to allow for instant lookups. Files are stored in subdirectories equal to the first, second, etc character of the sha256 hash. We do this to reduce the chance of reaching the limit of files per directory.

We currently do this 2 directories deep.

### 3. Creating the required directories

*Analysis location*
Submitted analyses are located in the analyses folder in the storage folder of the Cuckoo working directory. They are grouped by a day directory of the day the analysis was created. The analysis folder names in the day directory are random strings.

*Analysis id*
The analysis id consists of analysis creation date and the random string. The current format is: YYYYMMDD-XXXXXX, where X can be any in A-Z,0-9.

The id is used to find the directory of the analysis.

The random part of the id is only chosen the the directory does not already exist.


### 4. Storing analysis information

All given settings, the analysis id, creation datetime, target category, and target information are stored in a json dump called 'analysis.json' in the analysis directory root.


```python
"id": str,
"settings": Settings,
"created_on": datetime.datetime,
"category": str,
"submitted": SubmittedFile or SubmittedURL

```

### 5. Storing the untracked analysis id

The analysis is not stored in a database at this point. We refer to it as untracked. The creating of the analysis row(s) is the job of the controller. A file named after the analysis id is touched in the 'untracked' directory in the CWD/storage folder. This is used by the controller to know which analyses are untracked.

### 5. Notifying the controller

The controller is notified after all steps above have been performed for all targets that have been submitted. Notifying currently means sending a `{'subject':'tracknew'}` message over a unix socket to the controller process.

