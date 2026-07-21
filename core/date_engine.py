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

        # Quarterly / Custom

        if config.REPORT_MODE in [QUARTERLY, CUSTOM]:

            periods = {}

            for name, (start, end) in config.DATE_SPLITS.items():

                mask = (

                    (df["Date"] >= pd.to_datetime(start))

                    &

                    (df["Date"] <= pd.to_datetime(end))

                )

                periods[name] = df.loc[mask].copy()

            return periods

        # Monthly

        if config.REPORT_MODE == MONTHLY:

            periods = {}

            for month in sorted(

                df["Month Name"].unique(),

                key=lambda x: pd.to_datetime(x, format="%B").month

            ):

                periods[month] = df[

                    df["Month Name"] == month

                ].copy()

            return periods

        raise ValueError(

            f"Unknown REPORT_MODE : {config.REPORT_MODE}"

        )