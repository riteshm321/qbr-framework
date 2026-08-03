"""
Period Resolver

Turns the user's chosen AnalysisType (see engine/analysis_options.py) into
concrete config.REPORT_MODE / config.DATE_SPLITS values.

Quarter, half and month boundaries are derived from whatever date range is
actually present in the loaded reports -- never hardcoded -- so the same
four choices work for any client's export, for any reporting period.
"""

import pandas as pd

import config
from constants import CAMPAIGN, MONTHLY, QUARTERLY, CUSTOM
from engine.analysis_options import AnalysisType


def detect_date_range(datasets):

    """Earliest / latest Date found across every loaded report."""

    starts = []
    ends = []

    for df in datasets.values():

        if "Date" not in df.columns:
            continue

        dates = pd.to_datetime(df["Date"], errors="coerce").dropna()

        if dates.empty:
            continue

        starts.append(dates.min())
        ends.append(dates.max())

    if not starts:
        raise ValueError(
            "None of the loaded reports have a usable Date column - "
            "cannot determine the campaign period."
        )

    return min(starts), max(ends)


def _calendar_quarters(start, end):

    """Calendar quarters (Q1 = Jan-Mar, etc.) overlapping [start, end],
    clipped to that range and numbered in chronological order."""

    quarters = []

    period = start.to_period("Q")
    end_period = end.to_period("Q")

    n = 1

    while period <= end_period:

        q_start = max(period.start_time, start)
        q_end = min(period.end_time, end)

        quarters.append((f"Q{n}", q_start, q_end))

        period += 1
        n += 1

    return quarters


def _fmt(date):
    return date.strftime("%Y-%m-%d")


def _prompt_date(label):

    while True:

        raw = input(f"  {label} (YYYY-MM-DD): ").strip()

        parsed = pd.to_datetime(raw, errors="coerce")

        if pd.notna(parsed):
            return parsed

        print("Could not parse that date, try again.")


def resolve(analysis_type, datasets):

    """
    Sets config.REPORT_MODE / config.DATE_SPLITS for this run and returns
    them as (report_mode, date_splits) for convenience.
    """

    start, end = detect_date_range(datasets)

    print(f"\nDetected campaign period: {_fmt(start)} to {_fmt(end)}\n")

    # Default: the whole detected campaign. Only Custom Date Range
    # narrows this, to exactly the one period the user asks for.
    window_start, window_end = start, end

    config.DATE_SPLITS = {}

    if analysis_type == AnalysisType.FULL_CAMPAIGN:

        config.REPORT_MODE = CAMPAIGN

    elif analysis_type == AnalysisType.MONTH_OVER_MONTH:

        config.REPORT_MODE = MONTHLY

    elif analysis_type == AnalysisType.QUARTER_OVER_QUARTER:

        quarters = _calendar_quarters(start, end)

        if len(quarters) < 2:

            print(
                "\nQuarter over Quarter needs at least 2 real calendar "
                "quarters to compare (roughly 6+ months of data) -- this "
                "campaign doesn't have that, so falling back to "
                "Month-over-Month analysis instead.\n"
            )

            config.REPORT_MODE = MONTHLY

        else:

            # Every real calendar quarter in the campaign is analyzed
            # automatically -- no manual picking, the same way Month
            # over Month analyzes every real month automatically.
            config.REPORT_MODE = QUARTERLY

    elif analysis_type == AnalysisType.CUSTOM_DATE_RANGE:

        print("Enter the period to analyze:")
        custom_start = _prompt_date("Start date")
        custom_end = _prompt_date("End date")

        config.REPORT_MODE = CUSTOM

        # The whole analysis (every dataset, every table/chart) is
        # scoped to exactly this one period -- nothing outside it is
        # considered. The comparison/trend slides split this single
        # period into two internally (see DateEngine.split_periods()),
        # rather than asking for two separate ranges up front.
        window_start, window_end = custom_start, custom_end

    else:

        raise ValueError(f"Unhandled AnalysisType: {analysis_type}")

    config.ANALYSIS_WINDOW = (_fmt(window_start), _fmt(window_end))

    print(f"\nUsing report mode: {config.REPORT_MODE}")
    print(f"  Analysis window: {config.ANALYSIS_WINDOW[0]} to {config.ANALYSIS_WINDOW[1]}")
    print()

    return config.REPORT_MODE, config.DATE_SPLITS
