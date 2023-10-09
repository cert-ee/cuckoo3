# Copyright (C) 2019-2023 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common import config

from .signatures.signature import Levels


class ScoringLevel(config.String):

    def constraints(self, value):
        super().constraints(value)

        try:
            Levels.to_score(value)
        except KeyError:
            raise config.ConstraintViolationError(
                f"Invalid score level {value}. "
                f"Possible levels: {list(Levels.LEVEL_SCORE.keys())}"
            )


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
        "log_unidentified": config.Boolean(default_val=False),
        "selection": {
            "extension_priority": config.List(
                config.String, allow_empty=True,
                default_val=["exe", "msi", "docm", "dotm", "doc", "xlam",
                             "xlsm", "xlsb", "xls", "ppsm", "pptm", "ppt",
                             "ps1", "vbs", "bat", "hta", "jar", "iqy",
                             "slk", "wsf", "lnk", "url", "pdf", "dll"]
            )
        }
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
    "irma.yaml": {
        "enabled": config.Boolean(default_val=False),
        "min_suspicious": config.Int(default_val=3, min_value=1),
        "min_malicious": config.Int(default_val=5, min_value=1),
        "timeout": config.Int(default_val=60, min_value=0),
        "scan": config.Boolean(default_val=False),
        "force": config.Boolean(default_val=False),
        "url": config.HTTPUrl(),
        "probes": config.String(),
        "submitter": config.String(),
        "rescan_time": config.Int(default_val=15, min_value=1),
    },
    "mhr.yaml": {
        "enabled": config.Boolean(default_val=False),
        "timeout": config.Int(default_val=60, min_value=0),
        "url": config.HTTPUrl(default_val="https://hash.cymru.com/v2/"),
        "user": config.String(allow_empty=True),
        "password": config.String(allow_empty=True),
        "min_suspicious": config.Int(default_val=10, min_value=1),
        "min_malicious": config.Int(default_val=17, min_value=1),
    },
    "misp.yaml": {
        "processing": {
            "enabled": config.Boolean(default_val=False),
            "url": config.HTTPUrl(),
            "verify_tls": config.Boolean(default_val=True),
            "key": config.String(sensitive=True),
            "timeout": config.Int(default_val=5, min_value=0),
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
            "url": config.HTTPUrl(),
            "verify_tls": config.Boolean(default_val=True),
            "key": config.String(sensitive=True),
            "timeout": config.Int(default_val=5, min_value=0),
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
                    config.String, default_val=["Cuckoo 3"],
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
    },
    "intelmq.yaml": {
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
                default_val="Cuckoo 3 behavioral analysis",
                allow_empty=True
            )
        }
    },
    "elasticsearch.yaml": {
        "enabled": config.Boolean(default_val=False),
        "indices": {
            "names": {
                "analyses": config.String(default_val="analyses"),
                "tasks": config.String(default_val="tasks"),
                "events": config.String(default_val="events")
            },
        },
        "timeout": config.Int(default_val=300),
        "max_result_window": config.Int(default_val=10000),
        "hosts": config.List(config.HTTPUrl, ["http://127.0.0.1:9200"]),
        "user": config.String(allow_empty=True),
        "password": config.String(allow_empty=True),
        "ca_certs": config.String(default_val="/etc/ssl/certs/ca-certificates.crt"),
    },
    "suricata.yaml": {
        "enabled": config.Boolean(default_val=False),
        "unix_sock_path": config.UnixSocketPath(
            default_val="/var/run/suricata/suricata-command.socket",
            must_exist=True, readable=True, writable=True
        ),
        "process_timeout": config.Int(default_val=60),
        "evelog_filename": config.String(default_val="eve.json"),
        "classification_config": config.FilePath(
            default_val="/etc/suricata/classification.config",
            must_exist=True, readable=True
        ),
        "classtype_scores": config.Dict(
            element_class=ScoringLevel, default_val={
                "command-and-control": "known bad",
                "exploit-kit": "known bad",
                "domain-c2": "malicious",
                "trojan-activity": "malicious",
                "targeted-activity": "likely malicious",
                "shellcode-detect": "likely malicious",
                "coin-mining": "likely malicious",
                "external-ip-check": "suspicious",
                "non-standard-protocol": "informational"
            }
        ),
        "ignore_sigids": config.List(config.Int, allow_empty=True)
    },
    "post.yaml": {
        "signatures": {
            "max_iocs": config.Int(default_val=100, min_value=1),
            "max_ioc_bytes": config.Int(default_val=1024 * 20, min_value=150)
        },
        "processes": {
            "max_processes": config.Int(default_val=100, min_value=1)
        }
    }
}
