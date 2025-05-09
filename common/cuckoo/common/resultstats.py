# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.

import calendar
import datetime
from threading import Lock

from .analyses import count_submission
from .task import count_created as count_created_tasks
from .elastic import (
    analysis_unique_values_field,
    ElasticSearchError,
    analysis_count_field_val,
)


class StatisticsError(Exception):
    pass


class _StatisticsDateRange:
    NAME = ""
    DT_FMT = ""
    HUMAN_DESC = ""
    STEP_SIZE = None

    def __init__(self):
        self._start = None
        self._end = None
        self._point_ranges = []

    @property
    def start(self):
        if not self._start:
            self._set_start_end_dates()

        return self._start

    @property
    def end(self):
        if not self._end:
            self._set_start_end_dates()

        return self._end

    @property
    def point_ranges(self):
        if not self._point_ranges:
            self._make_point_ranges()

        return self._point_ranges

    @property
    def date_labels(self):
        return [p[2] for p in self.point_ranges]

    def _set_start_end_dates(self):
        raise NotImplementedError

    def _make_point_ranges(self):
        raise NotImplementedError


class Range24Hours(_StatisticsDateRange):
    NAME = "daily"
    DT_FMT = "%m-%d %H:%M"
    HUMAN_DESC = "24 hours"
    STEP_SIZE = datetime.timedelta(hours=1)

    def _set_start_end_dates(self):
        today = datetime.datetime.now().replace(minute=0, second=0)
        self._end = today
        self._start = today - datetime.timedelta(days=1)

    def _make_point_ranges(self):
        end_range = self.end
        for _ in range(24):
            start_range = end_range - self.STEP_SIZE
            self._point_ranges.insert(
                0, (start_range, end_range, end_range.strftime(self.DT_FMT))
            )
            end_range = start_range


class Range7Days(_StatisticsDateRange):
    NAME = "weekly"
    DT_FMT = "%a %d-%m %H:%M"
    HUMAN_DESC = "7 days"
    STEP_SIZE = datetime.timedelta(hours=12)

    def _set_start_end_dates(self):
        today = datetime.datetime.now()
        if today.hour <= 12:
            today = today.replace(hour=0, minute=0)
        else:
            today = today.replace(hour=12, minute=0)

        self._end = today
        self._start = today - datetime.timedelta(days=7)

    def _make_point_ranges(self):
        end_range = self.end
        for _ in range(14):
            start_range = end_range - self.STEP_SIZE
            self._point_ranges.insert(
                0, (start_range, end_range, end_range.strftime(self.DT_FMT))
            )
            end_range = start_range


class Range31Days(_StatisticsDateRange):
    NAME = "monthly"
    DT_FMT = "%y-%m-%d"
    HUMAN_DESC = "31 days"
    STEP_SIZE = datetime.timedelta(days=1)

    def _set_start_end_dates(self):
        today = datetime.datetime.now().replace(
            hour=23, minute=59, second=59, microsecond=0
        )

        self._end = today
        self._start = today - datetime.timedelta(days=31)

    def _make_point_ranges(self):
        end_range = self.end

        for _ in range(31):
            start_range = end_range - self.STEP_SIZE
            self._point_ranges.insert(
                0, (start_range, end_range, end_range.strftime(self.DT_FMT))
            )
            end_range = start_range


class Range12Months(_StatisticsDateRange):
    NAME = "yearly"
    DT_FMT = "%B %Y"
    HUMAN_DESC = "12 months"
    STEP_SIZE = datetime.timedelta(days=1)

    def _set_start_end_dates(self):
        currmonth_firstday = datetime.datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        daycount = calendar.monthrange(
            currmonth_firstday.year, currmonth_firstday.month
        )

        self._start = currmonth_firstday - datetime.timedelta(days=365)
        self._end = currmonth_firstday.replace(day=daycount[1], hour=23, minute=59)

    def _make_point_ranges(self):
        end_range = self.end
        for _ in range(12):
            daycount = calendar.monthrange(end_range.year, end_range.month)[1]
            end_range = end_range.replace(day=daycount, hour=23, minute=59)
            start_range = end_range.replace(day=1, hour=0, minute=0)

            self._point_ranges.insert(
                0, (start_range, end_range, end_range.strftime(self.DT_FMT))
            )
            end_range = start_range - datetime.timedelta(days=1)


class RangeTypes:
    DAILY = Range24Hours.NAME
    WEEKLY = Range7Days.NAME
    MONTHLY = Range31Days.NAME
    YEARLY = Range12Months.NAME

    _DATE_POINTMAKER = {
        DAILY: Range24Hours,
        WEEKLY: Range7Days,
        YEARLY: Range12Months,
        MONTHLY: Range31Days,
    }

    @staticmethod
    def all_types():
        return list(RangeTypes._DATE_POINTMAKER.keys())

    @staticmethod
    def valid(range_type):
        return range_type in RangeTypes._DATE_POINTMAKER

    @staticmethod
    def to_human(range_type):
        return RangeTypes._DATE_POINTMAKER[range_type].HUMAN_DESC

    @staticmethod
    def get_datepointmaker(range_type):
        try:
            return RangeTypes._DATE_POINTMAKER[range_type]
        except KeyError as e:
            raise StatisticsError(f"Invalid/unknown time range: {e}")


class _ChartData:
    def __init__(self, charttype, name, description, options={}):
        self._type = charttype
        self.name = name
        self.description = description
        self.options = options
        self.labels = []

        self._datasets = []

    def add_dataset(self, data, label=None):
        self._datasets.append({"data": data, "label": label})

    def to_dict(self):
        return {
            "type": self._type,
            "name": self.name,
            "description": self.description,
            "labels": self.labels,
            "datasets": self._datasets,
            "options": self.options,
        }


