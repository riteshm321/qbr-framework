import pandas as pd
from core.kpi_calculator import KPICalculator

from constants import (
    LEAD_DETAIL,
    ACCOUNT_ENGAGEMENT,
    TRENDING_TOPICS,
    TRENDING_ACCOUNTS,
    ASSET_DELIVERY
)

class LeadGenAnalyzer:

    def __init__(self, datasets):

        self.datasets = datasets

        self.results = {

            "executive": {},

            "audience": {},

            "content": {},

            "intent": {},

            "trend": {},

            "strategic": {}

        }

        self.tables = {}

        # Dataset shortcuts
        self.leads = datasets[LEAD_DETAIL]
        self.account_engagement = datasets[ACCOUNT_ENGAGEMENT]
        self.trending_topics = datasets[TRENDING_TOPICS]
        self.trending_accounts = datasets[TRENDING_ACCOUNTS]
        self.asset_delivery = datasets[ASSET_DELIVERY]

        from core.date_engine import DateEngine

        self.periods = DateEngine(self.leads).split_periods()

    # ------------------------------------------------

    def total_leads(self):

        leads = self.leads

        self.results["executive"]["Total Leads"] = len(leads)

    # ------------------------------------------------

    def unique_accounts(self):

        leads = self.leads

        self.results["executive"]["Unique Accounts"] = \
            leads["Account Name"].nunique()

    # ------------------------------------------------

    def unique_assets(self):

        leads = self.leads

        self.results["executive"]["Assets Used"] = \
            leads["Asset Name"].nunique()

    # ------------------------------------------------

    def unique_job_titles(self):

        leads = self.leads

        self.results["executive"]["Job Titles"] = \
            leads["Job Title"].nunique()
        
    # ------------------------------------------------

    def unique_topics(self):

        topics = self.trending_topics

        self.results["executive"]["Trending Topics"] = \
            topics["Topic"].nunique()

    # ------------------------------------------------

    def unique_countries(self):

        leads = self.leads

        self.results["executive"]["Countries"] = \
            leads["Country"].nunique()
        
    # ------------------------------------------------

    def top_accounts(self):

        leads = self.leads

        self.top_accounts_df = (
            leads.groupby("Account Name")
            .size()
            .sort_values(ascending=False)
            .head(20)
            .reset_index(name="Leads")
        )

    # ------------------------------------------------

    def top_assets(self):

        leads = self.leads

        self.top_assets_df = (
            leads.groupby("Asset Name")
            .size()
            .sort_values(ascending=False)
            .reset_index(name="Leads")
        )

    # ------------------------------------------------

    def top_job_titles(self):

        leads = self.leads

        self.job_title_df = (
            leads.groupby("Job Title")
            .size()
            .sort_values(ascending=False)
            .reset_index(name="Leads")
        )

    # ------------------------------------------------

    def monthly_leads(self):

        leads = self.leads

        self.month_df = (
            leads.groupby("Month")
            .size()
            .reset_index(name="Leads")
        )

    # ------------------------------------------------

    def quarterly_leads(self):

        leads = self.leads

        self.quarter_df = (
            leads.groupby("Quarter")
            .size()
            .reset_index(name="Leads")
        )

    def build_executive_table(self):

        executive = self.results["executive"]

        rows = []

        for kpi, overall_value in executive.items():

            row = {
                "KPI": kpi,
                "Overall": overall_value,
                "Change":  None,
                "% Change": None
            }

            # -----------------------------------
            # Calculate period values
            # -----------------------------------

            if kpi == "Total Leads":

                for period_name, period_df in self.periods.items():

                    row[period_name] = KPICalculator.row_count(period_df)

            elif kpi == "Unique Accounts":

                for period_name, period_df in self.periods.items():

                    row[period_name] = KPICalculator.unique(
                                            period_df,
                                            "Account Name"
                                        )
            
            elif kpi == "Assets Used":

                for period_name, period_df in self.periods.items():

                    row[period_name] = KPICalculator.unique(
                                                period_df,
                                                "Asset Name"
                                            )
                    
            elif kpi == "Job Titles":

                for period_name, period_df in self.periods.items():

                    row[period_name] = KPICalculator.unique(
                                                period_df,
                                                "Job Title"
                                            )
                    
            elif kpi == "Countries":

                for period_name, period_df in self.periods.items():

                    row[period_name] = KPICalculator.unique(
                                                period_df,
                                                "Country"
                                            )
                    
            if "Q1" in row and "Q2" in row:

                row["Change"] = row["Q2"] - row["Q1"]

                if row["Q1"] != 0:
                    row["% Change"] = round(
                        (row["Change"] / row["Q1"]) * 100,
                        2
                    )

            rows.append(row)

        self.tables["Executive"] = pd.DataFrame(rows)

    # ------------------------------------------------

    def run(self):

        self.total_leads()

        self.unique_accounts()

        self.unique_assets()

        self.unique_job_titles()

        self.unique_countries()

        self.unique_topics()

        self.top_accounts()

        self.top_assets()

        self.top_job_titles()

        self.monthly_leads()

        self.quarterly_leads()

        self.build_executive_table()

        self.build_campaign_snapshot()

        self.build_period_tables()

        self.build_asset_performance_table()

        self.build_engagement_summary()

        self.build_top_engaged_accounts()

        self.build_trending_topics_table()

        self.build_topic_categories()

        self.build_top_intent_companies()

        self.build_qoq_comparison()

        self.build_optimization_insights()

        self.build_trending_account_summary()

        self.build_buying_stage_table()

        self.build_funnel_table()

        self.build_conversion_table()

        self.build_asset_summary()

        self.build_asset_ranking()

        self.build_asset_contribution()

        self.build_asset_efficiency()

        return self
    
    def build_period_tables(self):

        for period_name, df in self.periods.items():

            rows = []

            rows.append({
                "Metric": "Total Leads",
                "Value": len(df)
            })

            rows.append({
                "Metric": "Unique Accounts",
                "Value": df["Account Name"].nunique()
            })

            rows.append({
                "Metric": "Assets Used",
                "Value": df["Asset Name"].nunique()
            })

            rows.append({
                "Metric": "Job Titles",
                "Value": df["Job Title"].nunique()
            })

            rows.append({
                "Metric": "Countries",
                "Value": df["Country"].nunique()
            })

            rows.append({
                "Metric": "Top Asset",
                "Value": df["Asset Name"].mode().iloc[0]
                if not df.empty else ""
            })

            rows.append({
                "Metric": "Top Topic",
                "Value": df["Top MLI Topic (Average Over Last 7 Weeks)"].mode().iloc[0]
                if not df.empty else ""
            })

            self.tables[f"{period_name} Summary"] = pd.DataFrame(rows)

    def build_asset_performance_table(self):

        asset = (
            self.leads
            .groupby("Asset Name")
            .agg(
                Leads=("Account Name", "count"),
                Accounts=("Account Name", "nunique")
            )
            .reset_index()
        )

        asset = asset.sort_values(
            "Leads",
            ascending=False
        )

        asset.insert(0, "Rank", range(1, len(asset)+1))

        self.tables["Asset Performance"] = asset

    def build_engagement_summary(self):

        df = self.account_engagement

        rows = []

        rows.append({
            "Metric": "Total Impressions",
            "Value": df["Display Impressions"].sum()
        })

        rows.append({
            "Metric": "Total Clicks",
            "Value": df["Clicks"].sum()
        })

        rows.append({
            "Metric": "Total Site Visits",
            "Value": df["Site Visits"].sum()
        })

        rows.append({
            "Metric": "Exposure Time (Minutes)",
            "Value": round(df["Exposure Time (Minutes)"].fillna(0).sum(), 2)
        })

        rows.append({
            "Metric": "Average CTR",
            "Value": round(df["Click Through Rate"].mean(), 2)
        })

        self.tables["Engagement Summary"] = pd.DataFrame(rows)

    def build_top_engaged_accounts(self):

        df = self.account_engagement

        table = (
            df.groupby("Account Name")
            .agg(
                Leads=("Leads", "sum"),
                Clicks=("Clicks", "sum"),
                SiteVisits=("Site Visits", "sum"),
                Impressions=("Display Impressions", "sum")
            )
            .reset_index()
        )

        table = table.sort_values(
            by=["Leads", "Clicks"],
            ascending=False
        )

        table.insert(0, "Rank", range(1, len(table)+1))

        self.tables["Top Engaged Accounts"] = table.head(20)

    def build_trending_topics_table(self):

        df = self.trending_topics

        table = (
            df.groupby("Topic")
            .size()
            .reset_index(name="Mentions")
            .sort_values(
                "Mentions",
                ascending=False
            )
        )

        table.insert(0, "Rank", range(1, len(table)+1))

        self.tables["Trending Topics"] = table.head(20)

    def build_topic_categories(self):

        df = self.trending_topics

        table = (
            df.groupby("Category")
            .size()
            .reset_index(name="Mentions")
            .sort_values(
                "Mentions",
                ascending=False
            )
        )

        self.tables["Topic Categories"] = table

    def build_top_intent_companies(self):

        df = self.trending_topics

        table = (
            df.groupby("Company")
            .agg(
                MLScore=("ML Insights Score","mean")
            )
            .reset_index()
            .sort_values(
                "MLScore",
                ascending=False
            )
        )

        self.tables["Top Intent Companies"] = table.head(20)

    def build_qoq_comparison(self):

        q1 = self.periods["Q1"]
        q2 = self.periods["Q2"]

        comparison = []

        metrics = [

            ("Total Leads",
            len(q1),
            len(q2)),

            ("Unique Accounts",
            q1["Account Name"].nunique(),
            q2["Account Name"].nunique()),

            ("Assets Used",
            q1["Asset Name"].nunique(),
            q2["Asset Name"].nunique()),

            ("Job Titles",
            q1["Job Title"].nunique(),
            q2["Job Title"].nunique()),

            ("Countries",
            q1["Country"].nunique(),
            q2["Country"].nunique())

        ]

        for metric, q1_value, q2_value in metrics:

            change = q2_value - q1_value

            pct = 0

            if q1_value != 0:
                pct = round((change / q1_value) * 100, 2)

            comparison.append({

                "Metric": metric,

                "Q1": q1_value,

                "Q2": q2_value,

                "Change": change,

                "% Change": pct

            })

        self.tables["QoQ Comparison"] = pd.DataFrame(comparison)

    def build_optimization_insights(self):

        comparison = self.tables["QoQ Comparison"]

        insights = []

        for _, row in comparison.iterrows():

            metric = row["Metric"]

            pct = row["% Change"]

            if pct > 10:

                status = "Strong Growth"

                recommendation = "Scale current strategy."

            elif pct > 0:

                status = "Stable Growth"

                recommendation = "Continue optimization."

            elif pct == 0:

                status = "No Change"

                recommendation = "Monitor performance."

            else:

                status = "Decline"

                recommendation = "Investigate and optimize."

            insights.append({

                "Metric": metric,

                "Q1": row["Q1"],

                "Q2": row["Q2"],

                "% Change": pct,

                "Status": status,

                "Recommendation": recommendation

            })

        self.tables["Optimization Insights"] = pd.DataFrame(insights)

    def build_trending_account_summary(self):

        df = self.trending_accounts

        rows = []

        rows.append({
            "Metric": "Targeted Accounts",
            "Value": len(df)
        })

        rows.append({
            "Metric": "Trending Accounts",
            "Value": (df["Trending"] == "Yes").sum()
        })

        rows.append({
            "Metric": "Reached Accounts",
            "Value": (df["Reached"] == "Yes").sum()
        })

        rows.append({
            "Metric": "Engaged Accounts",
            "Value": (df["Engaged"] == "Yes").sum()
        })

        self.tables["Trending Account Summary"] = pd.DataFrame(rows)

    def build_buying_stage_table(self):

        df = self.trending_accounts

        table = (
            df.groupby("Predictive Buying Stage")
            .size()
            .reset_index(name="Accounts")
            .sort_values(
                "Accounts",
                ascending=False
            )
        )

        self.tables["Buying Stage Distribution"] = table

    def build_funnel_table(self):

        df = self.trending_accounts

        targeted = len(df)

        trending = (df["Trending"] == "Yes").sum()

        reached = (df["Reached"] == "Yes").sum()

        engaged = (df["Engaged"] == "Yes").sum()

        funnel = pd.DataFrame({

            "Stage": [

                "Targeted",

                "Trending",

                "Reached",

                "Engaged"

            ],

            "Accounts": [

                targeted,

                trending,

                reached,

                engaged

            ]

        })

        self.tables["Account Funnel"] = funnel

    def build_conversion_table(self):

        funnel = self.tables["Account Funnel"]

        targeted = funnel.iloc[0]["Accounts"]

        trending = funnel.iloc[1]["Accounts"]

        reached = funnel.iloc[2]["Accounts"]

        engaged = funnel.iloc[3]["Accounts"]

        rows = []

        rows.append({

            "Conversion":

            "Trending / Targeted",

            "Rate":

            round(trending / targeted * 100, 2)

            if targeted else 0

        })

        rows.append({

            "Conversion":

            "Reached / Trending",

            "Rate":

            round(reached / trending * 100, 2)

            if trending else 0

        })

        rows.append({

            "Conversion":

            "Engaged / Reached",

            "Rate":

            round(engaged / reached * 100, 2)

            if reached else 0

        })

        self.tables["Account Conversion"] = pd.DataFrame(rows)

    def build_asset_summary(self):

        df = self.asset_delivery.copy()

        summary = pd.DataFrame({

            "Metric": [

                "Total Assets",

                "Total Accounts Reached",

                "Total Leads Generated"

            ],

            "Value": [

                len(df),

                df["# Accounts"].sum(),

                df["Leads"].sum()

            ]

        })

        self.tables["Asset Delivery Summary"] = summary

    def build_asset_ranking(self):

        df = self.asset_delivery.copy()

        ranking = df.sort_values(

            "Leads",

            ascending=False

        ).reset_index(drop=True)

        self.tables["Asset Ranking"] = ranking[
            [

                "Asset Name",

                "# Accounts",

                "Leads"

            ]

        ]

    def build_asset_contribution(self):

        df = self.asset_delivery.copy()

        total = df["Leads"].sum()

        contribution = df.copy()

        contribution["Contribution %"] = round(

            contribution["Leads"] / total * 100,

            2

        )

        contribution = contribution.sort_values(

            "Contribution %",

            ascending=False

        )

        self.tables["Asset Contribution"] = contribution[
            [

                "Asset Name",

                "Contribution %"

            ]

        ]

    def build_asset_efficiency(self):

        df = self.asset_delivery.copy()

        efficiency = df.copy()

        efficiency["Leads per Account"] = round(

            efficiency["Leads"] /

            efficiency["# Accounts"],

            2

        )

        efficiency = efficiency.sort_values(

            "Leads per Account",

            ascending=False

        )

        self.tables["Asset Efficiency"] = efficiency[
            [

                "Asset Name",

                "Leads per Account"

            ]

        ]

    def build_campaign_snapshot(self):

        rows = []

        leads = self.leads

        q1 = self.periods["Q1"]
        q2 = self.periods["Q2"]

        rows.append({
            "Metric": "Campaign Start",
            "Overall": leads["Date"].min().strftime("%d-%b-%Y"),
            "Q1": "",
            "Q2": ""
        })

        rows.append({
            "Metric": "Campaign End",
            "Overall": leads["Date"].max().strftime("%d-%b-%Y"),
            "Q1": "",
            "Q2": ""
        })

        rows.append({
            "Metric": "Assets Used",
            "Overall": leads["Asset Name"].nunique(),
            "Q1": q1["Asset Name"].nunique(),
            "Q2": q2["Asset Name"].nunique()
        })

        rows.append({
            "Metric": "Job Titles",
            "Overall": leads["Job Title"].nunique(),
            "Q1": q1["Job Title"].nunique(),
            "Q2": q2["Job Title"].nunique()
        })

        rows.append({
            "Metric": "Countries",
            "Overall": leads["Country"].nunique(),
            "Q1": q1["Country"].nunique(),
            "Q2": q2["Country"].nunique()
        })

        self.tables["Campaign Snapshot"] = pd.DataFrame(rows)