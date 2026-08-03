"""
Universal Presentation Data Model

Every module writes here.
Only ppt_engine.py reads from here.
"""
import math
import textwrap
import pandas as pd

class PresentationData:

    def __init__(self):

        self.metadata = {}

        self.campaign = {}

        self.kpis = {}

        self.charts = {}

        self.tables = {}

        self.tables = {}

        self.results = {}

        self.ai = {

            "executive_summary": "",

            "campaign_overview": "",

            "q1_analysis": "",

            "q2_analysis": "",

            # These three are read back as dicts (.get("summary"),
            # .get("bullets"/"actions")) in to_ppt_dictionary() -- {}
            # rather than "" so that default still supports .get() when
            # the AI call never ran (e.g. a Gemini failure/rate limit),
            # instead of crashing on a plain string with no .get().
            "comparison": {},

            "recommendations": {},

            "optimization": {},

            "value_add": "",

            "executive_conclusion": "",

            "speaker_notes": ""

        }

    def to_dict(self):

        return {
            "metadata": self.metadata,
            "campaign": self.campaign,
            "kpis": self.kpis,
            "charts": self.charts,
            "tables": self.tables,
            "ai": self.ai,
        }
    
    # ---------------------------------------------------------
    # Convert PresentationData to PowerPoint Object Dictionary
    # ---------------------------------------------------------

    def find_row(df, column, value):

        if df is None:
            return None

        rows = df[df[column] == value]

        if rows.empty:
            return None

        return rows.iloc[0]
    
    def wrap_chart_labels(self, series, width=20):
        """
        Automatically wraps long category labels
        for PowerPoint charts.
        """

        return series.apply(
            lambda x: "\n".join(
                textwrap.wrap(str(x), width=width)
            )
        )

    @staticmethod
    def format_count(value):
        """Thousands-separated display text for a KPI card count (e.g.
        1403 -> "1,403"). Only touches the text shown on the slide --
        callers needing the raw number for further math should keep
        reading it from self.tables/period_meta directly."""

        try:
            return f"{value:,}"
        except (TypeError, ValueError):
            return value

    @staticmethod
    def format_percent(value):
        """Display text for a % Change figure (e.g. 12.5 -> "12.5%"),
        so it reads as a percentage instead of a bare number that looks
        like a plain count next to it."""

        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""

        try:
            return f"{value:g}%"
        except (TypeError, ValueError):
            return value

    @staticmethod
    def pluralize_country(count):
        """"Country" for exactly 1, "Countries" for 0 or any other
        count -- the card's label text, not the number itself."""

        return "Country" if count == 1 else "Countries"

    def to_ppt_dictionary(self):

        ppt = {}

        # -------------------------------------------------
        # HELPER
        # -------------------------------------------------

        def find_row(df, column, value):

            if df is None:
                return None

            rows = df[df[column] == value]

            if rows.empty:
                return None

            return rows.iloc[0]
        
        # -------------------------------------------------
        # TABLE REFERENCES
        # -------------------------------------------------

        executive = self.tables.get("Executive")

        snapshot = self.tables.get("Campaign Snapshot")

        comparison_table = self.tables.get("QoQ Comparison")

        optimization_table = self.tables.get("Optimization Insights")

        # -------------------------------------------------
        # COVER PAGE
        # -------------------------------------------------

        ppt["TITLE_Report"] = self.metadata.get(
            "report_title",
            "Quarterly Business Review"
        )

        ppt["PERIOD_Report"] = self.metadata.get(
            "report_period",
            ""
        )

        # -------------------------------------------------
        # EXECUTIVE SUMMARY
        # -------------------------------------------------

        ppt["TITLE_ExecutiveSummary"] = "Executive Summary"

        ppt["AI_ExecutiveSummary"] = self.ai.get(
            "executive_summary",
            ""
        )

        # -------------------------------------------------
        # SELECTED PERIOD(S)
        #
        # Set once by the analyzer (see LeadGenAnalyzer._build_period_meta)
        # from whatever analysis period was picked when running the tool.
        # -------------------------------------------------

        periods = self.campaign.get("periods", {})

        comparison_slots = periods.get("comparison_slots", [])

        ppt["META_CampaignDescription"] = periods.get(
            "campaign_description",
            ""
        )

        # Campaign Snapshot (slide 4) always describes the whole
        # campaign, independent of whatever period(s) are being
        # compared elsewhere in the deck -- always one merged box
        # showing the overall date range, never split into two.
        ppt["PERIOD_Q1"] = periods.get("overall_range", "")
        ppt["PERIOD_Q2"] = periods.get("overall_range", "")

        ppt["SECTION_Q1"] = periods.get("section_title", "")

        # Agenda: fixed items around the period-specific performance
        # section(s), which vary in number and wording with the mode.

        ppt["Text Placeholder 1"] = (
            ["Executive Summary", "Campaign Snapshot"]
            + periods.get("agenda_items", ["Campaign Performance"])
            + [
                periods.get("comparison_label", "Comparative Analysis"),
                "Content, Audience & Intent Insights",
                "Key Learnings & Optimization Highlights",
                "Momentum & 2026 Outlook",
                "Value-Add Lead Impact Summary",
            ]
        )

        # -------------------------------------------------
        # PER-PERIOD DETAIL SLIDES (divider + performance detail,
        # one pair per slot in LeadGenAnalyzer.period_meta["slots"]).
        #
        # The first two slots reuse the template's existing Q1/Q2
        # objects; slide_ops.py clones and renames a Q1/Q2-shaped pair
        # for every slot beyond that (P3, P4, ...), so this loop maps
        # onto whichever slides actually exist for the selected mode.
        # -------------------------------------------------

        for slot in periods.get("slots", []):

            token = slot["slot"]
            metrics = slot["metrics"]
            date_range = f"{slot['start']} - {slot['end']}"

            ppt[f"TITLE_{token}Performance"] = f"{slot['label']} Performance"

            ppt[f"SECTION_{token}"] = f"{slot['label']} Performance"

            # PERIOD_Q1/PERIOD_Q2 are ambiguous names shared with slide 4
            # (already set above, occurrence 0) -- the detail-slide copy
            # is occurrence 1. P3+ names are unique, occurrence 0.
            period_key = f"PERIOD_{token}" if token not in ("Q1", "Q2") else f"PERIOD_{token}_Detail"

            ppt[period_key] = {
                "object": f"PERIOD_{token}",
                "occurrence": 1 if token in ("Q1", "Q2") else 0,
                "text": date_range,
            }

            ppt[f"CARD_{token}_TotalLeads"] = self.format_count(metrics["Total Leads"])
            ppt[f"CARD_{token}_Accounts"] = self.format_count(metrics["Unique Accounts"])
            ppt[f"CARD_{token}_Assets"] = self.format_count(metrics["Assets Used"])
            ppt[f"CARD_{token}_JobTitles"] = self.format_count(metrics["Job Titles"])
            ppt[f"CARD_{token}_Country"] = self.format_count(metrics["Countries"])

            ppt[f"CARD_{token}_CountryLabel"] = {
                "object": f"CARD_{token}_Country",
                "group_child_index": 2,
                "text": self.pluralize_country(metrics["Countries"]),
            }

            ppt[f"AI_{token}_TopAsset"] = {
                "paragraph_index": 2,
                "text": metrics["Top Asset"],
            }

            ppt[f"AI_{token}_TrendingTopic"] = {
                "paragraph_index": 2,
                "text": metrics["Top Topic"],
            }

        # The comparison section (divider + chart/table slide) always
        # exists, however many detail slides precede it, and its wording
        # adapts to the mode via the same comparison_label used in the
        # agenda above.

        ppt["SECTION_Comparison"] = periods.get("comparison_label", "Comparative Analysis")

        ppt["TITLE_Q1Q2Comparison"] = periods.get("comparison_label", "Comparative Analysis")

        ppt["TITLE_QoQMetrics"] = periods.get(
            "detail_metrics_title", "Detailed QoQ Metrics & Optimization Status"
        )

        # -------------------------------------------------
        # CAMPAIGN SNAPSHOT
        # -------------------------------------------------

        ppt["AI_CampaignSnapshot"] = self.ai.get(
            "campaign_overview",
            ""
        )

        # -------------------------------------------------
        # Q1 / Q2 INSIGHTS
        # -------------------------------------------------

        ppt["AI_Q1_Insight"] = self.ai.get(
            "q1_analysis",
            ""
        )

        ppt["AI_Q2_Insight"] = self.ai.get(
            "q2_analysis",
            ""
        )

        # -------------------------------------------------
        # OPTIMIZATION
        # -------------------------------------------------

        optimization = self.ai.get(
            "optimization",
            {}
        )

        ppt["AI_OptimizationHeading"] = "KEY OPTIMIZATION ACTIONS"

        summary = optimization.get(
            "summary",
            ""
        )

        bullets = optimization.get(
            "bullets",
            []
        )

        if bullets:

            summary += "\n\n"

            summary += "\n".join(
                f"• {bullet}"
                for bullet in bullets
            )

        ppt["AI_OptimizationSummary"] = summary

        # -------------------------------------------------
        # COMPARISON
        # -------------------------------------------------

        comparison = self.ai.get("comparison", {})

        ppt["AI_ComparisonSummary"] = comparison.get(
            "summary",
            ""
        )

        bullets = comparison.get(
            "bullets",
            []
        )

        ppt["AI_ComparisonHeadline"] = (
            bullets[0] if len(bullets) > 0 else ""
        )

        ppt["AI_ComparisonInsight1"] = (
            bullets[1] if len(bullets) > 1 else ""
        )

        ppt["AI_ComparisonInsight2"] = (
            bullets[2] if len(bullets) > 2 else ""
        )

        # -------------------------------------------------
        # RECOMMENDATIONS
        # -------------------------------------------------

        recommendations = self.ai.get(
            "recommendations",
            {}
        )

        ppt["AI_RecommendationsSummary"] = recommendations.get(
            "summary",
            ""
        )

        actions = recommendations.get(
            "actions",
            []
        )

        for i in range(5):

            ppt[f"AI_Recommendation{i+1}"] = (
                actions[i]
                if i < len(actions)
                else ""
            )

        # -------------------------------------------------
        # VALUE ADD
        # -------------------------------------------------

        ppt["AI_ValueAddSummary"] = self.ai.get(
            "value_add",
            ""
        )

        value_add_metrics = self.tables.get("Value Add Metrics")

        if value_add_metrics is not None:

            for i, row in value_add_metrics.iterrows():

                object_name = f"KPI_ValueMetric{i + 1}"

                ppt[f"{object_name}_Value"] = {
                    "object": object_name,
                    "paragraph_index": 0,
                    "text": row["Value"],
                }

                ppt[f"{object_name}_Caption"] = {
                    "object": object_name,
                    "paragraph_index": 1,
                    "text": row["Caption"],
                }

        # -------------------------------------------------
        # KPI CARDS (Overall only -- per-slot Q1/Q2/P3... cards are
        # set above, straight from LeadGenAnalyzer.period_meta)
        # -------------------------------------------------

        if executive is not None:

            assets = find_row(executive, "KPI", "Assets Used")
            topics = find_row(executive, "KPI", "Trending Topics")

            if assets is not None:
                # Keep temporarily until executive slide audit
                ppt["CARD_TotalAssets"] = int(assets["Overall"])

            if topics is not None:
                # Keep temporarily until executive slide audit
                ppt["CARD_TrendingTopics"] = int(topics["Overall"])

        if snapshot is not None:

            assets = find_row(snapshot, "Metric", "Assets Used")
            jobs = find_row(snapshot, "Metric", "Job Titles")
            countries = find_row(snapshot, "Metric", "Countries")
            start = find_row(snapshot, "Metric", "Campaign Start")
            end = find_row(snapshot, "Metric", "Campaign End")
            weeks = None

            if start is not None and end is not None:

                from datetime import datetime

                start_date = datetime.strptime(
                    str(start["Overall"]),
                    "%d-%b-%Y"
                )

                end_date = datetime.strptime(
                    str(end["Overall"]),
                    "%d-%b-%Y"
                )

                weeks = round(
                    (end_date - start_date).days / 7
                )

            if assets is not None:
                ppt["CARD_AssetsUsed"] = self.format_count(assets["Overall"])

            if jobs is not None:
                ppt["CARD_JobTitles"] = self.format_count(jobs["Overall"])

            if weeks is not None:
                ppt["CARD_WeeksInMarket"] = self.format_count(weeks)

            if countries is not None:

                ppt["CARD_Country"] = self.format_count(countries["Overall"])

                ppt["CARD_CountryLabel"] = {
                    "object": "CARD_Country",
                    "group_child_index": 2,
                    "text": self.pluralize_country(countries["Overall"]),
                }

            if start is not None:
                ppt["Campaign_Start"] = start["Overall"]

            if end is not None:
                ppt["Campaign_End"] = end["Overall"]

        if comparison_table is not None:

            leads = find_row(
                comparison_table,
                "Metric",
                "Total Leads"
            )

            accounts = find_row(
                comparison_table,
                "Metric",
                "Unique Accounts"
            )

            jobs = find_row(
                comparison_table,
                "Metric",
                "Job Titles"
            )

            if leads is not None:

                ppt["KPI_LeadGrowth"] = leads["% Change"]

            if accounts is not None:

                ppt["KPI_AccountGrowth"] = accounts["% Change"]

            if jobs is not None:

                ppt["KPI_JobTitleGrowth"] = jobs["% Change"]

        # The fixed 2-slot Optimization Insights table only means
        # "before vs after" when there genuinely are 2 comparable slots.
        # Whenever the comparison spans 3+ (e.g. Full Campaign grouped
        # into several months), use the first-vs-last Comparison
        # Overview instead so Status isn't stuck at "No Change" just
        # because _period_columns() had to duplicate a single slot.
        if len(comparison_slots) > 2:
            optimization_table = self.tables.get("Comparison Overview")

        if optimization_table is not None and not optimization_table.empty:

            metrics = {

                "Total Leads": "StatusPill_TotalLeads",

                "Unique Accounts": "StatusPill_UniqueAccounts",

                "Assets Used": "StatusPill_AssetsUsed",

                "Job Titles": "StatusPill_JobTitles",

                "Countries": "StatusPill_Countries"

            }

            for metric, object_name in metrics.items():

                row = find_row(
                    optimization_table,
                    "Metric",
                    metric
                )

                if row is not None:

                    # Each StatusPill_* name appears twice in the deck --
                    # once on the QoQ Metrics detail slide, once more
                    # (nested two groups deep) on the Optimization
                    # Highlights slide -- both showing the same metric's
                    # status. Only occurrence 0 was ever being set, so
                    # the second copy stayed stuck at the template's
                    # static example value. Set both explicitly.
                    ppt[object_name] = {
                        "object": object_name,
                        "occurrence": 0,
                        "text": row["Status"],
                    }

                    ppt[f"{object_name}_Highlights"] = {
                        "object": object_name,
                        "occurrence": 1,
                        "text": row["Status"],
                    }

        # -------------------------------------------------
        # POWERPOINT TABLES
        # -------------------------------------------------

        top_engaged_accounts = self.tables.get("Top Engaged Accounts")

        if top_engaged_accounts is not None:
            top_engaged_accounts = top_engaged_accounts[
                ["Account Name", "Leads"]
            ].copy()

        ppt["Table_TopEngagedAccounts"] = top_engaged_accounts

        ppt["Table_TopIntentCompanies"] = self.tables.get(
            "Top Intent Companies"
        )

        # Reuse `optimization_table` as already resolved above (which
        # switches to the first-vs-last Comparison Overview whenever
        # comparison_slots > 2) so the Recommendation text here always
        # matches whatever trend the StatusPill_* badges are showing --
        # not the fixed 2-slot table's always-zero-change verdict.
        # The template's table only has Metric/Recommendation columns
        # (Status renders as separate pill shapes, not a table column),
        # so keep only those two -- the source table carries extra
        # columns (period values, % Change, Status) that would otherwise
        # shift into the wrong cells.
        optimization_highlights = optimization_table

        if optimization_highlights is not None:
            optimization_highlights = optimization_highlights[
                ["Metric", "Recommendation"]
            ].copy()

        ppt["Table_OptimizationHighlights"] = optimization_highlights

        # QoQ table + comparison chart: the 2-period case (Quarterly,
        # Custom, and Full Campaign/Monthly whenever comparison_slots
        # still has only 2 entries) reuses the existing Change/% Change
        # table as before. 3+ comparison_slots (Month over Month, or
        # Full Campaign spanning 3+ months) means a single "Change"
        # column can't show a before/after pair per period -- show
        # Metric + one column per slot, plus an overall % Change
        # (first slot vs last, the same figure already driving the
        # Status pills below) rather than dropping it.

        if len(comparison_slots) > 2:

            metric_names = [
                "Total Leads", "Unique Accounts",
                "Assets Used", "Job Titles", "Countries"
            ]

            overall_change = self.tables.get("Comparison Overview")

            rows = []

            for metric in metric_names:

                row = {"Metric": metric}

                for slot in comparison_slots:
                    row[slot["label"]] = slot["metrics"][metric]

                if overall_change is not None and not overall_change.empty:

                    change_row = overall_change[overall_change["Metric"] == metric]

                    if not change_row.empty:
                        row["% Change"] = change_row.iloc[0]["% Change"]

                rows.append(row)

            comparison_df = pd.DataFrame(rows)

            ppt["CHART_Q1Q2Comparison"] = comparison_df[
                comparison_df["Metric"].isin(["Total Leads", "Unique Accounts"])
            ][["Metric"] + [slot["label"] for slot in comparison_slots]]

            if "% Change" in comparison_df.columns:
                comparison_df = comparison_df.copy()
                comparison_df["% Change"] = comparison_df["% Change"].apply(
                    self.format_percent
                )

            ppt["Table_QoQMetrics"] = comparison_df

        else:

            qoq_table = self.tables.get("QoQ Comparison")

            if qoq_table is not None and "% Change" in qoq_table.columns:
                qoq_table = qoq_table.copy()
                qoq_table["% Change"] = qoq_table["% Change"].apply(
                    self.format_percent
                )

            ppt["Table_QoQMetrics"] = qoq_table

            qoq_chart = self.tables["QoQ Comparison"]

            qoq_chart = qoq_chart[
                qoq_chart["Metric"].isin([
                    "Total Leads",
                    "Unique Accounts"
                ])
            ][["Metric", "Q1", "Q2"]]

            # _period_columns()'s "Q1"/"Q2" column names are generic
            # placeholders -- fine as-is for a real 2-quarter/2-month
            # comparison, but wrong for Custom mode's single user-picked
            # range (there's no "quarter" to speak of). Custom is the
            # only mode where the per-period detail collapses to one
            # slot while the comparison still has two -- that structural
            # signature (rather than checking the mode directly) is what
            # tells us to relabel the chart's legend with the real
            # "Period 1"/"Period 2" comparison_slots labels instead.
            slots = periods.get("slots", [])

            if len(slots) == 1 and len(comparison_slots) == 2:
                qoq_chart = qoq_chart.rename(columns={
                    "Q1": comparison_slots[0]["label"],
                    "Q2": comparison_slots[1]["label"],
                })

            ppt["CHART_Q1Q2Comparison"] = qoq_chart

        # -------------------------------------------------
        # TREND ANALYSIS CHART
        #
        # Built entirely by LeadGenAnalyzer._build_trend_projection() --
        # which real periods appear (individual months, grouped
        # 3-month "quarters", or the 2 selected periods) and how far
        # the forecast extends both vary by mode. The "Is Forecast"
        # column tells ppt_engine.replace_chart() which trailing points
        # to render dashed; it isn't itself a chart series.
        # -------------------------------------------------

        ppt["Chart_TrendAnalysis"] = self.tables["Trend Projection"]

        trend_projection = self.tables["Trend Projection"]

        forecast_labels = trend_projection.loc[
            trend_projection["Is Forecast"], "Period"
        ].tolist()

        if forecast_labels:

            ppt["AI_TrendAnalysisChartNote"] = (
                f"*{', '.join(forecast_labels)} figures are an illustrative, "
                "directional projection based on the observed trend -- "
                "not a guarantee of future performance."
            )
        
        # -------------------------------------------------
        # CONTENT PERFORMANCE CHART
        # -------------------------------------------------

        asset_chart = self.tables["Asset Ranking"].copy()

        # Keep only Asset Name and Leads
        asset_chart = asset_chart[
            ["Asset Name", "Leads"]
        ]

        asset_chart["Asset Name"] = self.wrap_chart_labels(
            asset_chart["Asset Name"],
            width=18
        )

        # Highest performer first, top 10 only -- a campaign with many
        # assets would otherwise plot all of them and overflow the chart
        # regardless of analysis mode.
        asset_chart = asset_chart.sort_values(
            by="Leads",
            ascending=False
        ).head(10)

        ppt["Chart_ContentPerformance"] = asset_chart

        # -------------------------------------------------
        # TRENDING TOPICS CHART
        # -------------------------------------------------

        topic_chart = self.tables["Trending Topics"].copy()

        topic_chart = topic_chart[
            ["Topic", "Mentions"]
        ]

        # Keep Top 10 only
        topic_chart = topic_chart.nlargest(
            10,
            "Mentions"
        )

        topic_chart["Topic"] = self.wrap_chart_labels(
            topic_chart["Topic"],
            width=18
        )

        ppt["Chart_TrendingTopics"] = topic_chart

        # -------------------------------------------------
        # TOPIC DISTRIBUTION
        # -------------------------------------------------

        topic_distribution = self.tables["Topic Categories"].copy()

        # Keep Top 8 only
        topic_distribution = topic_distribution.nlargest(8, "Mentions")

        ppt["Chart_TopicDistribution"] = topic_distribution

        # -------------------------------------------------
        # ENGAGEMENT FUNNEL
        # -------------------------------------------------

        funnel_chart = self.tables["Account Funnel"].copy()

        ppt["Chart_EngagementFunnel"] = funnel_chart

        # -------------------------------------------------
        # BUYING STAGE DISTRIBUTION
        # -------------------------------------------------

        buying_stage_chart = self.tables["Buying Stage Distribution"].copy()

        ppt["Chart_BuyingStage"] = buying_stage_chart

        # KPI_BuyingStage1 sits next to the "No Active Signals" caption,
        # KPI_BuyingStage2 next to the "Consideration + Decision" caption
        # (confirmed by on-slide position, not by the shape names' own
        # 1/2 suffixes, which don't match up with the captions).
        stage_counts = buying_stage_chart.set_index(
            "Predictive Buying Stage"
        )["Accounts"]

        ppt["KPI_BuyingStage1"] = self.format_count(
            int(stage_counts.get("No Active Signals", 0))
        )

        ppt["KPI_BuyingStage2"] = self.format_count(
            int(stage_counts.get("Decision", 0) + stage_counts.get("Consideration", 0))
        )

        return ppt