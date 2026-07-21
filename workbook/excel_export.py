from pathlib import Path

import pandas as pd


class ExcelExporter:

    def __init__(self, analysis):

        self.analysis = analysis

        self.output = Path("output")

        self.output.mkdir(exist_ok=True)

    # ---------------------------------------

    def export(self):

        file = self.output / "QBR_Workbook.xlsx"

        with pd.ExcelWriter(file) as writer:

            for sheet_name, table in self.analysis.tables.items():

                safe_name = sheet_name[:31]

                table.to_excel(

                    writer,

                    sheet_name=safe_name,

                    index=False

                )

        print()

        print("=" * 60)

        print("WORKBOOK CREATED")

        print(file)

        print("=" * 60)