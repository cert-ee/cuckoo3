# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

from cuckoo.common import config
from cuckoo.common.resultstats import ChartDataMaker, RangeTypes


class _ChartType(config.String):

    def constraints(self, value):
        super().constraints(value)

        if value not in ChartDataMaker.CHARTS:
            raise config.ConstraintViolationError(
                f"Invalid chart type: {value}. Existing "
                f"types: {', '.join(ChartDataMaker.CHARTS.keys())}"
            )


class _ChartTimeRange(config.String):

    def constraints(self, value):
        super().constraints(value)

        if value not in RangeTypes.all_types():
            raise config.ConstraintViolationError(
                f"Invalid chart time range: {value}. "
                f"Existing ranges: {RangeTypes.all_types()}"
            )


exclude_autoload = []
typeloaders = {
    "web.yaml": {
        "remote_storage": {
            "enabled": config.Boolean(default_val=False),
            "api_url": config.HTTPUrl(),
            "api_key": config.String(sensitive=True)
        },
        "elasticsearch": {
            "indices": {
                "names": {
                    "analyses": config.String(default_val="analyses"),
                    "tasks": config.String(default_val="tasks"),
                    "events": config.String(default_val="events")
                },
            },
            "max_result_window": config.Int(default_val=10000),
            "hosts": config.List(config.HTTPUrl, ["http://127.0.0.1:9200"]),
            "user": config.String(allow_empty=True),
            "password": config.String(allow_empty=True),
            "ca_certs": config.String(allow_empty=True, default_val="/etc/ssl/certs/ca-certificates.crt"),
            "web_search": {
                "enabled": config.Boolean(default_val=False)
            },
            "statistics": {
                "enabled": config.Boolean(default_val=False),
                "charts": config.DictList(child_typeloaders={
                    "chart_type": _ChartType(),
                    "time_range": _ChartTimeRange()
                }, default_val=[
                    {
                        "chart_type": "submissions_line",
                        "time_range": "yearly"
                    },
                    {
                        "chart_type": "submissions_line",
                        "time_range": "monthly"
                    },
                    {
                        "chart_type": "families_bar",
                        "time_range": "weekly"
                    },
                    {
                        "chart_type": "families_line",
                        "time_range": "weekly"
                    },
                    {
                        "chart_type": "targettypes_bar",
                        "time_range": "monthly"
                    },
                    {
                        "chart_type": "categories_bar",
                        "time_range": "monthly"
                    }
                ])
            }
        },
        "web": {
            "downloads": {
                "submitted_file": config.Boolean(default_val=False),
                "allowed_subnets": config.String(allow_empty=False, default_val="127.0.0.0/8,10.0.0.0/8")
            }
        }
    }
}
