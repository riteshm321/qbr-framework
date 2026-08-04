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

        identity = content_cache.build_identity(self.period_meta)

        if identity is None:

            # No analytics payload to fingerprint, so this run can't be
            # identified. Generate, but don't record it under a key that might
            # not describe it.
            print("\n[AI CACHE] run not identifiable - generating without caching\n")
            return self.ai.run()

        if not content_cache.is_cacheable():

            print(
                f"\n[AI CACHE] {config.REPORT_MODE} mode is not cached "
                f"(see config.AI_CACHE_MODES) - generating fresh\n"
            )
            return self.ai.run()

        print()

        if config.AI_FORCE_REGENERATE:
            print("  [AI CACHE] AI_FORCE_REGENERATE is on - ignoring any cached entry")

        else:
            cached = content_cache.load(identity)

            if cached is not None:
                print()
                return cached

            print(f"  [AI CACHE] MISS {content_cache.describe(identity)}")

        ai_json = self.ai.run()

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

        q1_analysis = ai_json.get("Q1Analysis", {})

        self.presentation.ai["q1_analysis"] = q1_analysis.get(
            "summary",
            ""
        )

        q2_analysis = ai_json.get("Q2Analysis", {})

        self.presentation.ai["q2_analysis"] = q2_analysis.get(
            "summary",
            ""
        )

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

        executive_conclusion = ai_json.get(
            "ExecutiveConclusion",
            {}
        )

        self.presentation.ai["executive_conclusion"] = executive_conclusion.get(
            "summary",
            ""
        )

        self.presentation.ai["speaker_notes"] = ai_json.get(
            "Speaker_Notes",
            ""
        )

        return self.presentation