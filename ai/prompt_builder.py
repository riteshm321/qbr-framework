import json
from pathlib import Path


class PromptBuilder:

    def __init__(self):

        self.package = Path("output/qbr_package.json")

    # ----------------------------------------------------------

    def load_package(self):

        with open(

            self.package,

            "r",

            encoding="utf-8"

        ) as f:

            return json.load(f)

    # ----------------------------------------------------------

    def build(self):

        package = self.load_package()

        prompt = f"""
You are a Senior B2B Marketing Consultant with expertise in Executive Quarterly Business Reviews (QBRs).

You are preparing a client-facing presentation.

The data below contains the complete campaign analytics.

IMPORTANT RULES

1. NEVER invent numbers.

2. NEVER change any metric.

3. Use ONLY the provided data.

4. Keep an executive consulting tone.

5. Highlight successes first, then optimization opportunities.

6. Every insight must be supported by the data.

7. PERIODS. The "Reporting Period" section states exactly what this report
   covers. Refer to periods using ONLY the labels given in its
   "Period Breakdown". Never invent a period name -- do not write "Q1" or "Q2"
   unless those exact labels appear there -- and never state or imply a
   different number of periods than "Periods Analyzed". If that count is 4, this
   is not a two-quarter report.

8. DIRECTION. Check whether each metric rose or fell before describing it. Do
   not call a decline "growth" or "momentum". Where a metric declined, say so
   plainly and treat it as an optimization opportunity.

------------------------------------------------------------

Return ONLY valid JSON.

Do NOT return markdown.

Do NOT wrap the JSON inside code fences.

Use exactly this schema.

{{
    "ExecutiveSummary": {{
        "short":"",
        "long":"",
        "bullets":[]
    }},

    "CampaignOverview": {{
        "summary":"",
        "bullets":[]
    }},

    "PeriodAnalysis": [
        {{
            "period":"",
            "summary":""
        }}
    ],

    "Comparison": {{
        "summary":"",
        "bullets":[]
    }},

    "Optimization": {{
        "summary":"",
        "bullets":[]
    }},

    "Recommendations": {{
        "summary":"",
        "actions":[]
    }},

    "ValueAdd": {{
        "heading":"",
        "summary":"",
        "bullets":[]
    }},

    "TrendAnalysis": {{
        "heading":"",
        "bullets":[]
    }},

    "ContentPerformance": {{
        "heading":"",
        "bullets":[]
    }},

    "AudienceInterest": {{
        "heading":"",
        "summary":""
    }},

    "Engagement": {{
        "bullets":[]
    }},

    "TopAccounts": {{
        "footer":""
    }},

    "OptimizationHighlights": {{
        "footer":""
    }},

    "KeyLearnings": {{
        "items":[
            {{
                "title":"",
                "detail":""
            }}
        ]
    }},

    "Partnership": {{
        "summary":""
    }},

    "ExecutiveConclusion": {{
        "summary":""
    }},

    "SpeakerNotes": {{
        "notes":""
    }}
}}

SECTION REQUIREMENTS

Each section below appears in a FIXED-SIZE text box on a specific slide, beside
a specific chart or table. Read the data named for it -- do not describe a
different dataset.

WORD LIMITS ARE HARD LIMITS, NOT TARGETS. These boxes cannot grow. Text over
the limit is cut off mid-sentence on the client's slide, so a complete short
sentence is always better than a detailed one that gets truncated. Count the
words before you answer, and cut adjectives and preamble rather than exceeding
the limit.

- PeriodAnalysis: exactly one entry per label listed under
  "Periods Needing Individual Commentary", in that same order, and each
  "period" value must be that exact label. Each "summary" max 30 words.

- TrendAnalysis: read "Trend Projection". Rows where "Is Forecast" is true are
  projections, not actuals -- never present them as results already achieved.
  Refer to points by the "Period" value in that table (e.g. "Q2"), NOT by the
  Reporting Period labels: this table numbers its points sequentially and its
  values are the chart's own axis labels, so using any other name would
  describe the chart beside it with labels it does not show.
  heading max 14 words; exactly 3 bullets, MAX 14 WORDS EACH.

- ContentPerformance: read "Asset Performance" and "Asset Contribution".
  heading max 11 words; exactly 3 bullets, MAX 16 WORDS EACH.

- AudienceInterest: read "Trending Topics" and "Topic Categories".
  heading max 12 words; summary max 26 words.

- Engagement: read "Account Funnel" and "Account Conversion" -- the
  Targeted / Reached / Engaged account funnel. This is NOT about impressions,
  clicks or CTR. Exactly 3 bullets, MAX 14 WORDS EACH.

- TopAccounts: read "Top Engaged Accounts" and "Top Intent Accounts".
  footer max 22 words.

- OptimizationHighlights: read "Optimization Insights". footer max 27 words.

- KeyLearnings: exactly 5 entries. "title" max 5 words (a short phrase, no
  trailing full stop). "detail" max 19 words, one sentence citing the
  supporting figures.

- Recommendations.actions: exactly 5 forward-looking actions, one sentence and
  max 20 words each.

- Partnership.summary: read "Value Add Metrics" and "Top Intent Accounts".
  Max 60 words.

- ValueAdd.heading: what the intent layer added beyond core lead delivery.
  Max 27 words.

- Every "heading" and "footer" is a single sentence that characterises what the
  data shows, rather than restating a number already printed on the slide.

Campaign Analytics

{json.dumps(package, indent=2)}

"""

        return prompt