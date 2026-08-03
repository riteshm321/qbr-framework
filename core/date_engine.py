"""
Date Engine

Responsible for:

- Date Parsing
- Date Validation
- Adding Year / Month / Quarter
- Splitting data into reporting periods

Version : 0.3
"""

import pandas as pd

import config
from constants import CAMPAIGN, MONTHLY, QUARTERLY, CUSTOM


class DateEngine:

    def __init__(self, dataframe):

        self.df = dataframe.copy()

    # -------------------------------------------------
    # Parse Date Column
    # -------------------------------------------------

    def parse_dates(self):

        if "Date" not in self.df.columns:
            return

        sample = str(
            self.df["Date"].dropna().iloc[0]
        )

        # yyyy-mm-dd

        if sample.startswith("20"):

            self.df["Date"] = pd.to_datetime(

                self.df["Date"],

                format="%Y-%m-%d",

                errors="coerce"

            )

        # dd-mm-yy

        else:

            self.df["Date"] = pd.to_datetime(

                self.df["Date"],

                format="%d-%m-%y",

                errors="coerce"

            )

    # -------------------------------------------------
    # Add Date Columns
    # -------------------------------------------------

    def add_date_columns(self):

        self.parse_dates()

        if "Date" not in self.df.columns:
            return self.df

        self.df["Year"] = self.df["Date"].dt.year

        self.df["Month"] = self.df["Date"].dt.month

        self.df["Quarter"] = self.df["Date"].dt.quarter

        self.df["Month Name"] = self.df["Date"].dt.month_name()

        return self.df

    # -------------------------------------------------
    # Split into reporting periods
    # -------------------------------------------------

    def split_periods(self):

        df = self.add_date_columns()

        # Campaign Mode

        if config.REPORT_MODE == CAMPAIGN:

            return {

                "Campaign": df

            }

        # Quarterly: every real calendar quarter in the campaign,
        # analyzed automatically -- same idea as Monthly below, just
        # bucketed by quarter instead of by month. config.ANALYSIS_WINDOW
        # is the whole detected campaign for this mode (set in
        # period_resolver.py), so this naturally covers every quarter,
        # not just a couple the user manually picked.

        if config.REPORT_MODE == QUARTERLY:

            periods = {}

            window_start = pd.to_datetime(config.ANALYSIS_WINDOW[0])
            window_end = pd.to_datetime(config.ANALYSIS_WINDOW[1])

            for period in pd.period_range(window_start, window_end, freq="Q"):

                quarter_start = max(period.start_time, window_start)
                quarter_end = min(period.end_time, window_end)

                mask = (df["Date"] >= quarter_start) & (df["Date"] <= quarter_end)

                quarter_df = df.loc[mask].copy()

                if quarter_df.empty:
                    continue

                quarter_df.attrs["period_bounds"] = (quarter_start, quarter_end)

                periods[f"Q{period.quarter} {period.year}"] = quarter_df

            return periods

        # Custom Date Range: the single period the user asked for,
        # split into a first half and second half -- so the comparison/
        # trend slides still have a before/after to show, without
        # requiring the user to specify two separate ranges up front.
        # config.ANALYSIS_WINDOW is exactly that one period for this mode.

        if config.REPORT_MODE == CUSTOM:

            window_start = pd.to_datetime(config.ANALYSIS_WINDOW[0])
            window_end = pd.to_datetime(config.ANALYSIS_WINDOW[1])

            midpoint = window_start + (window_end - window_start) / 2

            first_half = df.loc[
                (df["Date"] >= window_start) & (df["Date"] <= midpoint)
            ].copy()

            second_half = df.loc[
                (df["Date"] > midpoint) & (df["Date"] <= window_end)
            ].copy()

            first_half.attrs["period_bounds"] = (window_start, midpoint)
            second_half.attrs["period_bounds"] = (midpoint, window_end)

            return {
                "Period 1": first_half,
                "Period 2": second_half,
            }

        # Monthly

        if config.REPORT_MODE == MONTHLY:

            periods = {}

            # Walk every real calendar month in the full campaign window
            # (already known from config.ANALYSIS_WINDOW, detected across
            # every loaded report), but only keep a month that this
            # dataset (self.leads) actually has rows in -- a month with
            # no leads at all is skipped entirely, consistently, from
            # every slide that lists months (agenda, detail slides,
            # comparison table, trend chart), rather than appearing with
            # an all-zero row. Months that DO have data still get their
            # true calendar bounds (clipped to the campaign's actual
            # start/end) rather than wherever this dataset's own rows
            # happen to start/stop within the month.
            window_start = pd.to_datetime(config.ANALYSIS_WINDOW[0])
            window_end = pd.to_datetime(config.ANALYSIS_WINDOW[1])

            for period in pd.period_range(window_start, window_end, freq="M"):

                month_start = max(period.start_time, window_start)
                month_end = min(period.end_time, window_end)

                mask = (df["Date"] >= month_start) & (df["Date"] <= month_end)

                month_df = df.loc[mask].copy()

                if month_df.empty:
                    continue

                month_df.attrs["period_bounds"] = (month_start, month_end)

                periods[period.strftime("%B")] = month_df

            return periods

        raise ValueError(

            f"Unknown REPORT_MODE : {config.REPORT_MODE}"

        )