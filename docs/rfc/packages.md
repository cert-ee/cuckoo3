# Cuckoo Sandbox packages

Cuckoo Sandbox 3 consists of multiple packages.

A package MUST have a directory called 'data'. This directory is used to ship anything that is not part of the importable code.

The data directory must at least contain a .cuckoopackage file. This is simply an empty file. It is currently needed as it is used to determine if a Cuckoo package is indeed a Cuckoo package.


#### Configuration files:
Configuration files are YAML and have templates. These are rendered using Jinja2 with values shipped with the package. Values are verified upon loading by a 'typeloader' from cuckoo.common.config.

Configuration files are generated to {CuckooCWD}/conf/{Subpackage name}/{confname}.yaml.

1. Create a config.py in the root of the package.
2. Declare a variable called 'typeloaders'. This must be a dictionary of key: typeloader.
    * typeloaders are value verification tools that can be imported from cuckoo.common.config.

Example (Creating a kvm.yaml conf):

```python
typeloaders = {
    "kvm.yaml": {
         "dsn": config.String(default_val="qemu:///system")
    }
}
```

3. Create a 'conftemplates' directory and add a 'kvm.yaml.jinja2' file. This file is the template for the configuration. A template filename must be in the following format: {goal/module/etc}.yaml.jinja2.
