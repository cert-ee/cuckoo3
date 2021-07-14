# Processing

**Part of main Cuckoo process**: No

### What is it?
By processing, we mean the process of interacting with submitted and collected information. This can lead to new information such as file type information, pattern matches, etc. The storing of this information must happen in the reporting phase.

Processing consists of two steps:

1. Running plugins that interact with submitted/collected information.
2. Running 'reporting' plugins that store/use information from step 1.


### How

Processing must be a scalable component. It therefore happens in its own process dedicated to a specific processing stage. 'Processing workers' achieve this. See the 'workerhandler.md' for more information about processing workers and their handler.

### Processing stage
There are three processing phases between submission and the final report:

1. Identification

Identification is the first processing stage. It runs once for each created analysis. It is to identify the submitted target. Only lightweight/fast plugins may run here. This is because this action is meant to completely quick, as it will happen immediately after submission. A user that submits through the web interface has to wait for it to complete, so that they can select/choose settings.

Currently, it identifies target(s) that are interesting to run, ignore safelisted files, make a final selection of the target to analyse, and to determine what platform it must run on. If no target is selected after this phase, the analysis is cancelled.

The most import plugin for Identification is 'identification'. It uses Sflock to determine the type of submitted file, the platform(s) it can run on, the dependencies it has, and if it is interesting to run.

After this stage the following must be true:

* An 'identification.json' exists in the analysis root directory with the following structure:

```python
"selected": bool,
"target": TargetFile or TargetURL,
"category": str,
"ignored": list,
"parent": str
```


2. Pre

Pre is the second processing stage. It runs once for every analysis. It runs after identification has completed and all settings are final. It is a phase meant to perform more heavy tasks that take more time and to perform steps to prepare a target if required. An example of this is various forms of static analysis such as running Yara against the selected target.

Currently, it normalizes (nested) archives to a zip with the selected target. This zip is placed in the root of the analysis directory.

After this stage the following must be true:

* If the submitted target was an (nested) archive, the most inner archive containing the selected target must be normalized to a ZIP file named 'target.zip'. It must be in the root of the analysis directory.

After the pre processing finishes, the controller will create the tasks for the analysis.


3. Post

Post is the third and last stage of processing. It runs for every created task. This phase is responsible for interpreting the collected behavior, running signatures, scoring, etc.