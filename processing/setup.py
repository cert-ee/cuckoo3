#!/usr/bin/env python
# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import setuptools
import sys

if sys.version[0] == "2":
    sys.exit(
        "The latest version of Cuckoo is Python >=3.6 only. Any Cuckoo version "
        "earlier than 3.0.0 supports Python 2."
    )

setuptools.setup(
    name="Cuckoo-processing",
    author="",
    author_email="",
    packages=setuptools.find_namespace_packages(include=["cuckoo.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Security",
    ],
    python_requires=">=3.6",
    url="https://cuckoosandbox.org/",
    license="GPLv3",
    description="Cuckoo data processing helpers and modules",
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        "Cuckoo-common==0.1.0",
        "sflock>=1.0, <1.1",
        "protobuf>=3.12.2, <3.13.0",
        "httpreplay>=1.0, <1.1",
        "pefile>=2019.4.18, <2019.5.0",
        "oletools>=0.60, <0.61",
        "cryptography>=3.2, <3.3",
        "hyperscan>=0.1.5, <0.2",
        "yara-python>=4.0.2, <4.1",
        "roach>=1.0, <1.1",
        "suricatactl==0.0.1.dev3",
        "dpkt>=1.9.6, <1.10"
    ],
)
