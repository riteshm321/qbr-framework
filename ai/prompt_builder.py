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

9. FORMATTING. Write counts of a thousand or more with a thousands separator
   ("12,345", not "12345"), so the narrative matches the figures printed on the
   slides beside it. That is a formatting example only -- never treat it, or any
   number in these instructions, as campaign data.

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

EVERY bullet, heading, footer and detail must be a COMPLETE SENTENCE that says
what the data means. Never answer with a label-and-value pair, and never simply
restate a number that is already printed on the slide -- the figure is beside
the text, so repeating it adds nothing and reads as an unfinished placeholder.

  BAD:  "Targeted accounts: 1,507"
  BAD:  "Q2 leads: 384"
  BAD:  "Lead Volume - dropped 41% to 1,032 leads"
  GOOD: "Only 21% of reached accounts converted, the clearest gap to close."
  GOOD: "Leads peaked in Q2 then fell for two straight quarters."
  GOOD: "Lead volume fell while account reach widened, so intent is outpacing conversion."

WORD COUNTS ARE RANGES: land inside the stated range. Going over gets the text
cut off mid-sentence on the client's slide; coming in far under leaves the box
looking empty. A range of "10-14 words" means write 10 to 14 words, not 3.

NEVER write the word count into your answer. Counting is for you, not for the
reader -- every string you return is printed verbatim onto a client-facing
slide, so a trailing "(14 words)" appears in the presentation. Return only the
sentence itself.

- PeriodAnalysis: exactly one entry per label listed under
  "Periods Needing Individual Commentary", in that same order, and each
  "period" value must be that exact label. Each "summary" 22-30 words.

- TrendAnalysis: read "Trend Projection". Rows where "Is Forecast" is true are
  projections, not actuals -- never present them as results already achieved.
  Refer to points by the "Period" value in that table (e.g. "Q2"), NOT by the
  Reporting Period labels: this table numbers its points sequentially and its
  values are the chart's own axis labels, so using any other name would
  describe the chart beside it with labels it does not show.
  heading 9-14 words; exactly 3 bullets, 10-14 WORDS EACH.

- ContentPerformance: read "Asset Performance" and "Asset Contribution".
  heading 8-11 words; exactly 3 bullets, 11-16 WORDS EACH.

- AudienceInterest: read "Trending Topics" and "Topic Categories".
  heading 8-12 words; summary 18-26 words.

- Engagement: read "Account Funnel" and "Account Conversion" -- the
  Targeted / Reached / Engaged account funnel. This is NOT about impressions,
  clicks or CTR. Exactly 3 bullets, 10-14 WORDS EACH.

- TopAccounts: read "Top Engaged Accounts" and "Top Intent Accounts".
  footer 16-22 words.

- Optimization and OptimizationHighlights: read "Metric Status". That table
  carries the exact per-metric direction and Status wording shown on the status
  pills next to this text, so your description must agree with it -- do not call
  a metric flat if its Status says Decline or Strong Growth. Ignore any
  all-zero change figures in "Optimization Insights": for a single-period
  report that table compares the period against itself, and its zeroes mean
  "not applicable", not "no change".
  Optimization: EXACTLY 3 bullets, each a single action, 11-16 words each --
  these are the only three lines the slide has room for. summary 18-26 words.
  OptimizationHighlights: footer 19-27 words.

- ExecutiveConclusion.summary: the closing line of the executive summary --
  what the period means overall and where to focus next. 22-30 words.

- Comparison: summary 22-30 words. Exactly 3 bullets, each 12-18 words, in
  this order and no other: bullet 1 is the overall headline; bullet 2 MUST be
  about Total Leads; bullet 3 MUST be about Unique Accounts. Bullets 2 and 3 sit
  directly beneath the Total Leads and Unique Accounts percentage change
  figures, so covering a different metric there contradicts the number printed
  above it.

- KeyLearnings: exactly 5 entries. "title" 3-5 words (a short phrase, no
  trailing full stop). "detail" 13-19 words, one sentence that explains what the
  figures mean rather than listing them.

- Recommendations.actions: exactly 5 forward-looking actions, one sentence and
  14-20 words each.

- Partnership.summary: read "Value Add Metrics" and "Top Intent Accounts".
  THREE COMPLETE SENTENCES, 45-60 words in total. This one is a wide full-width
  panel rather than a narrow card, so unlike every other section above it needs
  a full paragraph -- a single clipped clause leaves most of the panel empty.
  Sentence 1: what the intent layer identified. Sentence 2: how much of it was
  engaged. Sentence 3: what is sales-ready and why that matters next.
  When quoting a figure from "Value Add Metrics", describe it using that row's
  "Caption" wording rather than its short "Metric" name -- the captions state
  which population each figure is measured against, and the names do not.

- ValueAdd.heading: what the intent layer added beyond core lead delivery, as
  ONE COMPLETE SENTENCE of 12-25 words. This is the slide's lead-in line under
  a large title, so a three-word fragment reads as unfinished.

- Every "heading" and "footer" is a single sentence that characterises what the
  data shows, rather than restating a number already printed on the slide.

Campaign Analytics

{json.dumps(package, indent=2)}

"""

        return prompt