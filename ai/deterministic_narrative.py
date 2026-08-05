"""
Deterministic Narrative Builder

Produces the exact JSON schema the AI providers return (see
ai/prompt_builder.py), computed directly from qbr_package.json instead of an
LLM call. No network, no API key, no quota -- this is what lets the tool
generate a full narrative deck forever, for any client, on any machine.

This is not a stub. Every section that build_narrative() fills reads real
figures out of the payload and branches on what they say (which period peaked,
which metrics declined, how concentrated the top asset is) so two campaigns
with different data produce different text -- the same guarantee the prompt
places on the AI providers, just reached by arithmetic instead of a call.

Nothing here invents a number. Every value comes from the payload; a section
with nothing to say (e.g. no trending topics for this campaign) says so
explicitly rather than fabricating content.
"""


# ------------------------------------------------------------
# Small formatting helpers
# ------------------------------------------------------------

def _num(value, default=0):

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _count(value):

    try:
        return f"{int(round(_num(value))):,}"

    except (TypeError, ValueError):
        return str(value)


def _pct(value):

    """Matches the style already used elsewhere in this deck's own generated
    text ("+200.0%", "-41.33%", "+31.58%") -- one decimal for a whole number,
    two otherwise."""

    value = _num(value)

    if value == int(value):
        return f"{value:+.1f}%"

    return f"{value:+.2f}%"


def _abs_pct(value):

    """Magnitude only, no sign -- pairs with _direction() so a decline reads
    as "fell 41.33%", never "fell -41.33%". _pct() keeps the sign for places
    that show a direction word AND signed magnitude separately (there are
    none left after this fix, but _pct() stays available for that case)."""

    return _pct(abs(_num(value))).lstrip("+")


def _direction(value):

    value = _num(value)

    if value > 0:
        return "grew"

    if value < 0:
        return "fell"

    return "held flat"


def _rows_by(rows, key):

    return {row.get(key): row for row in rows if row.get(key) is not None}


def _join_and(items):

    """["A", "B", "C"] -> "A, B and C" -- plain comma joins read as a raw
    list dump ("Saint-Gobain, Omya, Sartorius"), not a sentence."""

    items = [str(i) for i in items if i]

    if not items:
        return ""

    if len(items) == 1:
        return items[0]

    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _plural(count, noun):

    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _lead_lower(text):

    """Lowercases only the first character, so a caption reading
    "Accounts in Consideration + Decision - sales-ready" can open a sentence
    without capitalising mid-sentence, but "Consideration + Decision" -- a
    proper term used elsewhere on the same slide -- keeps its own casing.
    A full .lower() would turn that into "consideration + decision", which
    reads as a typo next to the correctly-cased chart labels beside it."""

    text = str(text or "")

    if not text:
        return text

    return text[0].lower() + text[1:]


def _lead_upper(text):

    """Capitalises only the first character -- the counterpart to
    _lead_lower(), for text built from lowercase metric names that opens its
    own standalone sentence rather than continuing one."""

    text = str(text or "")

    if not text:
        return text

    return text[0].upper() + text[1:]


# ------------------------------------------------------------
# Section builders
# ------------------------------------------------------------

