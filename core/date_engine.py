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

    # The Purchased Leads Report has no plain "Date" column -- when a lead
    # counts is the date it was delivered to the client. Preferred in this
    # order: the client delivery date is what the client was invoiced against,
    # with the internal one as a fallback for exports missing it.
    DELIVERED_DATE_COLUMNS = (
        "Client Delivered Date",
        "Internal Delivered Date",
    )

    # e.g. "Mon Apr 13 2026 08:51:51 GMT+0000 (Coordinated Universal Time)".
    # The trailing timezone name in brackets defeats pandas' inference, so it
    # is stripped and the rest parsed explicitly.
    DELIVERED_DATE_FORMAT = "%a %b %d %Y %H:%M:%S GMT%z"

    def adopt_delivered_date(self):

        """
        Creates a "Date" column from whichever delivered-date column exists, so
        every downstream period split works on this report unchanged.

        Some delivered leads have no delivery date recorded. Those rows are
        given the date carried by the surrounding rows (forward-fill, then
        back-fill for a gap at the very start), which places them in the
        delivery run they belong to rather than dropping them -- dropping would
        make the period figures sum to less than the campaign total. In the
        exports seen so far every blank sits between two dates in the same
        month, so this resolves them unambiguously.

        Returns True when a Date column was created.
        """

        for column in self.DELIVERED_DATE_COLUMNS:

            if column not in self.df.columns:
                continue

            cleaned = (
                self.df[column]
                .astype(str)
                .str.replace(r"\s*\([^)]*\)\s*$", "", regex=True)
                .str.strip()
                .replace({"": None, "nan": None, "NaT": None, "None": None})
            )

            parsed = pd.to_datetime(
                cleaned,
                format=self.DELIVERED_DATE_FORMAT,
                errors="coerce",
                utc=True,
            )

            if parsed.notna().sum() == 0:
                # Unexpected format -- let pandas try before giving up, so a
                # future export style doesn't silently produce no dates.
                parsed = pd.to_datetime(cleaned, errors="coerce", utc=True)

            if parsed.notna().sum() == 0:
                continue

            missing = int(parsed.isna().sum())

            # Timezone dropped, then truncated to midnight. Both matter:
            # every window and period bound in this framework is a plain date,
            # so a delivery timestamped 14:30 on the campaign's final day would
            # otherwise fall outside a window ending at that day's 00:00 and be
            # dropped from the count. Normalising makes this column match the
            # day-level model used everywhere else.
            parsed = parsed.dt.tz_convert(None).dt.normalize()

            self.df["Date"] = parsed.ffill().bfill()

            print(
                f"  [LEADS] delivery dates read from '{column}'"
                + (
                    f"; {missing} lead(s) had no delivery date and were placed "
                    "in the surrounding delivery run"
                    if missing else ""
                )
            )

            return True

        return False

    def parse_dates(self):

        if "Date" not in self.df.columns:

            if self.adopt_delivered_date():
                # Already parsed to datetime above.
                return

        if "Date" not in self.df.columns:
            return

        if pd.api.types.is_datetime64_any_dtype(self.df["Date"]):
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