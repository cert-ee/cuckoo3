# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import config

exclude_autoload = []
typeloaders = {
    "web.yaml": {
        "remote_storage": {
            "enabled": config.Boolean(default_val=False),
            "api_url": config.HTTPUrl(),
            "api_key": config.String(sensitive=True)
        },
        "search": {
            "enabled": config.Boolean(default_val=False)
        }
    }
}
