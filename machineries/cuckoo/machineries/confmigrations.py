# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

# This file contains configuration file migrations for this package.
# The migrations dict consists of the configuration file names of the current
# package. Each file can have one or more mapped migrations.
# Each migration entry consists of: a 'current version' key, and a tuple value
# with exactly 2 values.
# These values are: a migration function and a version the function migrates to.
# The migrations are performed until none are left.

# A migration function must accept a dict and return nothing. The dict it
# accepts is a dict of the config values of the file it is mapped to.

# Example:
# def _name_001_002(curr_cfg_dict):
#     """Rename 'old_example' to 'example'"""
#     curr_cfg_dict["example"] = curr_cfg_dict["old_example"]
#     del curr_cfg_dict["old_example"]
#
# def _name_002_010(curr_cfg_dict):
#     """Rename 'example' to 'new_example'"""
#     curr_cfg_dict["example_new"] = curr_cfg_dict["example"]
#     del curr_cfg_dict["example"]
#
# migrations = {
#     "name.yaml": {
#         "0.0.1": (_name_001_002, "0.0.2"),
#         "0.0.2": (_name_002_010, "0.1.0")
#     }
# }

migrations = {}
