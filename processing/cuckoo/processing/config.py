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
    }
}
