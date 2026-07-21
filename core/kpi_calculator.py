"""
Generic KPI Calculator

Reusable KPI calculations across campaign types.
"""

class KPICalculator:

    @staticmethod
    def row_count(df):
        """Returns total number of rows."""

        return len(df)

    @staticmethod
    def unique(df, column):
        """Returns unique count for a column."""

        if column not in df.columns:
            return 0

        return df[column].nunique()

    @staticmethod
    def count(df, column):
        """Counts non-null values."""

        if column not in df.columns:
            return 0

        return df[column].count()

    @staticmethod
    def total(df, column):
        """Returns sum of numeric column."""

        if column not in df.columns:
            return 0

        return df[column].sum()

    @staticmethod
    def average(df, column):
        """Returns average."""

        if column not in df.columns:
            return 0

        return round(df[column].mean(), 2)

    @staticmethod
    def top_value(df, column):

        if column not in df.columns:
            return None

        return (
            df[column]
            .value_counts()
            .idxmax()
        )

    @staticmethod
    def change(before, after):
        """Absolute change between two period values."""

        return after - before

    @staticmethod
    def pct_change(before, after):
        """Percent change between two period values, or None if before is 0."""

        if not before:
            return None

        return round((after - before) / before * 100, 2)