# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

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
                    }
                ])
            }
        }
    }
}