class DeterministicNarrativeBuilder:

    def __init__(self, package):

        self.package = package

        self.reporting_period = package.get("Reporting Period", {}) or {}

        self.breakdown = self.reporting_period.get("Period Breakdown", []) or []

        self.commentary_labels = (
            self.reporting_period.get("Periods Needing Individual Commentary", [])
            or []
        )

        self.metric_status = package.get("Metric Status", []) or []

        self.exec_rows = package.get("Executive Summary", []) or []

    # --------------------------------------------------------

    def _overall(self, kpi):

        row = _rows_by(self.exec_rows, "KPI").get(kpi)

        return None if row is None else row.get("Overall")

    def _status_row(self, metric):

        return _rows_by(self.metric_status, "Metric").get(metric)

    def _sorted_status(self):

        """Metric Status rows ordered by how large a story each tells --
        biggest decline first, so the sections that only have room for a
        few lines lead with what matters most."""

        return sorted(
            self.metric_status,
            key=lambda row: _num(row.get("% Change")),
        )

    def _breakdown_lookup(self, label):

        for entry in self.breakdown:
            if entry.get("Period") == label:
                return entry

        return None

    def _peak_and_last(self, metric):

        """(peak_entry, last_entry) across the granular breakdown, used to
        describe a trajectory ("peaked at X in {period}, then Y by {period}")
        without assuming how many periods there are."""

        entries = [e for e in self.breakdown if e.get(metric) is not None]

        if not entries:
            return None, None

        peak = max(entries, key=lambda e: _num(e.get(metric)))

        return peak, entries[-1]

    # --------------------------------------------------------
    # ExecutiveSummary
    # --------------------------------------------------------

    def executive_summary(self):

        leads = self._overall("Total Leads")
        accounts = self._overall("Unique Accounts")
        countries = self._overall("Countries")

        short = (
            f"{_count(leads)} leads from {_count(accounts)} accounts "
            f"across {_count(countries)} countries."
        )

        status = self._sorted_status()

        growth = [r for r in status if _num(r.get("% Change")) > 0]
        decline = [r for r in status if _num(r.get("% Change")) < 0]

        range_text = self.reporting_period.get("Overall Range", "")

        long_parts = [
            f"The campaign delivered {_count(leads)} leads from "
            f"{_count(accounts)} unique accounts"
            + (f" across {_count(countries)} countries" if countries else "")
            + (f" between {range_text}" if range_text else "")
            + "."
        ]

        if growth:
            names = ", ".join(r["Metric"].lower() for r in growth[:3])
            long_parts.append(f"Strong growth was seen in {names}.")

        if decline:
            names = " and ".join(r["Metric"].lower() for r in decline[:2])
            pct = min(_num(r.get("% Change")) for r in decline)
            long_parts.append(
                f"However, {names} declined, down as much as {abs(pct):.2f}%, "
                "signaling areas for optimization."
            )

        bullets = [
            f"{_count(leads)} leads delivered from {_count(accounts)} unique accounts.",
        ]

        if growth:
            bullets.append(
                "Strong growth in "
                + ", ".join(r["Metric"].lower() for r in growth[:3])
                + "."
            )

        if decline:
            bullets.append(
                "Decline in "
                + " and ".join(r["Metric"].lower() for r in decline[:2])
                + " needs attention."
            )

        return {
            "short": short,
            "long": " ".join(long_parts),
            "bullets": bullets,
        }

    # --------------------------------------------------------
    # CampaignOverview
    # --------------------------------------------------------

    def campaign_overview(self):

        range_text = self.reporting_period.get("Overall Range", "")

        leads = self._overall("Total Leads")
        accounts = self._overall("Unique Accounts")
        assets = self._overall("Assets Used")
        countries = self._overall("Countries")

        summary = (
            f"A lead generation programme running {range_text}, delivering "
            f"{_count(leads)} leads from {_count(accounts)} accounts across "
            f"{_count(countries)} countries."
        )

        peak, last = self._peak_and_last("Total Leads")

        bullets = [f"{len(self.breakdown)} periods analysed using {_count(assets)} assets."]

        if peak is not None and last is not None:
            if peak["Period"] == last["Period"]:
                bullets.append(
                    f"Volume was highest in the most recent period, {peak['Period']}."
                )
            else:
                bullets.append(
                    f"Volume peaked in {peak['Period']} and moved to "
                    f"{_count(last.get('Total Leads'))} leads by {last['Period']}."
                )

        return {"summary": summary, "bullets": bullets}

    # --------------------------------------------------------
    # PeriodAnalysis
    # --------------------------------------------------------

    def period_analysis(self):

        entries = []

        for label in self.commentary_labels:

            row = self._breakdown_lookup(label)

            if row is None:
                # No granular breakdown row matches this label (e.g. Full
                # Campaign / Custom Period have exactly one commentary slot
                # that doesn't appear in the quarter/month breakdown) -- fall
                # back to the campaign's own overall totals, which always
                # exist.
                leads = self._overall("Total Leads")
                accounts = self._overall("Unique Accounts")
                assets = self._overall("Assets Used")

                summary = (
                    f"{_count(leads)} leads were generated from "
                    f"{_count(accounts)} accounts using {_count(assets)} assets "
                    "across the full period analysed."
                )

                entries.append({"period": label, "summary": summary})
                continue

            leads = row.get("Total Leads")
            accounts = row.get("Unique Accounts")
            assets = row.get("Assets Used")

            # Found by identity rather than assuming commentary_labels and
            # the breakdown share index order -- true today, but this stays
            # correct even if that ever changes.
            idx = next(
                (j for j, e in enumerate(self.breakdown) if e is row), None
            )
            prev = self.breakdown[idx - 1] if idx else None

            trend_phrase = ""

            if prev is not None and prev.get("Total Leads") is not None:

                delta = _num(leads) - _num(prev.get("Total Leads"))

                if delta > 0:
                    trend_phrase = f", up from {_count(prev.get('Total Leads'))} the period before"
                elif delta < 0:
                    trend_phrase = f", down from {_count(prev.get('Total Leads'))} the period before"

            all_leads = [
                _num(e.get("Total Leads")) for e in self.breakdown
                if e.get("Total Leads") is not None
            ]

            standing = ""

            if all_leads and _num(leads) == max(all_leads) and len(all_leads) > 1:
                standing = ", the strongest period recorded"
            elif all_leads and _num(leads) == min(all_leads) and len(all_leads) > 1:
                standing = ", the weakest period recorded"

            summary = (
                f"{label} delivered {_count(leads)} leads from "
                f"{_count(accounts)} accounts using {_count(assets)} assets"
                f"{trend_phrase}{standing}."
            )

            entries.append({"period": label, "summary": summary})

        return entries

    # --------------------------------------------------------
    # Comparison
    # --------------------------------------------------------

    def comparison(self):

        status = self._sorted_status()

        growth = [r for r in status if _num(r.get("% Change")) > 0]
        decline = [r for r in status if _num(r.get("% Change")) < 0]

        if decline and growth:
            headline = (
                f"{growth[-1]['Metric']} and related reach metrics grew while "
                f"{decline[0]['Metric'].lower()} declined."
            )
        elif decline:
            headline = "Every tracked metric declined across the periods compared."
        elif growth:
            headline = "Every tracked metric grew across the periods compared."
        else:
            headline = "Metrics held broadly flat across the periods compared."

        bullets = [headline]

        for metric in ("Total Leads", "Unique Accounts"):

            row = self._status_row(metric)

            if row is None:
                continue

            bullets.append(
                f"{metric} {_direction(row.get('% Change'))} "
                f"{_abs_pct(row.get('% Change'))}."
            )

        return {
            "summary": headline,
            "bullets": bullets[:3],
        }

    # --------------------------------------------------------
    # Optimization / OptimizationHighlights / Recommendations
    #
    # All three reuse the Recommendation text already computed by
    # LeadGenAnalyzer._status_label() (see Metric Status) -- the same text
    # already shown on Table_OptimizationHighlights, so these sections can
    # never disagree with the table beside them.
    # --------------------------------------------------------

    def optimization(self):

        status = self._sorted_status()

        decline = [r for r in status if _num(r.get("% Change")) < 0]
        growth = [r for r in status if _num(r.get("% Change")) > 0]

        summary = (
            f"{_plural(len(decline), 'metric')} declined while "
            f"{_plural(len(growth), 'metric')} grew; converting existing reach "
            "is the priority."
            if decline
            else "Every tracked metric grew; sustaining that pace is the priority."
        )

        bullets = [row["Recommendation"] for row in status[:3] if row.get("Recommendation")]

        return {"summary": summary, "bullets": bullets}

    def optimization_highlights(self):

        status = self._sorted_status()

        decline = [r["Metric"].lower() for r in status if _num(r.get("% Change")) < 0]
        growth = [r["Metric"].lower() for r in status if _num(r.get("% Change")) > 0]

        if decline and growth:
            footer = (
                f"{_join_and(growth)} grew while {_join_and(decline)} declined, "
                "so converting existing reach is the next priority."
            )
        elif decline:
            footer = f"{_join_and(decline)} declined across the periods compared."
        else:
            footer = f"{_join_and(growth)} grew across the periods compared."

        return {"footer": _lead_upper(footer)}

    def recommendations(self):

        status = self._sorted_status()

        actions = [row["Recommendation"] for row in status if row.get("Recommendation")]

        summary = (
            "Convert existing reach before growing it further."
            if any(_num(r.get("% Change")) < 0 for r in status)
            else "Sustain current momentum across every metric."
        )

        return {"summary": summary, "actions": actions[:5]}

    # --------------------------------------------------------
    # ValueAdd / Partnership
    # --------------------------------------------------------

    def _value_add_lookup(self):

        rows = self.package.get("Value Add Metrics", []) or []

        return _rows_by(rows, "Metric")

    def value_add(self):

        by_metric = self._value_add_lookup()

        identified = by_metric.get("Accounts Identified", {})
        engaged = by_metric.get("Accounts Engaged", {})
        sales_ready = by_metric.get("Sales-Ready Accounts", {})

        if identified and engaged:
            heading = (
                f"Beyond core lead delivery, intent signals surfaced "
                f"{identified.get('Value')} accounts and engaged "
                f"{engaged.get('Value')} of them."
            )
        else:
            heading = (
                "Beyond core lead delivery, intent and trending signals "
                "identified and qualified an expanded pool of buying-ready accounts."
            )

        summary_parts = []

        for row in (identified, engaged, sales_ready):

            if row.get("Value") and row.get("Caption"):
                summary_parts.append(f"{row['Value']} {_lead_lower(row['Caption'])}")

        summary = ", ".join(summary_parts) + "." if summary_parts else ""

        return {"heading": heading, "summary": summary, "bullets": []}

    def partnership(self):

        by_metric = self._value_add_lookup()

        identified = by_metric.get("Accounts Identified", {})
        engaged = by_metric.get("Accounts Engaged", {})
        sales_ready = by_metric.get("Sales-Ready Accounts", {})

        sentences = []

        if identified.get("Value"):
            # Not built from the caption here (unlike value_add() above) --
            # that caption already reads "accounts identified via intent &
            # trending signals", so prefixing it with another "identified"
            # would repeat the verb. This states the same fact once.
            sentences.append(
                f"The intent layer identified {identified.get('Value')} accounts "
                "beyond core lead delivery."
            )

        if engaged.get("Value"):
            sentences.append(
                f"{engaged.get('Value')} of those accounts were actively engaged."
            )

        if sales_ready.get("Value"):
            sentences.append(
                f"A further {sales_ready.get('Value')} accounts are already "
                "sales-ready, a qualified pool available for immediate follow-up."
            )

        return {"summary": " ".join(sentences)}

    # --------------------------------------------------------
    # TrendAnalysis
    # --------------------------------------------------------

    def trend_analysis(self):

        rows = self.package.get("Trend Projection", []) or []

        real = [r for r in rows if not r.get("Is Forecast")]
        forecast = [r for r in rows if r.get("Is Forecast")]

        if not real:
            return {"heading": "Insufficient data to project a trend.", "bullets": []}

        peak = max(real, key=lambda r: _num(r.get("Total Leads")))
        last_real = real[-1]

        if forecast:
            direction = _direction(
                _num(forecast[-1].get("Total Leads")) - _num(last_real.get("Total Leads"))
            )
            heading = f"Volume peaked at {peak['Period']} and the projection {direction} beyond {last_real['Period']}."
        else:
            heading = f"Volume peaked at {peak['Period']} across the periods observed."

        bullets = [
            f"Leads peaked at {_count(peak.get('Total Leads'))} in {peak['Period']}, "
            f"ending at {_count(last_real.get('Total Leads'))} by {last_real['Period']}."
        ]

        peak_accounts = max(real, key=lambda r: _num(r.get("Unique Accounts")))

        bullets.append(
            f"Unique accounts peaked at {_count(peak_accounts.get('Unique Accounts'))} "
            f"in {peak_accounts['Period']}."
        )

        if forecast:
            bullets.append(
                f"Projections continue through {forecast[-1]['Period']} on the observed "
                "trend if no action is taken."
            )

        return {"heading": heading, "bullets": bullets[:3]}

    # --------------------------------------------------------
    # ContentPerformance
    # --------------------------------------------------------

    def content_performance(self):

        assets = self.package.get("Asset Performance", []) or []
        contribution = self.package.get("Asset Contribution", []) or []

        if not assets:
            return {"heading": "No asset performance data for this campaign.", "bullets": []}

        top = min(assets, key=lambda r: _num(r.get("Rank", 999)))

        contrib_by_name = _rows_by(contribution, "Asset Name")

        top_contrib = contrib_by_name.get(top.get("Asset Name"), {}).get("Contribution %")

        heading = (
            f"One asset carries {top_contrib:.1f}% of all leads generated."
            if top_contrib
            else f"'{top.get('Asset Name')}' leads all assets on volume."
        )

        bullets = [
            f"'{top.get('Asset Name')}' produced {_count(top.get('Leads'))} leads, "
            f"the most of any asset."
        ]

        if len(assets) > 1:
            bullets.append(
                f"{len(assets)} assets were in market across the period analysed."
            )

        if top_contrib and top_contrib > 25:
            bullets.append(
                f"Concentration is a risk: the top asset alone contributes "
                f"{top_contrib:.1f}% of all leads."
            )
        elif top_contrib:
            bullets.append(
                f"Contribution is well distributed, with the top asset at "
                f"{top_contrib:.1f}% of total leads."
            )

        return {"heading": heading, "bullets": bullets[:3]}

    # --------------------------------------------------------
    # AudienceInterest
    # --------------------------------------------------------

    def audience_interest(self):

        topics = self.package.get("Trending Topics", []) or []
        categories = self.package.get("Topic Categories", []) or []

        if not topics and not categories:
            return {
                "heading": "No trending topic data was captured for this campaign period.",
                "summary": (
                    "Topic-level intent reporting returned no rows for this "
                    "programme, so audience interest cannot be characterised "
                    "from the data available."
                ),
            }

        top_category = max(categories, key=lambda r: _num(r.get("Mentions"))) if categories else None

        if top_category:
            heading = f"'{top_category.get('Category')}' dominates topic mentions."
            summary = (
                f"'{top_category.get('Category')}' accounts for the largest share "
                f"of topic mentions at {_count(top_category.get('Mentions'))}."
            )
        else:
            heading = f"{len(topics)} trending topics identified across the campaign."
            summary = "Topic-level detail is available in the Trending Topics table."

        return {"heading": heading, "summary": summary}

    # --------------------------------------------------------
    # Engagement
    # --------------------------------------------------------

    def engagement(self):

        conversion = _rows_by(self.package.get("Account Conversion", []) or [], "Conversion")

        reached = conversion.get("Reached / Targeted", {}).get("Rate")
        engaged = conversion.get("Engaged / Reached", {}).get("Rate")

        funnel = self.package.get("Account Funnel", []) or []

        by_stage = _rows_by(funnel, "Stage")

        bullets = []

        if reached is not None:
            bullets.append(
                f"{reached}% of targeted accounts identified via intent signals were reached."
            )

        if engaged is not None:
            engaged_count = by_stage.get("Engaged", {}).get("Trending")
            reached_count = by_stage.get("Reached", {}).get("Trending")

            bullets.append(
                f"Only {engaged}% of reached accounts went on to engage"
                + (
                    f", {_count(engaged_count)} of {_count(reached_count)}"
                    if engaged_count is not None and reached_count is not None
                    else ""
                )
                + "."
            )

        if reached is not None and engaged is not None:

            gap_metric = "reach" if reached < engaged else "engagement"

            bullets.append(f"{gap_metric.capitalize()} is the clearer gap to close next.")

        return {"bullets": bullets[:3]}

    # --------------------------------------------------------
    # TopAccounts
    # --------------------------------------------------------

    def top_accounts(self):

        accounts = self.package.get("Top Engaged Accounts", []) or []

        if not accounts:
            return {"footer": "No account engagement data for this campaign."}

        ranked = sorted(accounts, key=lambda r: _num(r.get("Rank", 999)))

        top_names = [r.get("Account Name") for r in ranked[:3] if r.get("Account Name")]

        max_leads = max(_num(r.get("Leads")) for r in accounts)

        footer = (
            f"{_join_and(top_names)} lead engagement, but no single account "
            f"exceeds {_count(max_leads)} leads, so volume is widely distributed."
        )

        return {"footer": footer}

    # --------------------------------------------------------
    # KeyLearnings
    # --------------------------------------------------------

    def key_learnings(self):

        items = []

        status = self._sorted_status()

        if status:

            worst = status[0]
            best = status[-1]

            if _num(worst.get("% Change")) < 0:
                items.append({
                    "title": f"{worst['Metric']} needs attention",
                    "detail": f"{worst['Metric']} {_direction(worst.get('% Change'))} "
                              f"{_abs_pct(worst.get('% Change'))} across the periods compared.",
                })

            if _num(best.get("% Change")) > 0:
                items.append({
                    "title": f"{best['Metric']} is a strength",
                    "detail": f"{best['Metric']} grew {_abs_pct(best.get('% Change'))}, "
                              "the campaign's strongest mover.",
                })

        assets = self.package.get("Asset Performance", []) or []
        contribution = _rows_by(self.package.get("Asset Contribution", []) or [], "Asset Name")

        if assets:

            top = min(assets, key=lambda r: _num(r.get("Rank", 999)))

            top_pct = contribution.get(top.get("Asset Name"), {}).get("Contribution %")

            if top_pct:
                items.append({
                    "title": "One asset dominates",
                    "detail": f"'{top.get('Asset Name')}' alone contributes "
                              f"{top_pct:.1f}% of all leads generated.",
                })

        conversion = _rows_by(self.package.get("Account Conversion", []) or [], "Conversion")

        engaged = conversion.get("Engaged / Reached", {}).get("Rate")

        if engaged is not None:
            items.append({
                "title": "Engagement is the constraint",
                "detail": f"Only {engaged}% of reached accounts went on to engage "
                          "with the campaign's content.",
            })

        by_metric = self._value_add_lookup()

        sales_ready = by_metric.get("Sales-Ready Accounts", {})

        if sales_ready.get("Value"):
            items.append({
                "title": "A sales-ready pool exists",
                "detail": f"{sales_ready.get('Value')} accounts already sit in "
                          "Consideration or Decision, ready for outreach now.",
            })

        return {"items": items[:5]}

    # --------------------------------------------------------
    # ExecutiveConclusion / SpeakerNotes
    # --------------------------------------------------------

    def executive_conclusion(self):

        status = self._sorted_status()

        decline = [r for r in status if _num(r.get("% Change")) < 0]

        by_metric = self._value_add_lookup()

        sales_ready = by_metric.get("Sales-Ready Accounts", {}).get("Value")

        if decline and sales_ready:
            summary = (
                f"Reach expanded while {_plural(len(decline), 'metric')} declined; "
                f"converting the {sales_ready} sales-ready accounts is the "
                "fastest route back to performance."
            )
        elif sales_ready:
            summary = (
                f"Performance grew across every metric; converting the "
                f"{sales_ready} sales-ready accounts is the next opportunity."
            )
        else:
            summary = "The campaign's next priority is converting existing reach into pipeline."

        return {"summary": summary}

    def speaker_notes(self):

        leads = self._overall("Total Leads")
        accounts = self._overall("Unique Accounts")

        status = self._sorted_status()

        notes = [
            f"{_count(leads)} leads from {_count(accounts)} accounts across "
            f"{self.reporting_period.get('Overall Range', '')}."
        ]

        for row in status:
            notes.append(
                f"{row['Metric']} {_direction(row.get('% Change'))} "
                f"{_abs_pct(row.get('% Change'))}."
            )

        return {"notes": " ".join(notes)}

    # --------------------------------------------------------

    def build(self):

        return {
            "ExecutiveSummary": self.executive_summary(),
            "CampaignOverview": self.campaign_overview(),
            "PeriodAnalysis": self.period_analysis(),
            "Comparison": self.comparison(),
            "Optimization": self.optimization(),
            "Recommendations": self.recommendations(),
            "ValueAdd": self.value_add(),
            "TrendAnalysis": self.trend_analysis(),
            "ContentPerformance": self.content_performance(),
            "AudienceInterest": self.audience_interest(),
            "Engagement": self.engagement(),
            "TopAccounts": self.top_accounts(),
            "OptimizationHighlights": self.optimization_highlights(),
            "KeyLearnings": self.key_learnings(),
            "Partnership": self.partnership(),
            "ExecutiveConclusion": self.executive_conclusion(),
            "SpeakerNotes": self.speaker_notes(),
        }
