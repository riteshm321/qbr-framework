from pathlib import Path

import plotly.express as px

from chart_engine.chart_config import CHARTS


class ChartEngine:

    def __init__(self, analysis):

        self.analysis = analysis

        self.output = Path("output/charts")

        self.output.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------

    def save(self, fig, file):

        fig.update_layout(

            template="plotly_white",

            width=1920,

            height=1080,

            title_x=0.5,

            font=dict(

                family="Calibri",

                size=18

            )

        )

        fig.write_image(

            self.output / file,

            scale=2

        )

    # ----------------------------------------

    def create_bar(self, config):

        df = self.analysis.tables[config["table"]]

        fig = px.bar(

            df,

            x=config["x"],

            y=config["y"],

            text=config["y"],

            title=config["title"]

        )

        self.save(

            fig,

            config["file"]

        )

    # ----------------------------------------

    def export(self):

        for chart in CHARTS:

            if chart["type"] == "bar":

                self.create_bar(chart)

        print()

        print("="*60)

        print("ALL CHARTS GENERATED")

        print("="*60)