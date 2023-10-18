#!/usr/bin/env python
# Copyright (C) 2019-2022 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import setuptools
import sys

if sys.version[0] == "2":
    sys.exit(
        "The latest version of Cuckoo is Python >=3.8 only. Any Cuckoo version "
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
        "License :: OSI Approved :: European Union Public Licence 1.2 (EUPL 1.2)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
    url="https://cuckoosandbox.org/",
    license="GPLv3",
    description="Cuckoo data processing helpers and modules",
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        "Cuckoo-common>=0.1.0",
        "sflock>=1.0, <1.1",
        "protobuf>=3.20.1, <4.0.0",
        "httpreplay>=1.0, <1.1",
        "pefile>=2022.5.30, <2024.0.0",
        "oletools>=0.60.1, <0.61",
        "cryptography>=41.0.4, <42.0.0",
        "hyperscan>=0.2.0, <0.7",
        "yara-python>=4.2.0, <4.4",
        "roach>=1.0, <1.1",
        "suricatactl==0.0.1.dev3",
        "dpkt>=1.9.7.2, <1.10"
    ],
)
