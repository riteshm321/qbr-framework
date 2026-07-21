from pathlib import Path


class MarkdownExporter:

    def __init__(self):

        self.output = Path("output/AI")

        self.output.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------

    def export(self, ai_json):

        file_map = {

            "ExecutiveSummary": "Executive_Summary.md",

            "CampaignOverview": "Campaign_Overview.md",

            "Q1Analysis": "Q1_Analysis.md",

            "Q2Analysis": "Q2_Analysis.md",

            "Comparison": "Comparison.md",

            "Optimization": "Optimization.md",

            "Recommendations": "Recommendations.md",

            "ValueAdd": "Value_Add.md",

            "ExecutiveConclusion": "Executive_Conclusion.md",

            "SpeakerNotes": "Speaker_Notes.md"

        }

        for section, filename in file_map.items():

            if section not in ai_json:
                continue

            data = ai_json[section]

            with open(

                self.output / filename,

                "w",

                encoding="utf-8"

            ) as f:

                f.write(f"# {section}\n\n")

                if isinstance(data, dict):

                    for key, value in data.items():

                        if isinstance(value, list):

                            f.write(f"## {key}\n\n")

                            for item in value:
                                f.write(f"- {item}\n")

                            f.write("\n")

                        else:

                            f.write(f"## {key}\n\n")

                            f.write(str(value))

                            f.write("\n\n")

                else:

                    f.write(str(data))