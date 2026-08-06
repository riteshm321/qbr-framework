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

from datetime import datetime


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


def _magnitude(value):

    """An adverb sized to the change, so a 3% drift and a 200% expansion don't
    get described in identical language. Bands are deliberately wide -- the
    exact figure is always printed alongside, so this only has to set tone."""

    size = abs(_num(value))

    if size == 0:
        return ""

    if size < 5:
        return "marginally"

    if size < 25:
        return "moderately"

    if size < 75:
        return "sharply"

    return "dramatically"


def _movement(value):

    """"fell sharply" / "grew moderately" / "held flat" -- the direction and
    its magnitude as one phrase."""

    word = _direction(value)

    adverb = _magnitude(value)

    if not adverb or word == "held flat":
        return word

    return f"{word} {adverb}"


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


def _agrees(count, singular, plural=None):

    """Just the word, agreeing with `count` -- for sentences that already
    print the number somewhere else ("3 smaller markets", "Spain sits")."""

    return singular if count == 1 else (plural or f"{singular}s")


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

    # --------------------------------------------------------
    # Derived observations
    #
    # The difference between narrative that describes and narrative that
    # informs. Each observation is a thing worth pointing out that is NOT
    # simply a figure already printed on the slide -- a divergence between two
    # metrics, where a trajectory turned, whether concentration is a risk,
    # which funnel step actually leaks. Every one is guarded so it only
    # appears when the data genuinely supports it, so a campaign with a clean
    # growth story and one in trouble surface completely different points.
    #
    # Sections draw from this ranked list rather than each re-deriving its
    # own, which is what keeps the executive summary, key learnings and
    # conclusion consistent with one another.
    # --------------------------------------------------------

    def _observations(self):

        found = []

        status = {r.get("Metric"): r for r in self.metric_status}

        leads = status.get("Total Leads")
        accounts = status.get("Unique Accounts")

        lead_pct = _num(leads.get("% Change")) if leads else None
        account_pct = _num(accounts.get("% Change")) if accounts else None

        # 1. Reach and volume moving in opposite directions is the single most
        #    diagnostic thing a lead-gen campaign can show: it separates "not
        #    enough audience" from "audience isn't converting".
        if lead_pct is not None and account_pct is not None:

            if lead_pct < 0 < account_pct:
                found.append((
                    100,
                    "Reach outpaced conversion",
                    f"Account reach grew {_abs_pct(account_pct)} while lead volume "
                    f"fell {_abs_pct(lead_pct)}, so the audience is widening faster "
                    "than it converts.",
                ))

            elif account_pct < 0 < lead_pct:
                found.append((
                    100,
                    "Depth beat breadth",
                    f"Lead volume grew {_abs_pct(lead_pct)} even as account reach "
                    f"fell {_abs_pct(account_pct)}, so existing accounts are "
                    "converting harder.",
                ))

            elif lead_pct < 0 and account_pct < 0:
                found.append((
                    95,
                    "Volume and reach both softened",
                    f"Leads fell {_abs_pct(lead_pct)} and accounts "
                    f"{_abs_pct(account_pct)} together, pointing at supply rather "
                    "than conversion.",
                ))

            elif lead_pct > 0 and account_pct > 0:
                found.append((
                    95,
                    "Growth on both fronts",
                    f"Leads grew {_abs_pct(lead_pct)} and account reach "
                    f"{_abs_pct(account_pct)}, so volume and audience compounded "
                    "together.",
                ))

        # 2. Where the peak sits tells you whether this is a campaign losing
        #    steam, warming up, or still climbing -- three very different
        #    conversations to have with a client.
        entries = [e for e in self.breakdown if e.get("Total Leads") is not None]

        if len(entries) >= 3:

            peak = max(entries, key=lambda e: _num(e.get("Total Leads")))
            position = entries.index(peak)

            if position == len(entries) - 1:
                found.append((
                    90,
                    "Momentum is building",
                    f"{peak['Period']} was the strongest period yet, so the "
                    "campaign is still climbing.",
                ))

            elif position == 0:
                found.append((
                    90,
                    "Front-loaded performance",
                    f"{peak['Period']} opened as the strongest period and nothing "
                    "since has matched it.",
                ))

            else:
                found.append((
                    90,
                    f"{peak['Period']} was the turning point",
                    f"Volume peaked in {peak['Period']} at "
                    f"{_count(peak.get('Total Leads'))} leads and has trended down "
                    "since.",
                ))

        # 2b. A partial first or last period is the most common way a QBR
        #     misreads itself: fewer days looks identical to weaker performance
        #     on a bar chart. Ranked high because it changes how every other
        #     comparison on the deck should be read.
        partial = [
            e.get("Period") for e in self.breakdown
            if e.get("Partial Period")
        ]

        if partial and entries:

            lowest = min(entries, key=lambda e: _num(e.get("Total Leads")))

            if lowest.get("Partial Period"):
                found.append((
                    93,
                    "The lowest period is a partial one",
                    f"{lowest['Period']} covers only part of its calendar period, "
                    "so its lower total reflects fewer days rather than weaker "
                    "performance.",
                ))
            else:
                found.append((
                    72,
                    "Some periods are partial",
                    f"{_join_and(partial)} cover only part of their calendar "
                    "period, so their totals are not directly comparable.",
                ))

        # 3. Periods with no data at all are easy to miss on a chart that
        #    simply omits them, and they change how every average reads.
        gaps = self._coverage_gaps()

        if gaps:
            found.append((
                85,
                "Coverage had gaps",
                f"{_join_and(gaps)} produced no leads at all, so activity was not "
                "continuous across the period.",
            ))

        # 4. Concentration risk -- one asset carrying the campaign is fragile
        #    even when the headline numbers look healthy.
        top_asset, top_share = self._top_asset_share()

        if top_share is not None and top_share >= 30:
            found.append((
                80,
                "One asset carries the campaign",
                f"'{top_asset}' alone drives {top_share:.1f}% of all leads, so "
                "performance depends heavily on a single piece of content.",
            ))

        elif top_share is not None and top_share <= 20:
            found.append((
                60,
                "Content load is well spread",
                f"No single asset exceeds {top_share:.1f}% of leads, so no one "
                "piece of content is carrying undue weight.",
            ))

        # 5. Which funnel step leaks hardest is where the next intervention
        #    should go, and it is not always the obvious one.
        conversion = _rows_by(self.package.get("Account Conversion", []) or [], "Conversion")

        reach_rate = conversion.get("Reached / Targeted", {}).get("Rate")
        engage_rate = conversion.get("Engaged / Reached", {}).get("Rate")

        if reach_rate is not None and engage_rate is not None:

            if _num(engage_rate) < _num(reach_rate):
                found.append((
                    75,
                    "Engagement is the bottleneck",
                    f"{reach_rate}% of targeted accounts were reached but only "
                    f"{engage_rate}% of those engaged, so contact is easier than "
                    "interest.",
                ))
            else:
                found.append((
                    75,
                    "Reach is the bottleneck",
                    f"Only {reach_rate}% of targeted accounts were reached, yet "
                    f"{engage_rate}% of those engaged once contacted.",
                ))

        # 6. A large ready-now pool is the most actionable thing in the deck,
        #    and it is worth sizing as a share rather than a bare count.
        ready, ready_share = self._sales_ready_share()

        if ready:
            share_text = f", {ready_share:.0f}% of those identified" if ready_share else ""

            found.append((
                70,
                "A sales-ready pool is waiting",
                f"{ready} accounts already sit in Consideration or Decision"
                f"{share_text}, ready for outreach now.",
            ))

        # 7. Breadth expanding across several dimensions at once is a real
        #    finding, distinct from any single metric's movement.
        growth = [
            r["Metric"].lower() for r in self.metric_status
            if _num(r.get("% Change")) > 0
        ]

        if len(growth) >= 3:
            found.append((
                65,
                "Breadth expanded on every front",
                f"{_lead_upper(_join_and(growth))} all grew together, widening "
                "the campaign's footprint.",
            ))

        found.sort(key=lambda item: -item[0])

        return [
            {"title": title, "detail": detail}
            for _, title, detail in found
        ]

    def _coverage_gaps(self):

        """Months inside the reporting window that produced no leads at all.

        DateEngine skips an empty month entirely, so it never reaches the
        breakdown -- a gap can only be found by diffing what the window
        implies against what is actually present.

        Chronology comes from each period's real Start date rather than from
        ordering month names, because a campaign that crosses a year boundary
        (say May 2025 to January 2026) has "January" sorting before "May" by
        name while falling after it in time. Comparing (year, month) pairs
        makes that case work instead of having to bail out of it.

        Returns nothing for modes whose periods aren't months -- a missing
        quarter is a different, much less likely observation, and inferring
        one from quarter labels isn't worth the risk of being wrong.
        """

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        dated = []

        for entry in self.breakdown:

            if entry.get("Period") not in month_names or not entry.get("Start"):
                continue

            try:
                start = datetime.strptime(entry["Start"], "%d %b %Y")

            except (ValueError, TypeError):
                # An unexpected date format means we can't establish
                # chronology safely, so make no claim about gaps.
                return []

            dated.append((start.year, start.month))

        if len(dated) < 2:
            return []

        dated.sort()

        present = set(dated)

        year, month = dated[0]
        end_year, end_month = dated[-1]

        gaps = []

        while (year, month) < (end_year, end_month):

            month += 1

            if month > 12:
                month = 1
                year += 1

            if (year, month) >= (end_year, end_month):
                break

            if (year, month) not in present:
                gaps.append(month_names[month - 1])

        return gaps

    def _top_asset_share(self):

        contribution = self.package.get("Asset Contribution", []) or []

        if not contribution:
            return None, None

        top = max(contribution, key=lambda r: _num(r.get("Contribution %")))

        return top.get("Asset Name"), _num(top.get("Contribution %"))

    def _sales_ready_share(self):

        by_metric = self._value_add_lookup()

        ready = by_metric.get("Sales-Ready Accounts", {}).get("Value")
        identified = by_metric.get("Accounts Identified", {}).get("Value")

        if not ready:
            return None, None

        def as_number(text):
            try:
                return float(str(text).replace(",", ""))
            except (TypeError, ValueError):
                return 0

        ready_n = as_number(ready)
        identified_n = as_number(identified)

        share = (ready_n / identified_n * 100) if identified_n else None

        return ready, share

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
        assets = self._overall("Assets Used")

        short = (
            f"{_count(leads)} leads from {_count(accounts)} accounts "
            f"across {_count(countries)} countries."
        )

        range_text = self.reporting_period.get("Overall Range", "")

        # Opens with the scale of what was delivered, then hands straight to
        # the sharpest observation rather than listing every metric's movement
        # -- an executive summary that recites the metrics table adds nothing
        # the reader cannot already see.
        opening = (
            f"The campaign delivered {_count(leads)} leads from "
            f"{_count(accounts)} unique accounts"
            + (f" across {_count(countries)} countries" if countries else "")
            + (f", {range_text}" if range_text else "")
            + "."
        )

        observations = self._observations()

        long_parts = [opening]

        for observation in observations[:2]:
            long_parts.append(observation["detail"])

        # Distinct facts, not a restatement of the paragraph above.
        bullets = []

        if assets:
            bullets.append(
                f"{_count(assets)} assets in market reaching "
                f"{_count(self._overall('Job Titles'))} distinct job titles."
            )

        for observation in observations[:3]:
            bullets.append(f"{observation['title']}.")

        return {
            "short": short,
            "long": " ".join(long_parts),
            "bullets": bullets[:4],
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

        bullets = []

        # Averages give the reader a sense of scale per period that the totals
        # alone don't -- and immediately show how uneven delivery was.
        volumes = [
            _num(e.get("Total Leads")) for e in self.breakdown
            if e.get("Total Leads") is not None
        ]

        if len(volumes) > 1:
            average = sum(volumes) / len(volumes)

            bullets.append(
                f"{len(volumes)} periods analysed, averaging "
                f"{_count(average)} leads each."
            )

            spread = max(volumes) - min(volumes)

            if average and spread / average > 0.5:
                bullets.append(
                    f"Delivery was uneven, ranging from {_count(min(volumes))} "
                    f"to {_count(max(volumes))} leads per period."
                )

        elif assets:
            bullets.append(
                f"Delivered through {_count(assets)} assets across the period."
            )

        if peak is not None and last is not None and peak["Period"] != last["Period"]:
            bullets.append(
                f"Volume peaked in {peak['Period']} and closed at "
                f"{_count(last.get('Total Leads'))} leads in {last['Period']}."
            )

        return {"summary": summary, "bullets": bullets[:3]}

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

        # Names the metrics on each side rather than saying "and related
        # metrics", which was vague and could imply a grouping the data
        # doesn't actually support.
        if decline and growth:
            headline = (
                f"{_lead_upper(_join_and([r['Metric'].lower() for r in growth]))} "
                f"grew while {_join_and([r['Metric'].lower() for r in decline])} "
                "declined."
            )
        elif decline:
            headline = "Every tracked metric declined across the periods compared."
        elif growth:
            headline = "Every tracked metric grew across the periods compared."
        else:
            headline = "Metrics held broadly flat across the periods compared."

        # The summary interprets; the bullets carry the two headline figures.
        # Bullet 1 must stay the overall line and bullets 2 and 3 must cover
        # Total Leads then Unique Accounts in that order -- they sit directly
        # under those two percentage figures on the slide.
        summary = headline

        observations = self._observations()

        if observations:
            summary = observations[0]["detail"]

        bullets = [headline]

        for metric in ("Total Leads", "Unique Accounts"):

            row = self._status_row(metric)

            if row is None:
                continue

            bullets.append(
                f"{metric} {_movement(row.get('% Change'))} by "
                f"{_abs_pct(row.get('% Change'))} across the periods compared."
            )

        return {
            "summary": summary,
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

        recommended = [row for row in status if row.get("Recommendation")]

        summary = (
            "Convert existing reach before growing it further."
            if any(_num(r.get("% Change")) < 0 for r in status)
            else "Sustain current momentum across every metric."
        )

        geographic = self._geographic_action()

        if geographic:

            # The "Countries" metric row generates its own recommendation
            # ("evaluate geographic expansion opportunities"), which says
            # loosely what the geographic action below says with the actual
            # markets named. Keeping both puts two geography lines on a
            # six-line slide, so the vaguer one gives way.
            recommended = [
                row for row in recommended
                if row.get("Metric") != "Countries"
            ]

        actions = [row["Recommendation"] for row in recommended][:5]

        # The geographic action always lands last: it is an addition to the
        # metric-driven recommendations above it, not a replacement for any of
        # them. Omitted entirely when the campaign has no market spread to act
        # on, rather than padded with a generic line.
        geographic = self._geographic_action()

        if geographic:
            actions.append(geographic)

        return {"summary": summary, "actions": actions}

    def _geographic_action(self):

        """What to do next about where the campaign sells.

        Three genuinely different situations, three different actions:
        concentrated delivery calls for widening, a proven mid-tier calls for
        scaling into it, and an even spread calls for defending it.
        """

        real, top, top_two = self._markets()

        if top is None or len(real) < 2:
            return ""

        growth = [
            str(r.get("Country")) for r in real
            if str(r.get("Tier")) == "Growth Opportunity"
        ]

        if growth:
            return (
                f"Scale spend into {_join_and(growth)}, already delivering at "
                "proven rates with the most headroom left of any market."
            )

        if top_two >= 70:
            return (
                f"Widen beyond {str(top.get('Country'))}, which carries "
                f"{_num(top.get('Share %')):.1f}% of delivery and leaves the "
                "campaign exposed to a single market."
            )

        return (
            f"Hold the current spread across {_plural(len(real), 'market')} "
            "and test one adjacent territory before committing further budget."
        )

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
    # Geography
    # --------------------------------------------------------

    def _markets(self):

        """
        The country rows that name an actual place, plus the leading one and
        the top-two concentration.

        "Other (N countries)" is a combined remainder, never a market: it can't
        be called the leader, counted as somewhere to expand into, or named in
        a sentence about where demand sits.

        Returns (real_rows, top_row, top_two_share), with top_row None when the
        campaign has no usable country data.
        """

        rows = self.package.get("Country Distribution", []) or []

        real = [
            r for r in rows
            if not str(r.get("Country", "")).startswith("Other (")
        ]

        if not real:
            return [], None, 0.0

        return real, real[0], sum(_num(r.get("Share %")) for r in real[:2])

    def geography(self):

        """
        The market breakdown, written to the lengths the geography slides need
        rather than to the short-card lengths the other sections use: the
        heading is a full lead-in line above a row of market cards, and the
        first bullet sits alone in a wide panel.
        """

        real, top, top_two = self._markets()

        if top is None:
            return {
                "heading": "No country-level data available for this campaign.",
                "bullets": [],
            }

        total = sum(_num(r.get("Leads")) for r in
                    (self.package.get("Country Distribution", []) or []))

        names = [str(r.get("Country")) for r in real]

        top_share = _num(top.get("Share %"))

        # How the rest of the footprint reads once the leader is set aside --
        # a strong second market and a long thin tail are different stories
        # and deserve different sentences.
        if len(real) == 1:
            spread = (
                f"{names[0]} is the campaign's only named market, so every "
                "further lead has to come from somewhere new."
            )
        elif len(real) == 2:
            spread = (
                f"{names[1]} carries the remainder at "
                f"{_num(real[1].get('Share %')):.1f}%, leaving the campaign "
                "resting on two markets."
            )
        else:
            spread = (
                f"{names[1]} is the strongest secondary market and "
                f"{_join_and(names[2:])} make up the emerging tail."
            )

        heading = (
            f"{_count(total)} delivered leads spread across "
            f"{_plural(len(real), 'market')}, with "
            f"{names[0]} taking {top_share:.1f}%. {spread}"
        )

        # Bullet 1 is the wide panel under the market KPIs: concentration, and
        # what that leaves to play for.
        if len(real) > 1:

            headline = (
                f"{names[0]} and {names[1]} together take {top_two:.1f}% of "
                f"delivered leads"
            )

            remainder = len(real) - 2

            if remainder:
                headline += (
                    f", leaving {100 - top_two:.1f}% across "
                    f"{remainder} smaller {_agrees(remainder, 'market')} "
                    "where there is room to grow."
                )
            else:
                headline += (
                    ", so widening the footprint is the clearest route to "
                    "further growth."
                )

        else:
            headline = (
                f"{names[0]} accounts for effectively all delivery, so any "
                "meaningful growth has to come from opening a second market."
            )

        bullets = [headline]

        bullets.append(
            f"{names[0]} delivered {_count(top.get('Leads'))} leads at "
            f"{top_share:.1f}% of the total, setting the benchmark every "
            "other market is measured against."
        )

        # The forward-looking read: whichever markets are big enough to scale
        # but small enough to have headroom.
        growth = [
            r for r in real
            if str(r.get("Tier")) == "Growth Opportunity"
        ]

        if growth:
            bullets.append(
                f"{_join_and([str(r.get('Country')) for r in growth])} "
                f"{_agrees(len(growth), 'sits', 'sit')} in the growth tier, "
                "already proven and with the most headroom left to take."
            )
        elif top_two >= 70:
            bullets.append(
                f"With {top_two:.1f}% of volume in two markets, the footprint "
                "is concentrated enough that a single market's dip would show "
                "in the campaign total."
            )
        else:
            bullets.append(
                f"Volume is spread evenly enough across "
                f"{_plural(len(real), 'market')} that no single one carries "
                "disproportionate risk for the campaign."
            )

        return {"heading": heading, "bullets": bullets[:3]}

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

        # Straight from the ranked observations -- this slide exists to say
        # what the campaign taught us, which is exactly what an observation
        # is. Topping up from the metrics table only if fewer than five
        # observations fired (a very short or very flat campaign).
        items = [
            {"title": observation["title"], "detail": observation["detail"]}
            for observation in self._observations()
        ]

        if len(items) < 5:

            existing = {item["title"] for item in items}

            for row in self._sorted_status():

                title = f"{row['Metric']} {_direction(row.get('% Change'))}"

                if title in existing:
                    continue

                items.append({
                    "title": title,
                    "detail": f"{row['Metric']} {_movement(row.get('% Change'))} by "
                              f"{_abs_pct(row.get('% Change'))} across the periods "
                              "compared.",
                })

                if len(items) >= 5:
                    break

        items = items[:5]

        # Geography last, for the same reason as the geographic
        # recommendation: it adds to the campaign's learnings rather than
        # displacing one of them.
        geographic = self._geographic_learning()

        if geographic:
            items.append(geographic)

        return {"items": items}

    def _geographic_learning(self):

        """What the spread of markets taught us.

        Reads the same three situations as _geographic_action(), but states
        what is true rather than what to do -- the two slides sit pages apart
        and would read as a repeat if they said the same thing.
        """

        real, top, top_two = self._markets()

        if top is None or len(real) < 2:
            return None

        country = str(top.get("Country"))

        if top_two >= 70:
            return {
                "title": "Demand is geographically narrow",
                "detail": (
                    f"{country} and {str(real[1].get('Country'))} carry "
                    f"{top_two:.1f}% of delivery, so the campaign's total "
                    "tracks two markets rather than its whole footprint."
                ),
            }

        growth = [
            str(r.get("Country")) for r in real
            if str(r.get("Tier")) == "Growth Opportunity"
        ]

        if growth:
            return {
                "title": "Secondary markets are proving out",
                "detail": (
                    f"{_join_and(growth)} {_agrees(len(growth), 'is', 'are')} "
                    "delivering at a scale that justifies treating "
                    f"{_agrees(len(growth), 'it', 'them')} as core rather "
                    "than experimental."
                ),
            }

        return {
            "title": "The footprint is genuinely balanced",
            "detail": (
                f"Delivery spreads across {_plural(len(real), 'market')} with "
                f"{country} only reaching {_num(top.get('Share %')):.1f}%, so "
                "no single territory carries the campaign."
            ),
        }

    # --------------------------------------------------------
    # ExecutiveConclusion / SpeakerNotes
    # --------------------------------------------------------

    def executive_conclusion(self):

        """The closing "so what".

        Every clause is derived from the actual mix of movements. An earlier
        version opened with a fixed "Reach expanded while N metrics declined",
        which contradicted itself on a campaign where everything declined
        (reach had not expanded) and asserted growth on a single-period run
        that had no comparison data to support any claim at all.
        """

        status = self._sorted_status()

        decline = [r for r in status if _num(r.get("% Change")) < 0]
        growth = [r for r in status if _num(r.get("% Change")) > 0]

        sales_ready, _ = self._sales_ready_share()

        # The action half of the sentence -- always the most concrete next
        # step available, falling back progressively.
        if sales_ready:
            action = (
                f"converting the {sales_ready} sales-ready accounts is the "
                "clearest next step"
            )
        else:
            action = "converting existing reach into pipeline is the next priority"

        # The assessment half, strictly from what the comparison shows.
        if not status:
            assessment = "With a single period analysed there is no prior period to compare against"

        elif decline and growth:
            assessment = (
                f"{_lead_upper(_join_and([r['Metric'].lower() for r in growth]))} "
                f"grew while {_join_and([r['Metric'].lower() for r in decline])} fell"
            )

        elif decline:
            assessment = f"All {len(decline)} tracked metrics declined"

        else:
            assessment = f"All {len(growth)} tracked metrics grew"

        return {"summary": f"{assessment}; {action}."}

    def speaker_notes(self):

        """A talk track, not a metrics recital.

        These notes are for whoever presents the deck, so they say what to
        lead with, what to be ready to be challenged on, and where to land --
        the figures are already on the slides, and repeating them here in a
        flat list gives the presenter nothing to work with.
        """

        leads = self._overall("Total Leads")
        accounts = self._overall("Unique Accounts")

        observations = self._observations()

        notes = [
            f"Open with the scale: {_count(leads)} leads from "
            f"{_count(accounts)} accounts, "
            f"{self.reporting_period.get('Overall Range', 'the period analysed')}."
        ]

        if observations:
            notes.append(f"Lead on this: {_lead_lower(observations[0]['detail'])}")

        # Declines are what a client will interrupt about, so name them ahead
        # of time rather than leaving the presenter to find them mid-slide.
        decline = [
            r for r in self._sorted_status()
            if _num(r.get("% Change")) < 0
        ]

        if decline:
            names = _join_and([r["Metric"].lower() for r in decline])

            notes.append(
                f"Expect questions on {names} -- address the drop directly "
                "rather than leading with the positives."
            )
        else:
            notes.append(
                "Every tracked metric moved in the right direction, so the "
                "conversation can focus on where to scale next."
            )

        gaps = self._coverage_gaps()

        if gaps:
            notes.append(
                f"Flag {_join_and(gaps)} as having no recorded activity before "
                "anyone spots the gap on the chart."
            )

        ready, _ = self._sales_ready_share()

        if ready:
            notes.append(
                f"Close on the {ready} sales-ready accounts -- that is the "
                "concrete next step to agree in the room."
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
            "Geography": self.geography(),
            "Engagement": self.engagement(),
            "TopAccounts": self.top_accounts(),
            "OptimizationHighlights": self.optimization_highlights(),
            "KeyLearnings": self.key_learnings(),
            "Partnership": self.partnership(),
            "ExecutiveConclusion": self.executive_conclusion(),
            "SpeakerNotes": self.speaker_notes(),
        }
