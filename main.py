import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from engine.campaign_manager import CampaignManager

import config
from config import *

from core.loader import *

from core.cleaner import *

from core.validator import *

from core.date_engine import *

from core.detector import detect_dataset

import os
import pandas as pd

validate_files(INPUT_DIR)

datasets = {}

for file in INPUT_DIR.iterdir():

    if file.suffix.lower()==".csv":

        df=load_csv(file)

    elif file.suffix.lower()==".xlsx":

        df=load_excel(file)

    else:

        continue

    df=clean_dataframe(df)

    from core.date_engine import DateEngine

    engine = DateEngine(df)

    df = engine.add_date_columns()

    dataset_name = detect_dataset(df)

    print(f"{file.name}  --->  {dataset_name}")

    datasets[dataset_name] = df

# -------------------------------------------------------------
# Derive Client / Program from the reports themselves so the
# framework never relies on a hardcoded per-client config value.
# Falls back to whatever is already set in config.py if a report
# doesn't carry that metadata.
# -------------------------------------------------------------

for df in datasets.values():

    report_metadata = df.attrs.get("metadata", {})

    if report_metadata.get("Client"):
        config.CLIENT_NAME = report_metadata["Client"]

    if report_metadata.get("Program"):
        config.PROGRAM_NAME = report_metadata["Program"]

# -------------------------------------------------------------
# Decide which report the deck counts leads from. The Purchased
# Leads Report records what was actually delivered to the client;
# the Leads-by-day export includes refunded and non-delivered
# activity and counts materially more. Must run before the period
# resolver below, which detects the campaign window from the dates
# present in the datasets.
# -------------------------------------------------------------

from core.lead_source import resolve as resolve_lead_source

resolve_lead_source(datasets)

# -------------------------------------------------------------
# Ask the user which period(s) to analyze, then resolve that
# choice into concrete date ranges using the data that was
# actually loaded -- no reporting period is ever hardcoded.
# -------------------------------------------------------------

from core.period_resolver import resolve as resolve_period

manager = CampaignManager()
manager.select_analysis()

resolve_period(manager.analysis_type, datasets)

# -------------------------------------------------------------
# Keep an unfiltered copy of the Leads report before the window-scoping
# below -- Campaign Snapshot (slide 4) always shows the true full
# campaign, even in Quarterly/Custom modes where ANALYSIS_WINDOW is
# narrower (just the union of the 2 selected periods, not the whole
# campaign span).
# -------------------------------------------------------------

full_leads = datasets[LEAD_DETAIL].copy()

# -------------------------------------------------------------
# Scope every dataset to the selected window, so "Overall" KPIs
# reflect the period you chose, not just whatever date range
# happened to be in the input files.
# -------------------------------------------------------------

window_start = pd.to_datetime(config.ANALYSIS_WINDOW[0])
window_end = pd.to_datetime(config.ANALYSIS_WINDOW[1])

for name in list(datasets.keys()):

    df = datasets[name]

    if "Date" not in df.columns:
        continue

    mask = (df["Date"] >= window_start) & (df["Date"] <= window_end)

    datasets[name] = df.loc[mask].reset_index(drop=True)

print("\n")

for name, df in datasets.items():

    print("=" * 60)
    print(name)
    print(df.shape)

# -------------------------
# Run Analysis (ONLY ONCE)
# -------------------------

from campaign_types.leadgen import LeadGenAnalyzer

analysis = LeadGenAnalyzer(datasets, full_leads=full_leads).run()

print()

print("=" * 60)
print("SUMMARY")
print("=" * 60)

for k, v in analysis.results["executive"].items():

    print(k, ":", v)

print()

print("=" * 60)

print("EXECUTIVE TABLE")

print("=" * 60)

print(analysis.tables["Executive"])

print()

print("=" * 60)
print("CAMPAIGN SNAPSHOT")
print("=" * 60)

print(analysis.tables["Campaign Snapshot"])

print()

print("=" * 60)
print("Q1 SUMMARY")
print("=" * 60)

print(analysis.tables["Q1 Summary"])

print()

print("=" * 60)
print("Q2 SUMMARY")
print("=" * 60)

print(analysis.tables["Q2 Summary"])

print()

print("="*60)
print("TOP ASSETS")
print("="*60)

print(analysis.tables["Asset Performance"])

print()
print("="*60)
print("ENGAGEMENT SUMMARY")
print("="*60)
print(analysis.tables["Engagement Summary"])

print()
print("="*60)
print("TOP ENGAGED ACCOUNTS")
print("="*60)
print(analysis.tables["Top Engaged Accounts"])

