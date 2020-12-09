# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import config

typeloaders = {
    "identification.yaml": {
        "tags": config.Dict(
            config.List(config.String), allow_empty=True, default_val={
                "office": ["microsoft_word", "microsoft_excel",
                           "microsoft_powerpoint"],
                "dotnet": ["microsoft_dotnet"],
                "powershell": ["powershell"],
                "pdfreader": ["acrobat_reader"],
                "flash": ["flash"],
                "java": ["oracle_java"],
                "ruby": ["ruby"],
                "perl": ["perl"],
                "python": ["python"],
                "mediaplayer": ["mediaplayer"],
                "quicktime": ["quicktime"],
                "ace": ["ace"],
                "arc": ["arc"],
                "unarchive": ["unarchive"]
            }
        ),
        "log_unidentified": config.Boolean(default_val=False)
    },
    "virustotal.yaml": {
        "enabled": config.Boolean(default_val=True),
        "key": config.String(
            default_val="a0283a2c3d55728300d064874239b5346fb991317e8449fe43c902879d758088",
            sensitive=True
        ),
        "min_suspicious": config.Int(default_val=3, min_value=1),
        "min_malicious": config.Int(default_val=5, min_value=1)
    }
}
