# Cuckoo3 - Malware analysis tool
<img alt="Cuckoo3 logo" src="./INSTALL/logos/cuckoo3-github-readme-logo.png"/>

<a href="https://badge.fury.io/py/Cuckoo3"><img src="https://badge.fury.io/py/Cuckoo3.svg" alt="PyPI version" height="24"></a>
<img alt="GitHub License" src="https://img.shields.io/github/license/cert-ee/cuckoo3" height="24">
<img alt="GitHub contributors" src="https://img.shields.io/github/contributors/cert-ee/cuckoo3" height="24">
<img alt="GitHub Release" src="https://img.shields.io/github/v/release/cert-ee/cuckoo3?display_name=release&logoSize=24" height="24">

## About
Cuckoo3 is an open-source tool to test suspicious files or links in a controlled
environment.

It will test them in a sandboxed platform emulator(s) and generate a report, showing what the files 
or websites did during the test.

> ⚠️ You can currently only set up Cuckoo3 on Linux(Ubuntu) machines with Python 3.10 and run Windows sandboxes.  
Check our [Cuckoo3 requirements](https://cuckoo-hatch.cert.ee/static/docs/introduction/cuckoo/) for more information.

You can see it in action at our [online Cuckoo3 Sandbox](https://cuckoo-hatch.cert.ee/).  
For more insight into our plans, [check out our roadmap here](https://github.com/orgs/cert-ee/projects/1/views/1).


## Quickstart
To get started, we have created Quickstart script that installs and sets up everything you need to test out Cuckoo3.  

Run the following command in your terminal and follow on screen prompts.
```bash
curl -sSf https://cuckoo-hatch.cert.ee/static/install/quickstart | sudo bash

```

### A brief overview of Quickstart
Here is a short overview of what it will do:

- Create a new non sudo Cuckoo user.
- Install Cuckoo3 and VMCloak under that user.
- Download and prepare virtual machines.
- Configure Cuckoo.
- Installs UWSGI and Nginx.
- Serve the frontend using UWSGI and Nginx.

For the full list of things this script does, check out our [Quickstart walkthrough](INSTALL/QUICKSTART.md).



## Next steps
- For more in-depth guides and references, please check out our [documentation](https://cuckoo-hatch.cert.ee/static/docs/).

## IMPORTANT!
**This is not a production ready solution just yet.  
We highly advise you not to use it in production environment!**
