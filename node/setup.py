#!/usr/bin/env python
# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import setuptools
import platform
import sys

if sys.version[0] == "2":
    sys.exit(
        "The latest version of Cuckoo is Python >=3.8 only. Any Cuckoo version "
        "earlier than 3.0.0 supports Python 2."
    )

if platform.system().lower() != "linux":
    sys.exit("Cuckoo 3 only supports Linux hosts")

setuptools.setup(
    name="Cuckoo-node",
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
    description="Cuckoo sample detonation node",
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "cuckoonode = cuckoo.node.main:main",
            "cuckoorooter = cuckoo.node.scripts.rooter:main"
        ],
    },
    include_package_data=True,
    install_requires=[
        "Cuckoo-common>=0.1.0",
        "Cuckoo-machineries>=0.1.0",
        "aiohttp>=3.8.1, <3.9",
        "aiohttp-sse>=2.1.0, <2.2"
    ],
)
