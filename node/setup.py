#!/usr/bin/env python
# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - https://cuckoosandbox.org/.
# See the file 'docs/LICENSE' for copying permission.

import setuptools
import platform
import sys

if sys.version[0] == "2":
    sys.exit(
        "The latest version of Cuckoo is Python >=3.6 only. Any Cuckoo version "
        "earlier than 3.0.0 supports Python 2."
    )

if platform.system().lower() != "linux":
    sys.exit("Cuckoo 3 only supports Linux hosts")

setuptools.setup(
    name="Cuckoo-node",
    version="0.1.0",
    author="Stichting Cuckoo Foundation",
    author_email="cuckoo@cuckoofoundation.org",
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
    description="Cuckoo Sandbox sample detonation node",
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "cuckoonode = cuckoo.node.main:main",
        ],
    },
    include_package_data=True,
    install_requires=[
        "Cuckoo-common==0.1.0",
        "Cuckoo-machineries==0.1.0",
        "aiohttp>=3.6.2, <3.7",
        "aiohttp-sse>=2.0.0, <2.1"
    ],
)
