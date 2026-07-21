import json
from pathlib import Path


class PresentationAssets:

    def __init__(self):

        self.output = Path("output")

    def generate(self):

        slides = {

            "Slide 1": {

                "Title":"Cover"

            },

            "Slide 2": {

                "Chart":"01_Executive_KPI.png",

                "Section":"Executive Summary"

            },

            "Slide 3": {

                "Chart":"02_QoQ_Comparison.png",

                "Section":"Q1 vs Q2"

            },

            "Slide 4": {

                "Chart":"03_Asset_Performance.png",

                "Section":"Asset Performance"

            },

            "Slide 5": {

                "Chart":"04_Asset_Contribution.png",

                "Section":"Asset Contribution"

            },

            "Slide 6": {

                "Chart":"05_Buying_Stage.png",

                "Section":"Buying Stage"

            },

            "Slide 7": {

                "Chart":"06_Top_Accounts.png",

                "Section":"Top Accounts"

            }

        }

        with open(

            self.output /

            "presentation_assets.json",

            "w"

        ) as f:

            json.dump(

                slides,

                f,

                indent=4

            )

        print()

        print("="*60)

        print("PRESENTATION ASSETS CREATED")

        print("="*60)