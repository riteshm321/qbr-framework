from engine.presentation_data import PresentationData
from ai.ai_engine import AIEngine
from ai import content_cache

import config


class StoryBuilder:

    def __init__(self, period_meta=None):

        self.presentation = PresentationData()

        self.ai = AIEngine()

        # Needed to identify which period this run covers, so its AI content
        # is cached separately from the same campaign's other periods.
        self.period_meta = period_meta or {}

    # ------------------------------------------------

    def _resolve_content(self):

        """
        The AI narrative for this exact client + campaign + period + dataset,
        generating it only when there's nothing cached for that combination.

        Reuse is scoped deliberately tightly. Reusing across clients was the
        old behaviour and put one client's narrative into another's deck;
        reusing across datasets would leave the text quoting figures that
        disagree with the charts beside it.
        """

        # Built once and used for both the cache fingerprint and the API call,
        # so the key always describes the exact prompt that produced the
        # content it is stored against.
        prompt = self.ai.builder.build()

        identity = content_cache.build_identity(self.period_meta, prompt)

        if identity is None:

            # Nothing to fingerprint, so this run can't be identified.
            # Generate, but don't record it under a key that might not
            # describe it.
            print("\n[AI CACHE] run not identifiable - generating without caching\n")
            return self.ai.run(prompt=prompt)

        if not content_cache.is_cacheable():

            print(
                f"\n[AI CACHE] {config.REPORT_MODE} mode is not cached "
                f"(see config.AI_CACHE_MODES) - generating fresh\n"
            )
            return self.ai.run(prompt=prompt)

        print()

        if config.AI_FORCE_REGENERATE:
            print("  [AI CACHE] AI_FORCE_REGENERATE is on - ignoring any cached entry")

        else:
            cached = content_cache.load(identity)

            if cached is not None:
                print()
                return cached

            print(f"  [AI CACHE] MISS {content_cache.describe(identity)}")

        ai_json = self.ai.run(prompt=prompt)

        if ai_json is not None:
            content_cache.store(identity, ai_json, self.ai.provider)

        return ai_json

    # ------------------------------------------------

    def build(self):

        ai_json = self._resolve_content()

        if ai_json is None:
            return self.presentation

        executive_summary = ai_json.get("ExecutiveSummary", {})

        self.presentation.ai["executive_summary"] = executive_summary.get(
            "long",
            ""
        )

        campaign_overview = ai_json.get("CampaignOverview", {})

        self.presentation.ai["campaign_overview"] = campaign_overview.get(
            "summary",
            ""
        )

        # Per-period commentary, keyed by the period's own label ("Q2 2025",
        # "May", "Full Campaign"). Replaces the old fixed Q1Analysis /
        # Q2Analysis pair, which could only ever fill the first two period
        # slides -- every additional period's insight box was left showing
        # the template's example text.
        period_analysis = {}

        for entry in ai_json.get("PeriodAnalysis", []) or []:

            if not isinstance(entry, dict):
                continue

            label = (entry.get("period") or "").strip()

            if label:
                period_analysis[label] = entry.get("summary", "")

        self.presentation.ai["period_analysis"] = period_analysis

        self.presentation.ai["comparison"] = ai_json.get(
            "Comparison",
            {}
        )

        self.presentation.ai["recommendations"] = ai_json.get(
            "Recommendations",
            {}
        )

        self.presentation.ai["optimization"] = ai_json.get(
            "Optimization",
            {}
        )

        value_add = ai_json.get("ValueAdd", {})

        self.presentation.ai["value_add"] = value_add.get(
            "summary",
            ""
        )

        self.presentation.ai["value_add_heading"] = value_add.get(
            "heading",
            ""
        )

        # Sections backing the slide commentary boxes (trend, content, topics,
        # funnel, intent, optimization, learnings, partnership).
        for key, section in (
            ("trend_analysis", "TrendAnalysis"),
            ("content_performance", "ContentPerformance"),
            ("audience_interest", "AudienceInterest"),
            ("geography", "Geography"),
            ("engagement", "Engagement"),
            ("top_accounts", "TopAccounts"),
            ("optimization_highlights", "OptimizationHighlights"),
            ("key_learnings", "KeyLearnings"),
            ("partnership", "Partnership"),
        ):

            value = ai_json.get(section, {})

            self.presentation.ai[key] = value if isinstance(value, dict) else {}

        executive_conclusion = ai_json.get(
            "ExecutiveConclusion",
            {}
        )

        self.presentation.ai["executive_conclusion"] = executive_conclusion.get(
            "summary",
            ""
        )

        # The schema asks for "SpeakerNotes": {"notes": "..."}, but this read
        # "Speaker_Notes" and expected a bare string -- so speaker notes were
        # always empty regardless of what the model returned.
        speaker_notes = ai_json.get("SpeakerNotes", {})

        if isinstance(speaker_notes, dict):
            speaker_notes = speaker_notes.get("notes", "")

        self.presentation.ai["speaker_notes"] = speaker_notes

        return self.presentation