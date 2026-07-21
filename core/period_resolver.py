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


def _prompt_choice(prompt, labels):

    print(prompt)

    for i, label in enumerate(labels, start=1):
        print(f"  {i}. {label}")

    while True:

        raw = input("Enter choice number: ").strip()

        if raw.isdigit() and 1 <= int(raw) <= len(labels):
            return int(raw) - 1

        print("Invalid choice, try again.")


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

    if analysis_type == AnalysisType.FULL_CAMPAIGN:

        config.REPORT_MODE = CAMPAIGN
        config.DATE_SPLITS = {}

    elif analysis_type == AnalysisType.MONTH_OVER_MONTH:

        config.REPORT_MODE = MONTHLY
        config.DATE_SPLITS = {}

    elif analysis_type == AnalysisType.QUARTER_OVER_QUARTER:

        quarters = _calendar_quarters(start, end)

        if len(quarters) < 2:

            print(
                "Only one calendar quarter is present in this data - "
                "falling back to Full Campaign."
            )

            config.REPORT_MODE = CAMPAIGN
            config.DATE_SPLITS = {}

        else:

            if len(quarters) > 2:

                labels = [
                    f"{name}: {_fmt(qs)} to {_fmt(qe)}"
                    for name, qs, qe in quarters
                ]

                idx_a = _prompt_choice(
                    "Multiple quarters detected. Pick the FIRST period:",
                    labels
                )

                idx_b = _prompt_choice(
                    "Pick the SECOND period:",
                    labels
                )

            else:

                idx_a, idx_b = 0, 1

            _, sa, ea = quarters[idx_a]
            _, sb, eb = quarters[idx_b]

            config.REPORT_MODE = QUARTERLY
            config.DATE_SPLITS = {
                "Q1": (_fmt(sa), _fmt(ea)),
                "Q2": (_fmt(sb), _fmt(eb)),
            }

    elif analysis_type == AnalysisType.CUSTOM_DATE_RANGE:

        print("Enter the FIRST period to analyze:")
        a_start = _prompt_date("Start date")
        a_end = _prompt_date("End date")

        print("Enter the SECOND period to analyze:")
        b_start = _prompt_date("Start date")
        b_end = _prompt_date("End date")

        config.REPORT_MODE = CUSTOM
        config.DATE_SPLITS = {
            "Q1": (_fmt(a_start), _fmt(a_end)),
            "Q2": (_fmt(b_start), _fmt(b_end)),
        }

    else:

        raise ValueError(f"Unhandled AnalysisType: {analysis_type}")

    print(f"\nUsing report mode: {config.REPORT_MODE}")

    if config.DATE_SPLITS:

        for name, (s, e) in config.DATE_SPLITS.items():
            print(f"  {name}: {s} to {e}")

    print()

    return config.REPORT_MODE, config.DATE_SPLITS
