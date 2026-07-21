"""
Lead Detail Dataset

Responsible ONLY for understanding the Lead Detail file.
"""

from core.date_engine import DateEngine


class LeadDetailDataset:

    def __init__(self, dataframe):

        self.df = DateEngine(dataframe).add_date_columns()

        self.periods = DateEngine(self.df).split_periods()

    @property
    def total_leads(self):
        return len(self.df)

    @property
    def unique_accounts(self):
        return self.df["Account Name"].nunique()

    @property
    def unique_assets(self):
        return self.df["Asset Name"].nunique()

    @property
    def unique_job_titles(self):
        return self.df["Job Title"].nunique()