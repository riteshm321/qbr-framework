from enum import Enum


class AnalysisType(Enum):
    FULL_CAMPAIGN = "Full Campaign"
    MONTH_OVER_MONTH = "Month over Month"
    QUARTER_OVER_QUARTER = "Quarter over Quarter"
    CUSTOM_DATE_RANGE = "Custom Date Range"