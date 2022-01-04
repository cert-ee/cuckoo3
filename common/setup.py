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
    name="Cuckoo-common",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Security",
    ],
    python_requires=">=3.6",
    url="https://cuckoosandbox.org/",
    license="GPLv3",
    description="Cuckoo common and utility code",
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        "pyyaml",
        "jinja2",
        "requests",
        "python-dateutil",
        "sflock>=1.0, <1.1",
        "sqlalchemy>=1.4, <1.5",
        "elasticsearch>=7.8.1, <8.0",
        "elasticsearch-dsl>=7.2.1, <7.3",
        "vt-py>=0.5.4, <0.6",
        "pymisp>=2.4.135.3, <2.5",
        "aiohttp>=3.7.4, <3.8",
        "aiohttp-sse-client>=0.2.1, <0.3",
        "psutil>=5.8.0, <5.9",
        "alembic[tz]"
    ]
)
