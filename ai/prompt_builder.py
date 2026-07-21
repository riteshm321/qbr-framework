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

    "Q1Analysis": {{
        "summary":"",
        "bullets":[]
    }},

    "Q2Analysis": {{
        "summary":"",
        "bullets":[]
    }},

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
        "summary":"",
        "bullets":[]
    }},

    "ExecutiveConclusion": {{
        "summary":""
    }},

    "SpeakerNotes": {{
        "notes":""
    }}
}}

Campaign Analytics

{json.dumps(package, indent=2)}

"""

        return prompt