class StatisticsChart:
    KEY = ""
    CHARTTYPE = ""
    NAME = ""
    DESCRIPTION = ""

    def __init__(self, daterange, options={}):
        if not isinstance(options, dict):
            raise StatisticsError("Options must be a dictionary")

        self.range = daterange
        self.options = options

    def make_name_desc(self):
        name = self.NAME.replace("%RANGE%", self.range.HUMAN_DESC)
        desc = self.DESCRIPTION.replace("%RANGE%", self.range.HUMAN_DESC)
        return name, desc

    def retrieve_data(self):
        name, description = self.make_name_desc()
        chart_data = _ChartData(
            charttype=self.CHARTTYPE,
            name=name,
            description=description,
            options=self.options,
        )
        self._retrieve_data(chart_data)

        return chart_data

    def _retrieve_data(self, chartdata):
        raise NotImplementedError


class BarCountChart(StatisticsChart):
    CHARTTYPE = "bar"
    FIELD = ""

    def _retrieve_data(self, chart_data):
        try:
            labels_counts = analysis_unique_values_field(
                self.FIELD, start=self.range.start, end=self.range.end
            )
        except ElasticSearchError as e:
            raise StatisticsError(
                f"Failed to retrieve data for bar chart {self.FIELD}. {e}"
            )

        data = []
        for label, count in labels_counts:
            chart_data.labels.append(label)
            data.append(count)

        chart_data.add_dataset(data=data)


class FamilyCounts(BarCountChart):
    KEY = "families_bar"
    FIELD = "families"
    NAME = "Detected family counts"
    DESCRIPTION = "Counts per malware family of the last %RANGE%"


class BehaviorCategoryCounts(BarCountChart):
    KEY = "categories_bar"
    FIELD = "tags"
    NAME = "Detected behaviors counts"
    DESCRIPTION = "Counts of detected behavior of the last %RANGE%"


class TargetFileExt(BarCountChart):
    KEY = "targettypes_bar"
    FIELD = "target.fileext"
    NAME = "Submitted analysis file types"
    DESCRIPTION = "Submitted analysis file types the last %RANGE%"


class LineChart(StatisticsChart):
    CHARTTYPE = "line"
    FIELD = ""

    def _retrieve_data(self, chart_data):
        try:
            labels_counts = analysis_unique_values_field(
                self.FIELD, start=self.range.start, end=self.range.end
            )
        except ElasticSearchError as e:
            raise StatisticsError(
                f"Failed to retrieve data for bar chart {self.FIELD}. {e}"
            )

        for line_label, _ in labels_counts:
            data = []
            for start, end, _ in self.range.point_ranges:
                try:
                    data.append(
                        analysis_count_field_val(self.FIELD, line_label, start, end)
                    )
                except ElasticSearchError as e:
                    raise StatisticsError(
                        f"Failed to query data for line chart {self.FIELD}. {e}"
                    )

            chart_data.add_dataset(data=data, label=line_label)

        chart_data.labels = self.range.date_labels


class FamiliesLine(LineChart):
    KEY = "families_line"
    FIELD = "families"
    NAME = "Detected families over time"
    DESCRIPTION = "All detected malware families of the last %RANGE%"


class BehaviorCategoryLine(LineChart):
    KEY = "categories_line"
    FIELD = "tags"
    NAME = "Detected behavior over time"
    DESCRIPTION = "Detected behavior over time of the last %RANGE%"


class SubmissionsCountLine(LineChart):
    KEY = "submissions_line"
    NAME = "Submissions over time"
    DESCRIPTION = "The created analyses and their tasks over time of the last %RANGE%"

    def _retrieve_data(self, chart_data):
        for countfunc, data_label in (
            (count_submission, "Analyses"),
            (count_created_tasks, "Tasks"),
        ):
            data = []
            for start, end, _ in self.range.point_ranges:
                data.append(countfunc(start=start, end=end))

            chart_data.add_dataset(data=data, label=data_label)
        chart_data.labels = self.range.date_labels


class _ChartDataCacher:
    def __init__(self, chart_class, range_class, options):
        self._chart = chart_class
        self._range = range_class
        self._chart_options = options
        self._cache = {}
        self._expire_dt = None
        self._cache_lock = Lock()

    def _load_data(self):
        chart = self._chart(self._range(), options=self._chart_options)
        data = chart.retrieve_data().to_dict()
        self._expire_dt = datetime.datetime.now() + self._range.STEP_SIZE
        self._cache = data

    def retrieve_data(self):
        if not self._cache or datetime.datetime.now() > self._expire_dt:
            if self._cache_lock.acquire(blocking=False):
                try:
                    self._load_data()
                finally:
                    self._cache_lock.release()

        return self._cache


class ChartDataMaker:
    CHARTS = {
        FamiliesLine.KEY: FamiliesLine,
        BehaviorCategoryLine.KEY: BehaviorCategoryLine,
        FamilyCounts.KEY: FamilyCounts,
        BehaviorCategoryCounts.KEY: BehaviorCategoryCounts,
        TargetFileExt.KEY: TargetFileExt,
        SubmissionsCountLine.KEY: SubmissionsCountLine,
    }

    def __init__(self):
        self.charts = []

    def add_chart(self, name, rangetype, options={}):
        try:
            chart_class = self.CHARTS[name]
        except KeyError:
            raise StatisticsError(f"Unknown chart type: {name}")

        range_class = RangeTypes.get_datepointmaker(rangetype)

        self.charts.append(_ChartDataCacher(chart_class, range_class, options))

    def get_data(self):
        return [chartcache.retrieve_data() for chartcache in self.charts]


chartdata_maker = ChartDataMaker()
