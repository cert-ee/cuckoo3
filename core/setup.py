#!/usr/bin/env python
# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import setuptools
import platform
import sys

if sys.version[0] == "2":
    sys.exit(
        "The latest version of Cuckoo is Python >=3.8 only. Any Cuckoo version"
        " earlier than 3.0.0 supports Python 2."
    )

if platform.system().lower() != "linux":
    sys.exit("Cuckoo 3 only supports Linux hosts")

setuptools.setup(
    name="Cuckoo",
    author="",
    author_email="",
    packages=setuptools.find_namespace_packages(include=["cuckoo.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Flask",
        "Framework :: Pytest",
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
    keywords=(
        "cuckoo automated malware sandbox analysis project threat "
        "intelligence cert soc"
    ),
    python_requires=">=3.8",
    url="https://cuckoosandbox.org/",
    license="GPLv3",
    description="Automated Malware Analysis System",
    long_description=open("README.rst", "r").read(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "cuckoo = cuckoo.main:main",
            "cuckoosafelist = cuckoo.scripts.safelist:main",
            "cuckoocleanup = cuckoo.scripts.cleanup:main",
            "cuckoomigrate = cuckoo.scripts.migrate:main"
        ],
    },
    install_requires=[
        "Cuckoo-common>=0.1.1",
        "Cuckoo-processing>=0.1.1",
        "Cuckoo-machineries>=0.1.0",
        "Cuckoo-web>=0.1.2",
        "sqlalchemy>=1.4, <1.5",
        "sflock>=1.0, <1.1",
        "tabulate>=0.8, <0.9"
    ]
)