print()
print("="*60)
print("TRENDING TOPICS")
print("="*60)
print(analysis.tables["Trending Topics"])

print()
print("="*60)
print("TOPIC CATEGORIES")
print("="*60)
print(analysis.tables["Topic Categories"])

print()
print("="*60)
print("TOP INTENT COMPANIES")
print("="*60)
print(analysis.tables["Top Intent Companies"])

print()

print("="*60)
print("Q1 vs Q2 COMPARISON")
print("="*60)

print(analysis.tables["QoQ Comparison"])

print()

print("="*60)
print("OPTIMIZATION INSIGHTS")
print("="*60)

print(analysis.tables["Optimization Insights"])

print()
print("="*60)
print("TRENDING ACCOUNT SUMMARY")
print("="*60)
print(analysis.tables["Trending Account Summary"])

print()
print("="*60)
print("BUYING STAGE DISTRIBUTION")
print("="*60)
print(analysis.tables["Buying Stage Distribution"])

print()
print("="*60)
print("ACCOUNT FUNNEL")
print("="*60)
print(analysis.tables["Account Funnel"])

print()
print("="*60)
print("ACCOUNT CONVERSION")
print("="*60)
print(analysis.tables["Account Conversion"])

print()
print("="*60)
print("ASSET DELIVERY SUMMARY")
print("="*60)
print(analysis.tables["Asset Delivery Summary"])

print()
print("="*60)
print("ASSET RANKING")
print("="*60)
print(analysis.tables["Asset Ranking"])

print()
print("="*60)
print("ASSET CONTRIBUTION")
print("="*60)
print(analysis.tables["Asset Contribution"])

print()
print("="*60)
print("ASSET EFFICIENCY")
print("="*60)
print(analysis.tables["Asset Efficiency"])

from datasets.lead_detail import LeadDetailDataset

lead_dataset = LeadDetailDataset(datasets[LEAD_DETAIL])

print("\n")
print("=" * 60)
print("LEAD DETAIL DATASET")
print("=" * 60)

print("Total Leads :", lead_dataset.total_leads)
print("Unique Accounts :", lead_dataset.unique_accounts)
print("Assets :", lead_dataset.unique_assets)
print("Job Titles :", lead_dataset.unique_job_titles)

from export.ai_export import AIExporter

AIExporter(analysis).export()
from workbook.excel_export import ExcelExporter

ExcelExporter(analysis).export()

from chart_engine.chart_engine import ChartEngine

ChartEngine(analysis).export()

print()

print("=" * 60)
print("AI EXPORT COMPLETED")
print("=" * 60)
print("Files generated inside OUTPUT folder.")
print("=" * 60)

from presentation.presentation_assets import PresentationAssets
PresentationAssets().generate()

from engine.story_builder import StoryBuilder

# period_meta identifies which period this run covers, so the AI narrative is
# cached per client + campaign + period rather than globally (see
# ai/content_cache.py).
story = StoryBuilder(period_meta=analysis.period_meta)
presentation = story.build()

presentation.tables = analysis.tables
presentation.results = analysis.results
presentation.campaign["periods"] = analysis.period_meta

chart_tables = [
    "Trending Account Summary",
    "Asset Ranking",
    "Trending Topics",
    "Topic Categories",
    "Account Funnel",
    "Buying Stage Distribution",
]

for name in chart_tables:

    print("\n==============================")
    print(name)
    print("==============================")

    df = presentation.tables.get(name)

    if df is None:
        print("NOT FOUND")
    else:
        print(df.head())

from presentation.ppt_engine import PowerPointEngine
presentation.metadata["report_title"] = f"{config.CLIENT_NAME} QBR"
presentation.metadata["report_period"] = analysis.period_meta["overall_label"]
ppt = PowerPointEngine()

# Whole slides that only exist to show one report's data -- remove them
# entirely when that report had no rows at all, rather than leaving the
# template's own static example content on screen looking like real data.
empty_data_slides = []

if analysis.trending_topics.empty:
    empty_data_slides.append("Chart_TrendingTopics")

ppt.create(
    presentation.to_ppt_dictionary(),
    # Campaign Snapshot (slide 4) always shows one merged box for the
    # whole campaign, regardless of analysis mode -- see PERIOD_Q1/Q2
    # in presentation_data.py.
    merge_period_boxes=True,
    periods=analysis.period_meta,
    empty_data_slides=empty_data_slides
)

from presentation.ppt_scanner import PPTScanner
scanner = PPTScanner("templates/LeadGen_QBR_Template.pptx")
scanner.scan()