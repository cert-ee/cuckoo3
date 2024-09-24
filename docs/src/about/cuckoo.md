# What is Cuckoo3?

Cuckoo3 is an open-source tool to test suspicious files or links in a controlled 
environment.  

It will test them in [sandboxed](sandboxing.md) platform emulator(s) and generate a report, 
showing what the files or websites did during the test.

## Cuckoo3 requirements

|Supported|Name|version|
|---|---|---|
|Host|Linux||
|OS|Ubuntu|22.04|
|Language|Python|3.10|

## Supported sandbox environments

|Operating system|Version|Stager|Monitor|VMCloak option|
|---|---|---|---|---|
|Windows 7||Tmstage|Threemon|`--win7x64`|
|Windows 10|Build 1703|Tmstage|Threemon|`--win10x64`|
