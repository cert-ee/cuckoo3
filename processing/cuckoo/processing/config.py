# Copyright (C) 2020 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from cuckoo.common import config

exclude_autoload = []
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
    },
    "misp.yaml": {
        "enabled": config.Boolean(default_val=False),
        "url": config.HTTPUrl(),
        "verify_tls": config.Boolean(default_val=True),
        "key": config.String(sensitive=True),
        "timeout": config.Int(default_val=5, min_value=0),
        "processing": {
            "pre": {
                "event_limit": config.Int(default_val=1, min_value=1),
                "file": {
                    "hashes": config.List(
                        config.String, default_val=["sha256"]
                    )
                }
            },
            "post": {
                "query_limits": config.Dict(
                    config.Int, default_val={
                        "dst_ip": 10,
                        "domain": 10,
                        "url": 10
                    }
                ),
                "event_limits": config.Dict(
                    config.Int, default_val={
                        "dst_ip": 1,
                        "domain": 1,
                        "url": 1
                    }
                )
            }
        },
        "reporting": {
            "enabled": config.Boolean(default_val=False),
            "min_score": config.Int(default_val=7, min_value=1, max_value=10),
            "web_baseurl": config.HTTPUrl(allow_empty=True),
            "event": {
                "distribution": config.Int(allow_empty=True),
                "sharing_group": config.Int(allow_empty=True),
                "threat_level": config.Int(
                    allow_empty=True, min_value=0, max_value=4
                ),
                "analysis": config.Int(
                    allow_empty=True, min_value=0, max_value=2
                ),
                "galaxy_mitre_attack": config.Boolean(default_val=True),
                "publish": config.Boolean(default_val=False),
                "tags": config.List(
                    config.String, default_val=["Cuckoo Sandbox"],
                    allow_empty=True
                ),
                "attributes": {
                    "ip_addresses": {
                        "include": config.Boolean(default_val=True),
                        "ids": config.Boolean(default_val=False)
                    },
                    "domains": {
                        "include": config.Boolean(default_val=True),
                        "ids": config.Boolean(default_val=False)
                    },
                    "urls": {
                        "include": config.Boolean(default_val=True),
                        "ids": config.Boolean(default_val=False)
                    },
                    "mutexes": {
                        "include": config.Boolean(default_val=True),
                        "ids": config.Boolean(default_val=False)
                    },
                    "sample_hashes": {
                        "include": config.Boolean(default_val=True),
                        "ids": config.Boolean(default_val=False),
                        "upload_sample": config.Boolean(default_val=False)
                    },
                }
            }
        }
    }, "intelmq.yaml": {
        "processing": {
            "enabled": config.Boolean(default_val=False),
            "hosts": config.List(config.HTTPUrl, ["http://127.0.0.1:9200"]),
            "index_name": config.String(),
            "query_limit": config.Int(default_val=10, min_value=1),
            "event_limit": config.Int(
                default_val=1, min_value=1, max_value=10000
            ),
            "link_url": config.HTTPUrl(required=False)
        },
        "reporting": {
            "enabled": config.Boolean(default_val=False),
            "api_url": config.HTTPUrl(),
            "verify_tls": config.Boolean(default_val=True),
            "min_score": config.Int(default_val=7, min_value=1, max_value=10),
            "web_baseurl": config.HTTPUrl(allow_empty=True),
            "feed_accuracy": config.Int(
                allow_empty=True, min_value=0, max_value=100
            ),
            "event_description": config.String(
                default_val="Cuckoo Sandbox behavioral analysis",
                allow_empty=True
            )
        }
    }
}
