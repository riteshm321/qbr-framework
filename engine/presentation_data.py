"""
Universal Presentation Data Model

Every module writes here.
Only ppt_engine.py reads from here.
"""
import math
import re
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

        # Defaults for every AI-backed field, used as-is when the AI call
        # never ran (all providers out of quota, no API key, etc). Sections
        # read back with .get() must default to {} rather than "" -- a plain
        # string has no .get() and would crash the whole fill pass.
        self.ai = {

            "executive_summary": "",

            "campaign_overview": "",

            # label -> commentary, one per period that has a detail slide
            "period_analysis": {},

            "comparison": {},

            "recommendations": {},

            "optimization": {},

            "value_add": "",

            "value_add_heading": "",

            "trend_analysis": {},

            "content_performance": {},

            "audience_interest": {},

            "engagement": {},

            "top_accounts": {},

            "optimization_highlights": {},

            "key_learnings": {},

            "partnership": {},

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

    @staticmethod
    def at_least(text, min_words, fallback):

        """
        AI text, or `fallback` when the model returned something too short to
        fill its box.

        The prompt states a length for every section, but a model that leans
        terse can answer a lead-in line with a three-word fragment, which reads
        as unfinished next to a large title. The fallback must itself be built
        from campaign data, never a fixed sentence, so this stays correct for
        any client.
        """

        text = str(text or "").strip()

        if len(text.split()) >= min_words:
            return text

        return fallback

    @staticmethod
    def shorten_entity(text, limit=32):

        """
        A company/account name short enough for one line of a table cell.

        Two things make these values long enough to wrap, and a wrapped cell
        grows its row -- which pushes the table past the space the template
        allotted it and over whatever sits below. PowerPoint grows rows at
        render time, so python-pptx reports the original height and no
        geometry check can detect it; the only reliable fix is to keep the
        text short in the first place.

        First, the source data concatenates the domain onto the name
        ("Solvay(solvay.com)"). That is dropped -- the domain adds nothing on
        a slide and nearly doubles the length. Only a trailing parenthetical
        that looks like a domain is removed, so a name with its own brackets
        (e.g. a Chinese entity name containing "(中国)") keeps them.

        Second, some names are simply long, so what remains is capped.
        """

        text = str(text or "").strip()

        # Trailing "(something.tld)" only -- requires a dot and a short
        # alphabetic suffix so it can't match a genuine bracketed name part.
        text = re.sub(r"\s*\([^()]*\.[A-Za-z]{2,6}\)\s*$", "", text).strip()

        if len(text) <= limit:
            return text

        return text[:limit].rstrip(" ,.;:-–—") + "…"

    @staticmethod
    def clip(text, limit):

        """
        Hard cap on AI text that has to fit a fixed-size template box.

        The prompt states these limits, but nothing guarantees a model honours
        them, and an over-long line doesn't just look untidy -- PowerPoint
        pushes it past the bottom of its box, over the footer and off the
        slide. Cutting at a word boundary here means the layout holds whatever
        comes back.
        """

        text = str(text or "").strip()

        if len(text) <= limit:
            return text

        # Strip trailing punctuation before adding the ellipsis, or a cut that
        # lands just after a sentence end reads as four dots ("...opportunities....").
        trimmed = text[:limit].rsplit(" ", 1)[0].rstrip(" .,;:-–—")

        return f"{trimmed}..."

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

        ppt["AI_ExecutiveSummary"] = self.clip(
            self.ai.get("executive_summary", ""),
            330
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

        # -------------------------------------------------
        # EXECUTIVE SUMMARY BODY (slide 3)
        #
        # That box is ten paragraphs, not one: an opening narrative, then four
        # number+label pairs each followed by a supporting line, then a closing
        # narrative. Only paragraph 0 was ever written, so paragraphs 1-9 kept
        # the template's own example figures -- "1,621 Total Leads (H1)",
        # "+0.75% QoQ (799 -> 805)", "19 Trending Topics Tracked", and a
        # closing line about healthcare organizations -- on the first content
        # slide of every client's deck.
        #
        # Paragraphs 1/3/5/7 hold two runs: the bold 20pt figure and its 14pt
        # label, so each is written by run index to keep that styling.
        # -------------------------------------------------

        def overall_metric(kpi):

            row = find_row(executive, "KPI", kpi)

            if row is None:
                return None

            try:
                return int(row["Overall"])
            except (TypeError, ValueError):
                return None

        def change_detail(metric):

            """First vs last comparison period for one metric -- the same
            basis as the status pills, so this line never disagrees with
            them."""

            if len(comparison_slots) < 2:
                return "Single period - no earlier period to compare against"

            before = comparison_slots[0]["metrics"].get(metric)
            after = comparison_slots[-1]["metrics"].get(metric)

            if not before and not after:
                return "No activity recorded"

            if not before:
                return f"New this period ({after:,})"

            pct = (after - before) / before * 100

            direction = "+" if pct >= 0 else ""

            return f"{direction}{pct:.2f}%  ({before:,} → {after:,})"

        topic_categories = self.tables.get("Topic Categories")

        category_count = 0 if topic_categories is None else len(topic_categories)

        exec_rows = [
            ("Total Leads", "Total Leads", change_detail("Total Leads")),
            ("Unique Accounts", "Unique Accounts", change_detail("Unique Accounts")),
            ("Assets Used", "Assets in Market", change_detail("Assets Used")),
            (
                "Trending Topics",
                "Trending Topics Tracked",
                f"Across {category_count} categories of buyer interest"
                if category_count
                else "No trending topic data for this campaign",
            ),
        ]

        for i, (kpi, label, detail) in enumerate(exec_rows):

            value = overall_metric(kpi)

            number_paragraph = 1 + i * 2

            ppt[f"AI_ExecSummary_num{i}"] = {
                "object": "AI_ExecutiveSummary",
                "paragraph_index": number_paragraph,
                "run_index": 0,
                "text": f"{self.format_count(value)}  " if value is not None else "",
            }

            ppt[f"AI_ExecSummary_lbl{i}"] = {
                "object": "AI_ExecutiveSummary",
                "paragraph_index": number_paragraph,
                "run_index": 1,
                "text": label,
            }

            ppt[f"AI_ExecSummary_det{i}"] = {
                "object": "AI_ExecutiveSummary",
                "paragraph_index": number_paragraph + 1,
                "text": detail,
            }

        # Closing narrative. ExecutiveConclusion was already being generated
        # and parsed but never placed on any slide.
        ppt["AI_ExecSummary_closing"] = {
            "object": "AI_ExecutiveSummary",
            "paragraph_index": 9,
            "text": self.clip(self.ai.get("executive_conclusion"), 210),
        }

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
                "Momentum & Forward Outlook",
                "Value-Add Lead Impact Summary",
            ]
        )

        # -------------------------------------------------
        # SLIDE TITLES the template hardcodes to a period
        #
        # These three read "H1 2026" / "Building H1 Momentum" in the template
        # and were never wired, so every deck claimed to cover H1 2026 no
        # matter which period was selected -- and "momentum" asserts growth,
        # which misreads a declining campaign. The period is already stated on
        # the cover and Campaign Snapshot, so these titles simply drop it
        # rather than restating it in a form that can go wrong.
        # -------------------------------------------------

        ppt["TITLE_TrendAnalysis"] = "Trend Analysis & Forward Projection"

        ppt["TITLE_ContentPerformance"] = "Content & Asset Performance"

        ppt["TITLE_H2Momentum"] = "Momentum & Forward Outlook"

        # "Weeks in Market (H1)" -- the number is wired below, but its caption
        # child carried the same hardcoded half-year.
        ppt["CARD_WeeksInMarketLabel"] = {
            "object": "CARD_WeeksInMarket",
            "group_child_index": 2,
            "text": "Weeks in Market",
        }

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
        # PER-PERIOD INSIGHTS
        #
        # One per period detail slide, looked up by that period's own label.
        # Previously only AI_Q1_Insight and AI_Q2_Insight were set, so on a
        # Month-over-Month run the third month onward (AI_P3_Insight, ...)
        # kept the template's example insight text.
        # -------------------------------------------------

        period_analysis = self.ai.get("period_analysis", {}) or {}

        for slot in periods.get("slots", []):

            ppt[f"AI_{slot['slot']}_Insight"] = self.clip(
                period_analysis.get(slot["label"], ""),
                220
            )

        # -------------------------------------------------
        # OPTIMIZATION ACTIONS (slide 9)
        #
        # AI_OptimizationSummary is a three-bullet action list -- three
        # paragraphs, each an "-  action" line -- not a prose box. It was being
        # filled by writing the summary plus newline-joined bullets into
        # paragraph 0, which left paragraphs 1 and 2 showing the template's own
        # actions ("...planning fresh creative for H2", "+10% QoQ shows early
        # traction") and pushed the combined text down over the footer.
        # -------------------------------------------------

        optimization = self.ai.get(
            "optimization",
            {}
        )

        ppt["AI_OptimizationHeading"] = "KEY OPTIMIZATION ACTIONS"

        optimization_actions = optimization.get("bullets", []) or []

        if not optimization_actions and optimization.get("summary"):
            optimization_actions = [optimization["summary"]]

        for i in range(3):

            action = (
                self.clip(optimization_actions[i], 105)
                if i < len(optimization_actions)
                else ""
            )

            ppt[f"AI_OptimizationAction{i}"] = {
                "object": "AI_OptimizationSummary",
                "paragraph_index": i,
                # The dash is part of the template's own run text rather than
                # list formatting, so it has to be rewritten with the action.
                "text": f"–  {action}" if action else "",
            }

        # -------------------------------------------------
        # COMPARISON
        # -------------------------------------------------

        comparison = self.ai.get("comparison", {})

        ppt["AI_ComparisonSummary"] = self.clip(
            comparison.get("summary", ""),
            210
        )

        bullets = comparison.get(
            "bullets",
            []
        )

        ppt["AI_ComparisonHeadline"] = self.clip(
            bullets[0] if len(bullets) > 0 else "",
            110
        )

        ppt["AI_ComparisonInsight1"] = self.clip(
            bullets[1] if len(bullets) > 1 else "",
            130
        )

        ppt["AI_ComparisonInsight2"] = self.clip(
            bullets[2] if len(bullets) > 2 else "",
            130
        )

        # The two figures above those insight captions were never wired, so
        # every deck showed the template's own "+0.75%" and "+18.58%" -- the
        # same example numbers that produced its fake "799 -> 805" leads.
        # They pair with Insight1 and Insight2, which the prompt asks to cover
        # Total Leads and Unique Accounts in that order.
        for i, metric in enumerate(("Total Leads", "Unique Accounts")):

            pct = None

            if len(comparison_slots) >= 2:

                before = comparison_slots[0]["metrics"].get(metric)
                after = comparison_slots[-1]["metrics"].get(metric)

                if before:
                    pct = (after - before) / before * 100

            ppt[f"KPI_ComparisonMetric{i + 1}"] = (
                f"{pct:+.2f}%" if pct is not None else "n/a"
            )

        # -------------------------------------------------
        # RECOMMENDATIONS (slide 25)
        #
        # The template holds all five in ONE box, AI_H2Recommendations, as
        # paragraphs 1-5 (paragraph 0 is the section title). Each of those
        # paragraphs splits into two runs: a bold "01   " number prefix and
        # the text -- so these target run 1, or the numbering would be
        # overwritten.
        #
        # This previously wrote to AI_Recommendation1..5 and
        # AI_RecommendationsSummary, none of which exist in the template, so
        # every recommendation was generated and then silently discarded
        # while the slide showed the template's own example actions.
        # AI_RecommendationsSummary has no counterpart box and its content
        # duplicates the five actions, so it is dropped rather than rehomed.
        # -------------------------------------------------

        recommendations = self.ai.get(
            "recommendations",
            {}
        )

        actions = recommendations.get(
            "actions",
            []
        )

        # Paragraph 0 is the box's own heading. The template hardcodes it to
        # "Momentum & 2026 Outlook", and it now sits directly beside the
        # slide's panel title -- so make it describe the list instead of
        # repeating the title with a year baked in.
        ppt["AI_H2RecommendationsHeading"] = {
            "object": "AI_H2Recommendations",
            "paragraph_index": 0,
            "text": "Recommended Next Steps",
        }

        for i in range(5):

            ppt[f"AI_H2Recommendation{i + 1}"] = {
                "object": "AI_H2Recommendations",
                "paragraph_index": i + 1,
                "run_index": 1,
                "text": self.clip(actions[i], 140) if i < len(actions) else "",
            }

        # -------------------------------------------------
        # VALUE ADD / PARTNERSHIP (slide 26)
        #
        # AI_ValueAddSummary doesn't exist either. The template's boxes are
        # AI_ValueAddHeading (the lead line) and AI_PartnershipSummary, whose
        # paragraph 0 is a fixed "WHAT THIS MEANS FOR THE PARTNERSHIP" label
        # with the body in paragraph 2.
        # -------------------------------------------------

        # Falls back to a sentence built from this campaign's own value-add
        # figures when the model answers too briefly for the slide's lead-in
        # line. Both the AI text and the fallback are campaign-derived.
        value_add_metrics_table = self.tables.get("Value Add Metrics")

        identified = engaged = None

        if value_add_metrics_table is not None and not value_add_metrics_table.empty:

            by_metric = {
                row["Metric"]: row["Value"]
                for _, row in value_add_metrics_table.iterrows()
            }

            identified = by_metric.get("Accounts Identified")
            engaged = by_metric.get("Accounts Engaged")

        if identified and engaged:
            value_add_fallback = (
                f"Beyond core lead delivery, intent and trending signals identified "
                f"{identified} accounts and actively engaged {engaged} of them."
            )
        else:
            value_add_fallback = (
                "Beyond core lead delivery, intent and trending signals identified "
                "and qualified an expanded pool of buying-ready accounts."
            )

        ppt["AI_ValueAddHeading"] = self.clip(
            self.at_least(
                self.ai.get("value_add_heading"),
                10,
                value_add_fallback
            ),
            190
        )

        partnership = self.ai.get("partnership", {}) or {}

        ppt["AI_PartnershipSummary"] = {
            "object": "AI_PartnershipSummary",
            "paragraph_index": 2,
            "text": self.clip(
                partnership.get("summary") or self.ai.get("value_add", ""),
                420
            ),
        }

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
        # SLIDE COMMENTARY BOXES
        #
        # Every box here previously showed the template's own example text --
        # sentences about a different campaign entirely ("Medical billing and
        # patient payments dominate conversation", "All 1,719 targeted
        # accounts...") sitting next to this client's real charts.
        #
        # Only boxes that carry an insight about the slide's data get AI
        # content. Labels, counts and boilerplate are computed below instead:
        # asking a model to restate a number it was handed is just a chance
        # for it to get the number wrong.
        # -------------------------------------------------

        def bulleted(object_name, bullets, limit, count=3):

            """Writes `count` body lines into a box whose paragraph 0 is a
            fixed bold label and paragraph 1 a blank spacer -- body starts at
            paragraph 2. Lines the AI didn't supply are blanked so no template
            sentence survives underneath."""

            for i in range(count):

                ppt[f"{object_name}_p{i}"] = {
                    "object": object_name,
                    "paragraph_index": i + 2,
                    "text": self.clip(bullets[i], limit) if i < len(bullets) else "",
                }

        trend = self.ai.get("trend_analysis", {}) or {}
        content_perf = self.ai.get("content_performance", {}) or {}
        audience = self.ai.get("audience_interest", {}) or {}
        engagement = self.ai.get("engagement", {}) or {}
        top_accounts = self.ai.get("top_accounts", {}) or {}
        opt_highlights = self.ai.get("optimization_highlights", {}) or {}
        learnings = self.ai.get("key_learnings", {}) or {}

        # Slide 13 - trend/projection chart
        ppt["AI_TrendAnalysisHeading"] = self.clip(trend.get("heading"), 95)
        bulleted("AI_TrendAnalysisSummary", trend.get("bullets", []), 125)

        # Slide 15 - asset contribution chart
        ppt["AI_ContentPerformanceHeading"] = self.clip(content_perf.get("heading"), 70)
        bulleted("AI_ContentPerformanceSummary", content_perf.get("bullets", []), 130)

        # Slide 17 - topic distribution
        ppt["AI_AudienceInterestHeading"] = self.clip(audience.get("heading"), 80)
        ppt["AI_AudienceInterestSummary"] = self.clip(audience.get("summary"), 180)

        # Slide 18 - engagement funnel
        bulleted("AI_EngagementSummary", engagement.get("bullets", []), 125)

        # Slide 19 - top accounts / intent tables
        ppt["AI_TopAccountsFooter"] = self.clip(top_accounts.get("footer"), 135)

        # Slide 23 - optimization highlights
        ppt["AI_OptimizationFooter"] = self.clip(opt_highlights.get("footer"), 190)

        # Slide 24 - key learnings: 5 pairs, even paragraphs are the bold
        # title, odd paragraphs the supporting detail. The template numbers
        # each title ("1.  Reach is outpacing volume.") as part of the text
        # rather than as list formatting, so the number is rebuilt here.
        items = learnings.get("items", []) or []

        for i in range(5):

            item = items[i] if i < len(items) and isinstance(items[i], dict) else {}

            title = self.clip(item.get("title"), 40)

            ppt[f"AI_KeyLearnings_t{i}"] = {
                "object": "AI_KeyLearnings",
                "paragraph_index": i * 2,
                "text": f"{i + 1}.  {title}" if title else "",
            }

            ppt[f"AI_KeyLearnings_d{i}"] = {
                "object": "AI_KeyLearnings",
                "paragraph_index": i * 2 + 1,
                "text": self.clip(item.get("detail"), 135),
            }

        # -------------------------------------------------
        # COMPUTED COMMENTARY (no AI)
        #
        # The template hardcodes "H1"/"H2" into these, which is wrong for any
        # campaign not running on that calendar, and phrases two of them as
        # growth ("momentum", "signals into action") which would misread a
        # declining campaign. Both use direction-neutral wording built from
        # the real period labels.
        # -------------------------------------------------

        period_label = periods.get("overall_label", "").split("  |  ")[0]
        period_label = period_label or "this period"

        ppt["AI_OptimizationHighlightsSummary"] = (
            f"Turning {period_label} signals into the next period's actions"
        )

        ppt["AI_ClosingMessage"] = (
            "Questions? Let's discuss how we build on these results together."
        )

        buying_stage = self.tables.get("Buying Stage Distribution")

        if buying_stage is not None and not buying_stage.empty:

            # The only client-specific value in this slide's commentary. The
            # two stage captions beside it (AI_BuyingStageHeading1/2) are left
            # at their template wording on purpose: they label the
            # KPI_BuyingStage1/2 figures, which key on those exact stage names
            # ("No Active Signals", "Consideration", "Decision"), so deriving
            # the captions from the data instead would risk a caption that
            # disagrees with the number printed next to it.
            total_signal_accounts = int(buying_stage[buying_stage.columns[-1]].sum())

            ppt["AI_BuyingStageSummary"] = (
                f"Where the {self.format_count(total_signal_accounts)} "
                f"signal-showing accounts sit in the buying journey"
            )

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

        # Account and topic values are shortened for display only -- the full
        # values stay in self.tables for the Excel export. A cell long enough
        # to wrap makes PowerPoint grow that row at render time, which pushes
        # the table past the height the template allotted it and over the
        # footnote below; because the growth happens at render time,
        # python-pptx still reports the original height and no geometry check
        # can catch it. Keeping the text short is the only reliable fix.
        top_engaged_accounts = self.tables.get("Top Engaged Accounts")

        if top_engaged_accounts is not None:
            top_engaged_accounts = top_engaged_accounts[
                ["Account Name", "Leads"]
            ].copy()

            top_engaged_accounts["Account Name"] = (
                top_engaged_accounts["Account Name"].apply(self.shorten_entity)
            )

        ppt["Table_TopEngagedAccounts"] = top_engaged_accounts

        top_intent = self.tables.get("Top Intent Companies")

        if top_intent is not None and not top_intent.empty:

            top_intent = top_intent.copy()

            if "Account" in top_intent.columns:
                top_intent["Account"] = top_intent["Account"].apply(
                    self.shorten_entity
                )

            if "Topic" in top_intent.columns:
                top_intent["Topic"] = top_intent["Topic"].apply(
                    lambda value: self.shorten_entity(value, limit=28)
                )

        ppt["Table_TopIntentCompanies"] = top_intent

        # The template's static heading reads "TOP INTENT COMPANIES (BY
        # ML SCORE)" -- these are accounts (the same entity as the Top
        # Engaged Accounts table beside it), and the "(BY ML SCORE)"
        # qualifier is already obvious from the table's own Score
        # column. Set from here rather than editing the template.
        ppt["AI_TopIntentHeading"] = "TOP INTENT ACCOUNTS"

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

        # The funnel carries an "All Accounts" series only when a Target
        # Account List History report was supplied -- that is the only export
        # holding the full targeted universe. When it's absent the chart shows
        # trending accounts alone, so the heading says so: a reader comparing
        # this against the platform would otherwise assume the smaller figures
        # were the whole picture rather than one of two series.
        if "All Accounts" in funnel_chart.columns:
            ppt["AI_EngagementHeading"] = (
                "From intent-based targeting to active engagement"
            )
        else:
            ppt["AI_EngagementHeading"] = (
                "Trending accounts only - from intent-based targeting to active engagement"
            )

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