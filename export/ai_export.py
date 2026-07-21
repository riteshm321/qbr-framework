import json
from pathlib import Path
from datetime import datetime

from config import CLIENT_NAME, PROGRAM_NAME, CAMPAIGN_TYPE, REPORT_MODE


class AIExporter:

    def __init__(self, analysis):

        self.analysis = analysis

        self.output = Path("output")

        self.output.mkdir(exist_ok=True)

    # -----------------------------------------------------

    def build_package(self):

        package = {

            "Metadata": {

                "Client": CLIENT_NAME,

                "Program": PROGRAM_NAME,

                "Campaign Type": CAMPAIGN_TYPE,

                "Report Mode": REPORT_MODE,

                "Generated On": datetime.now().strftime("%d-%b-%Y %H:%M")

            },

            "Executive Summary":

                self.analysis.tables["Executive"].to_dict(
                    orient="records"
                ),

            "Campaign Snapshot":

                self.analysis.tables["Campaign Snapshot"].to_dict(
                    orient="records"
                ),

            "Q1 Summary":

                self.analysis.tables["Q1 Summary"].to_dict(
                    orient="records"
                ),

            "Q2 Summary":

                self.analysis.tables["Q2 Summary"].to_dict(
                    orient="records"
                ),

            "Asset Performance":

                self.analysis.tables["Asset Performance"].to_dict(
                    orient="records"
                ),

            "Engagement Summary":

                self.analysis.tables["Engagement Summary"].to_dict(
                    orient="records"
                ),

            "Top Engaged Accounts":

                self.analysis.tables["Top Engaged Accounts"].to_dict(
                    orient="records"
                ),

            "Trending Topics":

                self.analysis.tables["Trending Topics"].to_dict(
                    orient="records"
                ),

            "Topic Categories":

                self.analysis.tables["Topic Categories"].to_dict(
                    orient="records"
                ),

            "Top Intent Companies":

                self.analysis.tables["Top Intent Companies"].to_dict(
                    orient="records"
                ),

            "QoQ Comparison":

                self.analysis.tables["QoQ Comparison"].to_dict(
                    orient="records"
                ),

            "Optimization Insights":

                self.analysis.tables["Optimization Insights"].to_dict(
                    orient="records"
                )

        }

        return package

    # -----------------------------------------------------

    def export_json(self):

        package = self.build_package()

        with open(

            self.output / "qbr_package.json",

            "w",

            encoding="utf-8"

        ) as f:

            json.dump(

                package,

                f,

                indent=4,

                default=str

            )

    # -----------------------------------------------------

    def export_prompt(self):

        prompt = """
You are a Senior B2B Marketing Consultant.

The attached JSON file contains the complete campaign analytics for a Madison Logic Quarterly Business Review.

Using ONLY the information provided inside the JSON, generate the following sections.

1. Executive Summary

2. Campaign Snapshot

3. Q1 Highlights

4. Q2 Highlights

5. Q1 vs Q2 Comparative Analysis

6. Asset Performance Analysis

7. Account Engagement Analysis

8. Trending Topics Analysis

9. Optimization Highlights

10. Key Learnings

11. Recommendations

12. Executive Conclusion

Important Rules

• Never invent metrics.

• Never change numbers.

• Keep an executive consulting tone.

• Maximum 150 words per section.

• Use headings.

• Use bullet points where appropriate.

• Mention positive trends as well as optimization opportunities.

• Make the language suitable for a client-facing PowerPoint.
"""

        with open(

            self.output / "ai_prompt.txt",

            "w",

            encoding="utf-8"

        ) as f:

            f.write(prompt)

    # -----------------------------------------------------

    def export(self):

        self.export_json()

        self.export_prompt()