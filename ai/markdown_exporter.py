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

            # One entry per analysed period, replacing the old fixed
            # Q1Analysis / Q2Analysis pair.
            "PeriodAnalysis": "Period_Analysis.md",

            "Comparison": "Comparison.md",

            "Optimization": "Optimization.md",

            "OptimizationHighlights": "Optimization_Highlights.md",

            "Recommendations": "Recommendations.md",

            "TrendAnalysis": "Trend_Analysis.md",

            "ContentPerformance": "Content_Performance.md",

            "AudienceInterest": "Audience_Interest.md",

            "Geography": "Geography.md",

            "Engagement": "Engagement.md",

            "TopAccounts": "Top_Accounts.md",

            "KeyLearnings": "Key_Learnings.md",

            "Partnership": "Partnership.md",

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

                        f.write(f"## {key}\n\n")

                        if isinstance(value, list):

                            for item in value:
                                f.write(f"- {self._render(item)}\n")

                            f.write("\n")

                        else:

                            f.write(str(value))

                            f.write("\n\n")

                elif isinstance(data, list):

                    # PeriodAnalysis is a list of {period, summary} entries --
                    # give each its own subheading rather than dumping the
                    # raw repr of the list.
                    for item in data:

                        if isinstance(item, dict):

                            title = (
                                item.get("period")
                                or item.get("title")
                                or ""
                            )

                            if title:
                                f.write(f"## {title}\n\n")

                            body = [
                                str(value)
                                for key, value in item.items()
                                if key not in ("period", "title") and value
                            ]

                            f.write("\n\n".join(body))
                            f.write("\n\n")

                        else:

                            f.write(f"- {item}\n")

                else:

                    f.write(str(data))

    # ----------------------------------------------------------

    @staticmethod
    def _render(item):

        """A list entry as one readable line. Entries are usually plain
        strings, but KeyLearnings.items are {title, detail} pairs."""

        if isinstance(item, dict):

            parts = [str(value) for value in item.values() if value]

            return " - ".join(parts)

        return str(item)