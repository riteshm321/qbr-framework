import json
from pathlib import Path

from config import CLIENT_NAME, PROGRAM_NAME, CAMPAIGN_TYPE, REPORT_MODE
from constants import CAMPAIGN, MONTHLY, QUARTERLY, CUSTOM


# How each report mode should be described to the AI. The raw REPORT_MODE
# values ("Campaign", "Monthly") don't say what is being compared with what.
ANALYSIS_TYPE_LABELS = {
    CAMPAIGN: "Full Campaign (one period covering the entire campaign)",
    MONTHLY: "Month over Month (one period per calendar month with data)",
    QUARTERLY: "Quarter over Quarter (one period per calendar quarter with data)",
    CUSTOM: "Custom Date Range (a single user-selected window)",
}


class AIExporter:

    def __init__(self, analysis):

        self.analysis = analysis

        self.output = Path("output")

        self.output.mkdir(exist_ok=True)

    # -----------------------------------------------------

    def reporting_period(self):

        """
        The periods this run actually covers, named as they appear on the
        slides.

        Without this the AI had no way to know what it was looking at: the
        tables below carry generic "Q1"/"Q2" column names from the
        first-vs-last comparison logic, so a four-quarter Quarter-over-Quarter
        run read as a two-quarter campaign and the narrative said "covering
        Q1 and Q2 -- the initial two quarters".

        Built from comparison_slots rather than slots because slots is capped
        at MAX_MONTHLY_DETAIL_SLIDES and would silently omit later periods
        (a 7-month campaign would describe only 6 months).
        """

        meta = getattr(self.analysis, "period_meta", {}) or {}

        slots = meta.get("comparison_slots") or meta.get("slots") or []

        breakdown = []

        for slot in slots:

            entry = {
                "Period": slot.get("label", ""),
                "Start": slot.get("start", ""),
                "End": slot.get("end", ""),
            }

            entry.update(slot.get("metrics", {}))

            breakdown.append(entry)

        # The deck gives an individual performance slide to each entry in
        # slots, which is not always the same list as the breakdown above:
        # Full Campaign has one slide covering a multi-month breakdown, and a
        # Monthly run past MAX_MONTHLY_DETAIL_SLIDES has fewer slides than
        # months. The AI needs one commentary per slide, so name them.
        detail_labels = [
            slot.get("label", "")
            for slot in (meta.get("slots") or [])
        ]

        return {

            "Analysis Type": ANALYSIS_TYPE_LABELS.get(REPORT_MODE, REPORT_MODE),

            "Overall Range": meta.get("overall_range", ""),

            "Periods Analyzed": len(breakdown),

            "Period Breakdown": breakdown,

            "Periods Needing Individual Commentary": detail_labels,

        }

    # -----------------------------------------------------

    def _period_labelled(self, table_name):

        """
        A comparison table with its generic "Q1"/"Q2" columns renamed to the
        real period labels, so the AI quotes the period names that appear on
        the slides instead of inventing quarter numbers.

        For Full Campaign both slots are the same period, which makes the
        change columns meaningless zeroes -- those are dropped rather than
        handed over for the AI to narrate as "flat growth".
        """

        table = self.analysis.tables.get(table_name)

        if table is None:
            return []

        meta = getattr(self.analysis, "period_meta", {}) or {}

        label_a = (meta.get("Q1") or {}).get("label", "Q1")
        label_b = (meta.get("Q2") or {}).get("label", "Q2")

        table = table.copy()

        if label_a == label_b:

            drop = [
                column for column in ("Q2", "Change", "% Change")
                if column in table.columns
            ]

            table = table.drop(columns=drop)

        if "Q1" in table.columns:
            table = table.rename(columns={"Q1": label_a})

        if "Q2" in table.columns:
            table = table.rename(columns={"Q2": label_b})

        return table.to_dict(orient="records")

    def _records(self, table_name):

        """One analyzer table as records, or [] when it isn't present."""

        table = self.analysis.tables.get(table_name)

        if table is None:
            return []

        return table.to_dict(orient="records")

    def build_package(self):

        package = {

            "Metadata": {

                "Client": CLIENT_NAME,

                "Program": PROGRAM_NAME,

                "Campaign Type": CAMPAIGN_TYPE,

                "Report Mode": REPORT_MODE

                # Deliberately no generation timestamp here. ai/content_cache.py
                # fingerprints this file to decide whether the AI narrative can
                # be reused, so a value that changes every run (as a timestamp
                # does) would make the cache never hit and silently burn API
                # quota on every single run. Each cache entry records its own
                # generated_at instead.

            },

            # What this report actually covers. Must come before the tables
            # below, which describe metrics without ever naming the periods
            # they belong to.
            "Reporting Period": self.reporting_period(),

            "Executive Summary": self._period_labelled("Executive"),

            "Campaign Snapshot":

                self.analysis.tables["Campaign Snapshot"].to_dict(
                    orient="records"
                ),

            # The former "Q1 Summary" / "Q2 Summary" keys are gone. They held
            # the first and last period under hardcoded quarter names, which
            # is what led the AI to describe any multi-period run as a
            # two-quarter campaign. Every period's metrics now live in
            # Reporting Period -> Period Breakdown, correctly labelled.

            "Asset Performance":

                self.analysis.tables["Asset Performance"].to_dict(
                    orient="records"
                ),

            "Engagement Summary":

                self.analysis.tables["Engagement Summary"].to_dict(
                    orient="records"
                ),

            # Data behind charts the AI is asked to comment on. Without these
            # it was writing the funnel commentary from "Engagement Summary"
            # (impressions and clicks) because the funnel's own
            # Targeted/Reached/Engaged figures were never in the payload --
            # confidently describing the wrong chart.
            "Account Funnel": self._records("Account Funnel"),

            "Account Conversion": self._records("Account Conversion"),

            "Trend Projection": self._records("Trend Projection"),

            "Buying Stage Distribution": self._records("Buying Stage Distribution"),

            "Asset Contribution": self._records("Asset Contribution"),

            "Value Add Metrics": self._records("Value Add Metrics"),

            "Top Engaged Accounts":

                self.analysis.tables["Top Engaged Accounts"].to_dict(
                    orient="records"
                ),

            "Trending Topics":

                self.analysis.tables["Trending Topics"].to_dict(
                    orient="records"
                ),

            "Topic Categories":

                self.analysis.tables["Topic Categories"].to_dict(
                    orient="records"
                ),

            "Top Intent Accounts":

                self.analysis.tables["Top Intent Companies"].to_dict(
                    orient="records"
                ),

            "Period Comparison": self._period_labelled("QoQ Comparison"),

            "Optimization Insights": self._period_labelled("Optimization Insights"),

            # First vs last period per metric, with the Status wording the
            # deck's own status pills display. The "Optimization Insights"
            # table above is built from the fixed 2-slot comparison, which for
            # Full Campaign compares the period against itself and so reports
            # zero change for everything -- the AI read that and wrote
            # "metrics held flat" onto a slide whose pills said "Decline" and
            # "Strong Growth". This is the table those pills come from.
            "Metric Status": self._records("Comparison Overview")

        }

        return package

    # -----------------------------------------------------

    def export_json(self):

        package = self.build_package()

        with open(

            self.output / "qbr_package.json",

            "w",

            encoding="utf-8"

        ) as f:

            json.dump(

                package,

                f,

                indent=4,

                default=str

            )

    # -----------------------------------------------------

    def export_prompt(self):

        prompt = """
You are a Senior B2B Marketing Consultant.

The attached JSON file contains the complete campaign analytics for a Madison Logic Quarterly Business Review.

Using ONLY the information provided inside the JSON, generate the following sections.

1. Executive Summary

2. Campaign Snapshot

3. Q1 Highlights

4. Q2 Highlights

5. Q1 vs Q2 Comparative Analysis

6. Asset Performance Analysis

7. Account Engagement Analysis

8. Trending Topics Analysis

9. Optimization Highlights

10. Key Learnings

11. Recommendations

12. Executive Conclusion

Important Rules

• Never invent metrics.

• Never change numbers.

• Keep an executive consulting tone.

• Maximum 150 words per section.

• Use headings.

• Use bullet points where appropriate.

• Mention positive trends as well as optimization opportunities.

• Make the language suitable for a client-facing PowerPoint.
"""

        with open(

            self.output / "ai_prompt.txt",

            "w",

            encoding="utf-8"

        ) as f:

            f.write(prompt)

    # -----------------------------------------------------

    def export(self):

        self.export_json()

        self.export_prompt()