import numpy as np
import pandas as pd

import config
from core.kpi_calculator import KPICalculator

from constants import (
    LEAD_DETAIL,
    ACCOUNT_ENGAGEMENT,
    TRENDING_TOPICS,
    TRENDING_ACCOUNTS,
    ASSET_DELIVERY,
    TARGET_ACCOUNT_HISTORY,
    CAMPAIGN,
    MONTHLY,
    QUARTERLY,
    CUSTOM
)

class LeadGenAnalyzer:

    def __init__(self, datasets, full_leads=None):

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

        # Campaign Snapshot (and the merged period date box) always show
        # the true full campaign, even in Quarterly/Custom modes where
        # self.leads above has already been scoped to just the union of
        # the 2 selected periods -- falls back to self.leads if the
        # unfiltered version wasn't supplied, so this stays optional.
        self.leads_full = full_leads if full_leads is not None else self.leads
        self.account_engagement = datasets[ACCOUNT_ENGAGEMENT]
        self.trending_topics = datasets[TRENDING_TOPICS]
        self.trending_accounts = datasets[TRENDING_ACCOUNTS]
        self.asset_delivery = datasets[ASSET_DELIVERY]

        from core.date_engine import DateEngine

        self.periods = DateEngine(self.leads).split_periods()

    # ------------------------------------------------

    def _period_columns(self):

        """
        Returns ("Q1", df_a, "Q2", df_b) for the two periods that drive
        every before/after comparison table (Executive/QoQ/Snapshot).
        The "Q1"/"Q2" labels are fixed on purpose -- every PPT object
        and AI export field downstream is wired to those exact column
        names -- only which DataFrame sits in each slot changes with
        the selected analysis mode:

        - Quarter over Quarter / Custom Date Range: the two periods the
          user picked, chronologically.
        - Full Campaign (1 period): the same period in both slots, so
          comparisons degrade to zero-change rather than crashing.
        - Month over Month (3+ periods): earliest vs most recent month,
          a representative before/after snapshot. A true month-by-month
          trend is a separate table (see monthly_leads()) and is a
          slide-design decision for a later pass, not a data gap.
        """

        names = list(self.periods.keys())

        if len(names) == 1:
            df = self.periods[names[0]]
            return "Q1", df, "Q2", df

        return (
            "Q1", self.periods[names[0]],
            "Q2", self.periods[names[-1]]
        )

    # ------------------------------------------------

    @staticmethod
    def _bounds(df):

        # Month-over-Month slices (DateEngine.split_periods()) stamp the
        # real calendar month's clipped bounds here -- prefer that over
        # this dataset's own min/max, which for a month with sparse or
        # zero leads would understate the month's true date range (or,
        # for an empty slice, have no dates to compute from at all).
        period_bounds = df.attrs.get("period_bounds")

        if period_bounds is not None:
            return period_bounds

        dates = df["Date"].dropna()

        if dates.empty:
            return None, None

        return dates.min(), dates.max()

    @staticmethod
    def _fmt(d):
        return d.strftime("%d %b %Y") if d is not None else ""

    @staticmethod
    def _slot_id(index):

        """
        Object-name token for the index'th performance slot. The first
        two reuse the template's existing "Q1"/"Q2" objects (no cloning
        needed); the third onward name the clones that slide_ops.py
        produces, one divider+detail pair per slot.
        """

        return ("Q1", "Q2")[index] if index < 2 else f"P{index + 1}"

    @staticmethod
    def _slot_metrics(df):

        """KPI-card figures for one performance detail slide, computed
        straight from that slot's own DataFrame so this works uniformly
        whether there are 2 slots (Quarterly/Custom) or N (Month over
        Month) -- no dependence on the fixed 2-column Executive table."""

        def top_value(column):

            if df.empty or column not in df.columns:
                return ""

            mode = df[column].mode()

            return mode.iloc[0] if not mode.empty else ""

        return {
            "Total Leads": KPICalculator.row_count(df),
            "Unique Accounts": KPICalculator.unique(df, "Account Name"),
            "Assets Used": KPICalculator.unique(df, "Asset Name"),
            "Job Titles": KPICalculator.unique(df, "Job Title"),
            "Countries": KPICalculator.unique(df, "Country"),
            "Top Asset": top_value("Asset Name"),
            "Top Topic": top_value("Top MLI Topic (Average Over Last 7 Weeks)"),
        }

    def _slot(self, index, label, df):

        start, end = self._bounds(df)

        return {
            "slot": self._slot_id(index),
            "label": label,
            "df": df,
            "start": self._fmt(start),
            "end": self._fmt(end),
            "metrics": self._slot_metrics(df),
        }

    @staticmethod
    def _constituent_month_periods(df):

        """Splits a DataFrame into chronological (pandas Period, month_df)
        pairs, one per calendar month present. The raw Period (not just
        its label) is what lets forecasting continue the sequence -- e.g.
        knowing "June 2026" is the last real month to compute "July 2026"
        as the next one."""

        dated = df.dropna(subset=["Date"])

        if dated.empty:
            return []

        month_key = dated["Date"].dt.to_period("M")

        return [
            (period, dated[month_key == period])
            for period in sorted(month_key.unique())
        ]

    @staticmethod
    def _group_by_calendar_quarter(months):

        """Groups a chronological [(Period('M'), df), ...] list by the
        real calendar quarter each month falls in (Jan-Mar, Apr-Jun,
        Jul-Sep, Oct-Dec), labeled sequentially Q1, Q2, ... in
        chronological order. A quarter missing one of its 3 months
        (e.g. that month had zero leads and was skipped entirely) still
        forms one group from whichever real months belong to it --
        unlike a fixed 50/50 split, this reflects the actual number of
        real quarters the campaign spans, and unlike requiring 3
        strictly consecutive months, a gap (a skipped empty month)
        doesn't prevent the surrounding real months from being grouped
        under their shared quarter."""

        quarter_groups = {}

        for period, df in months:

            key = (period.year, period.quarter)

            quarter_groups.setdefault(key, []).append(df)

        return [
            (f"Q{i}", pd.concat(dfs))
            for i, dfs in enumerate(quarter_groups.values(), start=1)
        ]

    @classmethod
    def _constituent_months(cls, df):

        """Splits a DataFrame into chronological (label, month_df) pairs,
        one per calendar month present -- used to give Full Campaign's
        comparison chart/table a month-level breakdown even though the
        mode itself doesn't split into per-month detail slides."""

        return [
            (period.strftime("%B %Y"), month_df)
            for period, month_df in cls._constituent_month_periods(df)
        ]

    @staticmethod
    def _bucket_into_two(items):

        """Splits a chronological (label, df) list into two combined
        groups (first half vs second half), used whenever there are too
        many periods to show individually on the comparison chart/table."""

        midpoint = (len(items) + 1) // 2

        def combine(group):

            labels = [label for label, _ in group]
            dfs = [df for _, df in group]

            if not dfs:
                return "", pd.DataFrame()

            combined = pd.concat(dfs)

            label = labels[0] if len(labels) == 1 else f"{labels[0]} - {labels[-1]}"

            return label, combined

        return [combine(items[:midpoint]), combine(items[midpoint:])]

    @staticmethod
    def _trend_metrics(df):

        return {
            "Total Leads": KPICalculator.row_count(df),
            "Unique Accounts": KPICalculator.unique(df, "Account Name"),
        }

    @staticmethod
    def _label_span(label):

        """How many calendar months a trend point represents -- 3 for a
        combined "Q" quarter point, 1 for an individual month point.
        Used to put mixed-granularity points on a comparable per-month
        basis before fitting a trend across them."""

        return 3 if label.startswith("Q") and label[1:].isdigit() else 1

    def _half_period_trend(self, df, metric_names):

        """Estimates growth/decline for a single real trend point (one
        lone period with nothing else to compare it to) by comparing its
        own first half against its second half -- the only way to see a
        direction with just one period of data. The half-to-half delta
        is doubled to read as a full-period-equivalent (per-month) rate,
        comparable to a real month-over-month delta."""

        dated = df.dropna(subset=["Date"])

        if dated.empty or dated["Date"].nunique() < 2:
            return {metric: 0 for metric in metric_names}

        start, end = dated["Date"].min(), dated["Date"].max()
        midpoint = start + (end - start) / 2

        first_half = dated[dated["Date"] <= midpoint]
        second_half = dated[dated["Date"] > midpoint]

        first_metrics = self._trend_metrics(first_half)
        second_metrics = self._trend_metrics(second_half)

        return {
            metric: (second_metrics[metric] - first_metrics[metric]) * 2
            for metric in metric_names
        }

    @staticmethod
    def _project_trend(values, spans, count, forecast_span, fallback_delta=None):

        """Projects `count` more points continuing the overall growth/
        decline trend across ALL real points -- a least-squares fit on
        each point's per-month rate (value / its own span), so a 3-month
        "Q" point and a 1-month point sit on a comparable scale -- rather
        than just the last two, so a single noisy or in-progress trailing
        period (e.g. a month whose data cuts off mid-month) doesn't
        produce a misleading cliff. `forecast_span` is how many months
        each projected point itself represents (3 when continuing as
        more quarters, 1 when continuing as more months). A lone real
        point has no multi-point trend to fit -- `fallback_delta` (a
        per-month rate, from `_half_period_trend`) is used instead."""

        n = len(values)

        if n == 0:
            return [0] * count

        rates = [value / span for value, span in zip(values, spans)]

        if n == 1:

            delta = fallback_delta or 0
            last_rate = rates[0]
            forecast = []

            for _ in range(count):
                last_rate = last_rate + delta
                forecast.append(max(0, round(last_rate * forecast_span)))

            return forecast

        slope, intercept = np.polyfit(np.arange(n), rates, 1)

        forecast = []

        for i in range(count):
            rate = intercept + slope * (n + i)
            forecast.append(max(0, round(rate * forecast_span)))

        return forecast

    def _build_trend_projection(self):

        """
        Builds the Total Leads / Unique Accounts trend chart's data.
        Which periods count as "real" varies by mode:

        - Month over Month: every month, individually, no grouping.
        - Full Campaign / Custom Date Range: constituent months, with any
          run of 3 consecutive months that completes a real calendar
          quarter (Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec) combined into one
          "Q" point (numbered sequentially in the order found); any month
          that isn't part of such a complete quarter -- because the
          campaign never completes one, or because it's left over once
          complete quarters are pulled out -- stays an individual point.
        - Quarter over Quarter: the 2 selected quarters, as "Q1"/"Q2".

        The forecast continues the overall trend across every real point
        (a least-squares fit on each point's per-month rate, so a 3-month
        "Q" point and a 1-month point sit on a comparable scale) rather
        than just the last two, so a single noisy or in-progress trailing
        period doesn't produce a misleading cliff. A lone real point
        (e.g. exactly one calendar month of data) has no multi-point
        trend to fit -- its own first half vs second half estimates a
        direction instead. Forecast labels continue in whatever style
        the last real point was (more "Q" numbers after a quarter point,
        more month names after a month point).
        """

        mode = config.REPORT_MODE

        real_points = []
        real_dfs = []
        continue_from = None

        if mode in (MONTHLY, CAMPAIGN, QUARTERLY):

            # Real calendar quarters (a quarter missing one of its 3 months,
            # e.g. a month with zero leads that got skipped, still forms one
            # group from whichever real months belong to it). Several
            # individual months read as a noisy zigzag line -- grouping gives
            # a clean few-point real trend to project a forecast from instead
            # of fitting a line through every swing. Since Quarter over
            # Quarter's ANALYSIS_WINDOW is the whole campaign (every real
            # quarter, not a couple hand-picked ones), deriving straight from
            # self.leads here reproduces the exact same quarters as
            # self.periods does for that mode.
            months = self._constituent_month_periods(self.leads)

            # ...but ONLY when the quarters being compared are actually
            # comparable. Grouping a campaign that spans, say, April to July
            # buckets three months into one quarter and the fourth into the
            # next, so the chart plots a 3-month total against a 1-month total
            # and shows a ~90% "collapse" that is purely an artefact of
            # unequal bucket sizes -- which then drags the forecast to zero and
            # makes the whole chart unreadable. Below MIN_MONTHS_TO_GROUP there
            # are few enough months to plot individually, which is both honest
            # (every point covers one month) and gives the fit more points to
            # work with.
            if len(months) < config.MIN_MONTHS_TO_GROUP:

                points = [
                    (period.strftime("%B"), month_df)
                    for period, month_df in months
                ]

            else:
                points = self._group_by_calendar_quarter(months)

            for label, df in points:
                real_points.append((label, self._trend_metrics(df)))
                real_dfs.append(df)

            continue_from = months[-1][0] if months else None

            forecast_count = 3

        else:  # CUSTOM

            # The single user-selected period, already auto-bisected
            # into "Period 1" / "Period 2" by DateEngine.split_periods()
            # -- show that real before/after (using those actual labels,
            # not "Q1"/"Q2" -- this is an arbitrary custom range, not a
            # calendar quarter), then forecast 2 more chunks the same
            # size as those halves.
            period_items = list(self.periods.items())

            real_points = [
                (name, self._trend_metrics(df))
                for name, df in period_items
            ]
            real_dfs = [df for _, df in period_items]

            forecast_count = 2

        labels = [point[0] for point in real_points]
        metric_names = ["Total Leads", "Unique Accounts"]

        series_values = {
            metric: [point[1][metric] for point in real_points]
            for metric in metric_names
        }

        spans = [self._label_span(label) for label in labels]
        last_label = labels[-1] if labels else ""
        forecast_span = self._label_span(last_label) if last_label else 1

        forecast_values = {}

        for metric in metric_names:

            fallback_delta = (
                self._half_period_trend(real_dfs[0], metric_names)[metric]
                if len(real_points) == 1
                else None
            )

            forecast_values[metric] = self._project_trend(
                series_values[metric], spans, forecast_count, forecast_span, fallback_delta
            )

        is_quarter_ending = last_label.startswith("Q") and last_label[1:].isdigit()
        is_period_ending = last_label.startswith("Period ") and last_label[7:].isdigit()

        if is_quarter_ending:

            last_q_num = int(last_label[1:])
            forecast_labels = [
                f"Q{last_q_num + i + 1}" for i in range(forecast_count)
            ]

        elif is_period_ending:

            # Custom mode's bisected "Period 1"/"Period 2" real points --
            # continue the same naming ("Period 3", "Period 4", ...)
            # rather than quarter or month-name labels, which wouldn't
            # match an arbitrary user-selected range.
            last_period_num = int(last_label[7:])
            forecast_labels = [
                f"Period {last_period_num + i + 1}" for i in range(forecast_count)
            ]

        else:

            forecast_labels = []
            period = continue_from

            for _ in range(forecast_count):

                period = period + 1 if period is not None else None
                forecast_labels.append(period.strftime("%B") if period is not None else "")

        all_labels = labels + forecast_labels
        is_forecast = [False] * len(labels) + [True] * forecast_count

        rows = []

        for i, label in enumerate(all_labels):

            row = {"Period": label, "Is Forecast": is_forecast[i]}

            for metric in metric_names:
                row[metric] = (series_values[metric] + forecast_values[metric])[i]

            rows.append(row)

        self.tables["Trend Projection"] = pd.DataFrame(rows)

    def _build_period_meta(self):

        """
        Human-facing labels/dates for the selected analysis mode, used
        by every slide that describes "what period is this". Computed
        once here (business logic) so PresentationData only has to
        format, never decide.
        """

        bounds = self._bounds
        fmt = self._fmt

        mode = config.REPORT_MODE

        name_a, a, name_b, b = self._period_columns()
        a_start, a_end = bounds(a)
        b_start, b_end = bounds(b)

        if mode == CAMPAIGN:

            label_a = label_b = "Full Campaign"
            overall_label = "Full Campaign"
            comparison_label = "Campaign Overview & Highlights"

            month_periods = self._constituent_month_periods(self.leads)

            # "QoQ" framing only makes sense once there are at least 2
            # real calendar quarters to compare -- the same calendar-
            # quarter grouping the comparison table/chart and trend
            # chart both use below, so this title never claims "QoQ"
            # while those are actually showing something else.
            real_quarters = len(self._group_by_calendar_quarter(month_periods))

            detail_metrics_title = (
                "Detailed QoQ Metrics & Optimization Status"
                if real_quarters >= 2
                else "Detailed Campaign Metrics & Optimization Status"
            )

            slots = [self._slot(0, "Full Campaign", self.leads)]

            if not month_periods:
                comparison_slots = slots
            elif len(month_periods) <= 3:
                comparison_slots = [
                    self._slot(i, period.strftime("%B %Y"), df)
                    for i, (period, df) in enumerate(month_periods)
                ]
            else:
                comparison_slots = [
                    self._slot(i, name, df)
                    for i, (name, df) in enumerate(
                        self._group_by_calendar_quarter(month_periods)
                    )
                ]

        elif mode in (MONTHLY, QUARTERLY):

            # Both walk self.periods the same way -- month-keyed for
            # Month over Month, quarter-keyed for Quarter over Quarter
            # (DateEngine.split_periods() builds either one automatically
            # from every real period in the campaign, no manual picking)
            # -- capped at MAX_MONTHLY_DETAIL_SLIDES individual detail
            # slides, with any remainder bucketed for the comparison
            # table/chart only.
            period_items = list(self.periods.items())

            label_a = period_items[0][0]
            label_b = period_items[-1][0]

            if mode == MONTHLY:
                overall_label = "Monthly Trend"
                comparison_label = "Month-over-Month Comparative Analysis"
                detail_metrics_title = "Detailed Month-over-Month Metrics & Optimization Status"
            else:
                overall_label = f"{label_a} vs {label_b}"
                comparison_label = "Quarter-over-Quarter Comparative Analysis"
                detail_metrics_title = "Detailed QoQ Metrics & Optimization Status"

            capped = period_items[: config.MAX_MONTHLY_DETAIL_SLIDES]
            overflow = period_items[config.MAX_MONTHLY_DETAIL_SLIDES :]

            slots = [
                self._slot(i, name, df)
                for i, (name, df) in enumerate(capped)
            ]

            if len(overflow) >= 2:

                bucketed = self._bucket_into_two(overflow)
                comparison_slots = slots + [
                    self._slot(len(slots), bucketed[0][0], bucketed[0][1]),
                    self._slot(len(slots) + 1, bucketed[1][0], bucketed[1][1]),
                ]

            elif len(overflow) == 1:

                # A single leftover period can't be split into 2 buckets
                # (the second half would be empty) -- just add it as its
                # own slot instead of forcing an artificial 2-way split.
                name, df = overflow[0]
                comparison_slots = slots + [self._slot(len(slots), name, df)]

            else:
                comparison_slots = slots

        else:  # CUSTOM

            # Only one period was ever selected here -- it gets exactly
            # one detail slide-pair (agenda item, slide 6), same
            # treatment as Full Campaign's single slot, rather than
            # being presented as two separate "Period 1"/"Period 2"
            # sections. DateEngine.split_periods() still auto-bisects
            # this same window into "Period 1" / "Period 2" internally
            # -- that breakdown is used only by comparison_slots below,
            # which feeds the comparison/trend slides (10/11/13) that
            # need a before/after to show.
            period_items = list(self.periods.items())

            label_a = label_b = "Custom Period"
            overall_label = "Custom Period"
            comparison_label = "Period-over-Period Comparative Analysis"
            detail_metrics_title = "Detailed Period-over-Period Metrics & Optimization Status"

            slots = [self._slot(0, "Custom Period", self.leads)]

            comparison_slots = [
                self._slot(i, name, df)
                for i, (name, df) in enumerate(period_items)
            ]

        agenda_items = [f"{slot['label']} Performance" for slot in slots]

        # Always the true full campaign span (see leads_full in
        # __init__) -- this drives the merged period date box on
        # Campaign Snapshot, which should never shrink to just the
        # selected window in Quarterly/Custom modes.
        overall_start = self.leads_full["Date"].min()
        overall_end = self.leads_full["Date"].max()
        overall_range = f"{fmt(overall_start)} - {fmt(overall_end)}"

        self.period_meta = {

            "Q1": {"label": label_a, "start": fmt(a_start), "end": fmt(a_end)},
            "Q2": {"label": label_b, "start": fmt(b_start), "end": fmt(b_end)},

            "slots": slots,
            "comparison_slots": comparison_slots,

            "agenda_items": agenda_items,

            "comparison_label": comparison_label,

            "detail_metrics_title": detail_metrics_title,

            "section_title": f"{label_a} Performance",

            "overall_range": overall_range,

            "overall_label": f"{overall_label}  |  {overall_range}",

            "campaign_description": f"{overall_range}  ·  {config.CAMPAIGN_TYPE} Campaign",

        }

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

        name_a, a, name_b, b = self._period_columns()

        kpi_columns = {
            "Total Leads": lambda df: KPICalculator.row_count(df),
            "Unique Accounts": lambda df: KPICalculator.unique(df, "Account Name"),
            "Assets Used": lambda df: KPICalculator.unique(df, "Asset Name"),
            "Job Titles": lambda df: KPICalculator.unique(df, "Job Title"),
            "Countries": lambda df: KPICalculator.unique(df, "Country"),
        }

        rows = []

        for kpi, overall_value in executive.items():

            row = {
                "KPI": kpi,
                "Overall": overall_value,
                "Change":  None,
                "% Change": None
            }

            column_fn = kpi_columns.get(kpi)

            if column_fn:

                row[name_a] = column_fn(a)
                row[name_b] = column_fn(b)

                row["Change"] = KPICalculator.change(row[name_a], row[name_b])
                row["% Change"] = KPICalculator.pct_change(row[name_a], row[name_b])

            rows.append(row)

        self.tables["Executive"] = pd.DataFrame(rows)

    # ------------------------------------------------

    def run(self):

        self._build_period_meta()

        self._build_trend_projection()

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

        self._build_comparison_overview()

        self.build_trending_account_summary()

        self.build_buying_stage_table()

        self.build_funnel_table()

        self.build_conversion_table()

        self.build_value_add_metrics()

        self.build_asset_summary()

        self.build_asset_ranking()

        self.build_asset_contribution()

        self.build_asset_efficiency()

        return self
    
    def build_period_tables(self):

        name_a, a, name_b, b = self._period_columns()

        for period_name, df in [(name_a, a), (name_b, b)]:

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

        """Top accounts by ML intent score, each shown with the single
        topic they're most engaged with (their highest-scoring topic,
        i.e. what they're "surging on") rather than an average across
        every topic they've touched -- an account's real story is which
        specific topic is driving their score, not a blended number.

        The source report calls this column "Company" (that name is also
        what core/detector.py keys on to recognise the report, so it
        stays untouched on the raw dataframe), but the deck presents
        these as accounts -- so the output column is renamed to
        "Account" here, keeping the PPT table, Excel export and AI
        export all consistent with that wording."""

        df = self.trending_topics

        if df.empty:
            self.tables["Top Intent Companies"] = pd.DataFrame(
                columns=["Account", "Topic", "MLScore"]
            )
            return

        top_topic_idx = (
            df.groupby("Company")["ML Insights Score"].idxmax()
        )

        table = (
            df.loc[
                top_topic_idx,
                ["Company", "Topic", "ML Insights Score"]
            ]
            .rename(columns={
                "Company": "Account",
                "ML Insights Score": "MLScore",
            })
            .sort_values("MLScore", ascending=False)
        )

        self.tables["Top Intent Companies"] = table.head(20)

    def build_qoq_comparison(self):

        name_a, a, name_b, b = self._period_columns()

        comparison = []

        metrics = [

            ("Total Leads",
            len(a),
            len(b)),

            ("Unique Accounts",
            a["Account Name"].nunique(),
            b["Account Name"].nunique()),

            ("Assets Used",
            a["Asset Name"].nunique(),
            b["Asset Name"].nunique()),

            ("Job Titles",
            a["Job Title"].nunique(),
            b["Job Title"].nunique()),

            ("Countries",
            a["Country"].nunique(),
            b["Country"].nunique())

        ]

        for metric, a_value, b_value in metrics:

            comparison.append({

                "Metric": metric,

                name_a: a_value,

                name_b: b_value,

                "Change": KPICalculator.change(a_value, b_value),

                "% Change": KPICalculator.pct_change(a_value, b_value) or 0

            })

        self.tables["QoQ Comparison"] = pd.DataFrame(comparison)

    # Per-metric, per-status recommendation phrasing -- descriptive
    # rather than a single generic line reused across every metric.
    # These 5 metrics are the deck's own fixed KPI taxonomy (same set
    # hardcoded in engine/presentation_data.py's StatusPill_* mapping),
    # not client-specific data, so naming them here follows the same
    # pattern already used elsewhere for this table.
    _RECOMMENDATION_TEMPLATES = {

        "Total Leads": {
            "Strong Growth": "Lead volume is up {pct}% – scale the channels and assets driving it.",
            "Stable Growth": "Lead volume grew {pct}% – continue the current optimization cadence.",
            "No Change": "Lead volume held flat – monitor next period before adjusting spend.",
            "Decline": "Lead volume dropped {abs_pct}% – investigate the cause and reallocate budget.",
        },

        "Unique Accounts": {
            "Strong Growth": "Account reach is up {pct}% – scale the current account-based targeting strategy.",
            "Stable Growth": "Account reach grew {pct}% – continue expanding the target account list.",
            "No Change": "Account reach held flat – revisit targeting criteria to widen the net.",
            "Decline": "Account reach dropped {abs_pct}% – review the targeting list for coverage gaps.",
        },

        "Assets Used": {
            "Strong Growth": "Asset variety is up {pct}% – keep rotating fresh content into the mix.",
            "Stable Growth": "Asset variety grew {pct}% – continue testing new formats alongside top performers.",
            "No Change": "Asset variety held flat – test an additional asset next period to keep content fresh.",
            "Decline": "Asset variety dropped {abs_pct}% – refresh the content mix to re-engage accounts.",
        },

        "Job Titles": {
            "Strong Growth": "Persona reach is up {pct}% – keep broadening title targeting.",
            "Stable Growth": "Persona reach grew {pct}% – continue broadening persona/title reach.",
            "No Change": "Persona reach held flat – expand messaging to reach adjacent titles.",
            "Decline": "Persona reach dropped {abs_pct}% – revisit persona targeting to widen title coverage.",
        },

        "Countries": {
            "Strong Growth": "Geographic reach is up {pct}% – scale into the strongest-performing regions.",
            "Stable Growth": "Geographic reach grew {pct}% – continue evaluating expansion into new regions.",
            "No Change": "Geographic footprint held flat – evaluate geographic expansion opportunities.",
            "Decline": "Geographic reach dropped {abs_pct}% – review regional targeting for gaps.",
        },
    }

    _DEFAULT_RECOMMENDATIONS = {
        "Strong Growth": "Scale current strategy.",
        "Stable Growth": "Continue optimization.",
        "No Change": "Monitor performance.",
        "Decline": "Investigate and optimize.",
    }

    @classmethod
    def _status_label(cls, metric, pct):

        """Growth/decline label + a metric-specific recommendation for
        a % change value. Shared by the fixed 2-slot Optimization
        Insights table and the N-period Comparison Overview, so both
        read the same thresholds and phrasing."""

        if pct > 10:
            status = "Strong Growth"
        elif pct > 0:
            status = "Stable Growth"
        elif pct == 0:
            status = "No Change"
        else:
            status = "Decline"

        template = cls._RECOMMENDATION_TEMPLATES.get(
            metric, cls._DEFAULT_RECOMMENDATIONS
        )

        recommendation = template[status].format(pct=pct, abs_pct=abs(pct))

        return status, recommendation

    def build_optimization_insights(self):

        comparison = self.tables["QoQ Comparison"]

        period_columns = [
            col for col in comparison.columns
            if col not in ("Metric", "Change", "% Change")
        ]

        insights = []

        for _, row in comparison.iterrows():

            metric = row["Metric"]

            pct = row["% Change"]

            status, recommendation = self._status_label(metric, pct)

            insight = {"Metric": metric}

            for col in period_columns:
                insight[col] = row[col]

            insight.update({
                "% Change": pct,
                "Status": status,
                "Recommendation": recommendation
            })

            insights.append(insight)

        self.tables["Optimization Insights"] = pd.DataFrame(insights)

    def _build_comparison_overview(self):

        """
        A generic "how did this trend overall" summary -- first vs last
        comparison_slot for each metric -- computed directly from real
        slot data rather than the fixed 2-slot QoQ Comparison table.

        QoQ Comparison is tied to _period_columns()'s Q1/Q2 (which, for
        Full Campaign, is the same single period duplicated into both
        slots -- an intentional zero-change placeholder for slides 6/8's
        before/after cards, but meaningless as "the" change figure for
        the comparison table/status pills whenever there are 3+ real
        comparison_slots to actually compare across (e.g. Full Campaign
        spanning several months). This looks at the real first and last
        slots instead, so % Change and Status are meaningful regardless
        of which analysis mode is selected.
        """

        slots = self.period_meta.get("comparison_slots", [])

        if len(slots) < 2:
            self.tables["Comparison Overview"] = pd.DataFrame()
            return

        first_metrics = slots[0]["metrics"]
        last_metrics = slots[-1]["metrics"]

        metric_names = [
            "Total Leads", "Unique Accounts",
            "Assets Used", "Job Titles", "Countries"
        ]

        rows = []

        for metric in metric_names:

            before = first_metrics[metric]
            after = last_metrics[metric]

            pct = KPICalculator.pct_change(before, after) or 0
            status, recommendation = self._status_label(metric, pct)

            rows.append({
                "Metric": metric,
                "% Change": pct,
                "Status": status,
                "Recommendation": recommendation,
            })

        self.tables["Comparison Overview"] = pd.DataFrame(rows)

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

        df = self.trending_accounts.copy()

        # Some clients' raw stage values use underscores instead of
        # spaces (e.g. "No_Asset_Information") -- as a single unbroken
        # "word" with no space to wrap on, that value can't wrap across
        # lines like "No Active Signals" does and instead overlaps the
        # neighboring axis label. Spacing it out gives the chart a
        # natural wrap point, same as every other stage name already has.
        df["Predictive Buying Stage"] = df["Predictive Buying Stage"].str.replace(
            "_", " ", regex=False
        )

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

        """3-stage account funnel (Targeted / Reached / Engaged), each
        stage showing the Trending-Accounts-report figure always, plus
        an "All Accounts" figure whenever a Target Account List History
        report is present for this campaign -- that's the only loaded
        report that can tell us the true full targeted universe, since
        Trending Accounts only ever contains accounts that are already
        trending (confirmed true for every client's export seen so far).
        Reached/Engaged "All Accounts" are an approximation from Account
        Engagement (which does cover non-trending accounts too): Reached
        = any recorded activity, Engaged = at least one lead."""

        df = self.trending_accounts

        stages = ["Targeted", "Reached", "Engaged"]

        trending_values = [
            len(df),
            (df["Reached"] == "Yes").sum(),
            (df["Engaged"] == "Yes").sum(),
        ]

        funnel = pd.DataFrame({"Stage": stages, "Trending": trending_values})

        history = self.datasets.get(TARGET_ACCOUNT_HISTORY)

        if history is None or "Accounts Targeted" not in getattr(history, "columns", []):

            # Say so rather than silently dropping half the chart. Without this
            # the funnel quietly renders a single series and looks like a bug in
            # the chart rather than a missing input.
            print(
                "\n[FUNNEL] No Target Account List History report found - "
                "the 'All Accounts' series is omitted."
            )
            print(
                "         Only that report carries the full targeted universe; "
                "Account Engagement covers accounts with activity and Trending "
                "Accounts only trending ones, so neither can substitute for it."
            )
            print(
                "         Export that report for this campaign into input/ to "
                "show All Accounts alongside Trending.\n"
            )

        else:

            targeted_all = self._targeted_universe(history)

            engagement = self.account_engagement

            # Reached = present in Account Engagement at all (some
            # campaign delivery touched them, whether or not this
            # program tracks Site Visits/Impressions/Clicks -- some
            # exports, like content syndication-only programs, log those
            # columns as 0 for every row). Engaged = a stricter subset,
            # accounts that also generated a lead. When every logged
            # account already has a lead (an Account Engagement export
            # scoped the same way Trending Accounts is), the two figures
            # come out equal -- same degenerate case already accepted
            # for Targeted/Trending, not a bug.
            reached_all = engagement["Account Name"].nunique()

            engaged_all = engagement.loc[
                engagement["Leads"].fillna(0) > 0, "Account Name"
            ].nunique()

            # A funnel cannot narrow upwards: fewer accounts targeted than
            # reached is arithmetically impossible and means one of the three
            # figures doesn't describe what we think it does. Publishing it
            # anyway puts a self-contradicting chart in front of a client, so
            # the series is dropped and the contradiction reported instead.
            if targeted_all is None or targeted_all < reached_all:

                print(
                    "\n[FUNNEL] 'All Accounts' series suppressed - the figures "
                    "contradict each other."
                )
                print(
                    f"         Targeted={targeted_all} but Reached={reached_all}; "
                    "a funnel cannot reach more accounts than it targeted."
                )
                print(
                    "         Check the Target Account List History export for "
                    "this campaign - showing Trending only rather than an "
                    "impossible chart.\n"
                )

            else:
                funnel["All Accounts"] = [targeted_all, reached_all, engaged_all]

        self.tables["Account Funnel"] = funnel

    @staticmethod
    def _targeted_universe(history):

        """
        The size of the target account list, read as a value rather than a row
        count.

        This previously used `notna().sum()`, which counts rows. A Target
        Account List History export carries one row per date (that is what
        makes it a history, and why it also has New/Removed Accounts columns),
        so counting rows returns the number of dates in the report and not the
        number of accounts at all -- which is how a campaign came out with 651
        targeted against 1,959 reached.

        The largest value across the history is used: for a report covering the
        campaign period, that is the widest the target list ever was, which is
        what "accounts targeted" should mean over a reporting window. Reading
        the latest row instead would understate it whenever accounts were
        removed part-way through.
        """

        if "Accounts Targeted" not in getattr(history, "columns", []):
            return None

        values = pd.to_numeric(history["Accounts Targeted"], errors="coerce").dropna()

        if values.empty:
            return None

        return int(values.max())

    def build_conversion_table(self):

        funnel = self.tables["Account Funnel"]

        targeted = funnel.iloc[0]["Trending"]
        reached = funnel.iloc[1]["Trending"]
        engaged = funnel.iloc[2]["Trending"]

        rows = []

        rows.append({

            "Conversion":

            "Reached / Targeted",

            "Rate":

            round(reached / targeted * 100, 2)

            if targeted else 0

        })

        rows.append({

            "Conversion":

            "Engaged / Reached",

            "Rate":

            round(engaged / reached * 100, 2)

            if reached else 0

        })

        self.tables["Account Conversion"] = pd.DataFrame(rows)

    def build_value_add_metrics(self):

        """The 4 KPI cards on the Value-Add Lead Impact Summary slide --
        computed from the real Trending Accounts / Account Engagement
        data (never a fixed example figure). Trending Accounts has no
        Date column, so "Accounts Identified"/"Sales-Ready" are already
        whole-campaign totals by construction, same as the Funnel/Buying
        Stage slides; Account Engagement's Leads figure reflects
        whatever window main.py scoped it to for the selected mode."""

        accounts = self.trending_accounts

        targeted = len(accounts)
        reached = (accounts["Reached"] == "Yes").sum()

        sales_ready = accounts["Predictive Buying Stage"].isin(
            ["Consideration", "Decision"]
        ).sum()

        reach_to_engage_pct = round(reached / targeted * 100, 1) if targeted else 0

        engagement = self.account_engagement

        # Deliberately the same expression build_funnel_table() uses for its
        # "Reached (All Accounts)" figure, so this average's denominator is
        # always exactly the number the funnel slide shows as reached. The
        # caption below names that figure rather than saying "per account",
        # which invited it to be read against the 371 lead-generating accounts
        # quoted elsewhere in the deck -- a different, smaller universe.
        unique_accounts = engagement["Account Name"].nunique()
        total_leads = engagement["Leads"].sum()

        avg_leads_per_account = (
            round(total_leads / unique_accounts, 2) if unique_accounts else 0
        )

        self.tables["Value Add Metrics"] = pd.DataFrame([
            {
                "Metric": "Accounts Identified",
                "Value": f"{targeted:,}",
                "Caption": "Accounts identified via intent & trending signals",
            },
            {
                "Metric": "Accounts Engaged",
                "Value": f"{reached:,}",
                "Caption": f"Accounts actively engaged ({reach_to_engage_pct}% reach-to-engage)",
            },
            {
                "Metric": "Sales-Ready Accounts",
                "Value": f"{sales_ready:,}",
                "Caption": "Accounts in Consideration + Decision – sales-ready",
            },
            {
                "Metric": "Avg Leads Per Account",
                "Value": f"{avg_leads_per_account}",
                "Caption": f"Avg. leads across the {unique_accounts:,} accounts reached",
            },
        ])

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

        # "Overall" always reflects the true full campaign (self.leads
        # is scoped to just the selected window in Quarterly/Custom
        # modes) -- name_a/name_b below intentionally keep reading from
        # the scoped a/b, since those columns are about the 2 selected
        # periods specifically, not the whole campaign.
        leads = self.leads_full

        name_a, a, name_b, b = self._period_columns()

        rows.append({
            "Metric": "Campaign Start",
            "Overall": leads["Date"].min().strftime("%d-%b-%Y"),
            name_a: "",
            name_b: ""
        })

        rows.append({
            "Metric": "Campaign End",
            "Overall": leads["Date"].max().strftime("%d-%b-%Y"),
            name_a: "",
            name_b: ""
        })

        rows.append({
            "Metric": "Assets Used",
            "Overall": leads["Asset Name"].nunique(),
            name_a: a["Asset Name"].nunique(),
            name_b: b["Asset Name"].nunique()
        })

        rows.append({
            "Metric": "Job Titles",
            "Overall": leads["Job Title"].nunique(),
            name_a: a["Job Title"].nunique(),
            name_b: b["Job Title"].nunique()
        })

        rows.append({
            "Metric": "Countries",
            "Overall": leads["Country"].nunique(),
            name_a: a["Country"].nunique(),
            name_b: b["Country"].nunique()
        })

        self.tables["Campaign Snapshot"] = pd.DataFrame(rows)