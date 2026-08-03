from engine.presentation_data import PresentationData
from ai.ai_engine import AIEngine

import json
from pathlib import Path
from config import USE_CACHED_AI


class StoryBuilder:

    def __init__(self):

        self.presentation = PresentationData()

        self.ai = AIEngine()

    def build(self):

        # AI generation is paused: USE_CACHED_AI means always reuse
        # output/ai_response.json as-is, with no automatic freshness
        # check against the current client/data -- calling Gemini
        # happens only when that cache file doesn't exist at all (e.g.
        # you've deleted it yourself because you specifically want new
        # AI content generated for what's currently loaded).
        if USE_CACHED_AI:

            cache = Path("output") / "ai_response.json"

            if cache.exists():

                with open(
                    cache,
                    encoding="utf-8"
                ) as f:

                    ai_json = json.load(f)

                print("\nUsing cached AI response...\n")

            else:

                print("\nCached AI not found. Running Gemini...\n")

                ai_json = self.ai.run()

        else:

            ai_json = self.ai.run()

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