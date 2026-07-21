from pathlib import Path
from pptx import Presentation
from pptx.chart.data import CategoryChartData

class PowerPointEngine:

    def __init__(self):

        self.template = Path("templates/LeadGen_QBR_Template.pptx")
        self.prs = None

    # ---------------------------------------------------------
    # Load PowerPoint
    # ---------------------------------------------------------

    def load(self):

        self.prs = Presentation(self.template)

    # ---------------------------------------------------------
    # Find object by Selection Pane name
    # (supports grouped shapes)
    # ---------------------------------------------------------

    def find_shape(self, object_name):

        def search(shapes):

            for shape in shapes:

                if shape.name == object_name:
                    return shape

                # Search inside grouped shapes
                if hasattr(shape, "shapes"):

                    found = search(shape.shapes)

                    if found is not None:
                        return found

            return None

        for slide in self.prs.slides:

            found = search(slide.shapes)

            if found is not None:
                return found

        return None

    # ---------------------------------------------------------
    # Replace text
    # ---------------------------------------------------------

    def replace_text(self, object_name, value):

        shape = self.find_shape(object_name)

        if shape is None:

            print(f"[NOT FOUND] {object_name}")

            return False

        # -------------------------------------------------
        # Grouped KPI cards
        # -------------------------------------------------

        if not shape.has_text_frame:

            if hasattr(shape, "shapes"):

                for child in shape.shapes:

                    if child.has_text_frame:

                        tf = child.text_frame

                        if tf.paragraphs and tf.paragraphs[0].runs:

                            tf.paragraphs[0].runs[0].text = str(value)

                        else:

                            tf.clear()

                            tf.paragraphs[0].text = str(value)

                        print(f"[UPDATED GROUP] {object_name}")

                        return True

            print(f"[NO TEXT FRAME] {object_name}")

            return False

        tf = shape.text_frame

        # Preserve formatting by editing the first run
        if tf.paragraphs and tf.paragraphs[0].runs:

            tf.paragraphs[0].runs[0].text = str(value)

            # Remove any extra runs
            while len(tf.paragraphs[0].runs) > 1:
                tf.paragraphs[0]._element.remove(
                    tf.paragraphs[0].runs[-1]._r
                )

        else:

            tf.clear()

            tf.paragraphs[0].text = str(value)

        print(f"[UPDATED] {object_name}")

        return True
    
    def replace_table(self, object_name, dataframe):

        print(f"[TABLE] {object_name}")

        shape = self.find_shape(object_name)

        if shape is None:

            print(f"[NOT FOUND] {object_name}")

            return False

        if not shape.has_table:

            print(f"[NOT A TABLE] {object_name}")

            return False

        table = shape.table

        # ---------------------------------------
        # Write dataframe into PPT table
        # ---------------------------------------

        max_rows = min(len(dataframe), len(table.rows) - 1)

        max_cols = min(len(dataframe.columns), len(table.columns))

        for r in range(max_rows):

            for c in range(max_cols):

                value = dataframe.iloc[r, c]

                if value is None:
                    value = ""

                cell = table.cell(r + 1, c)

                tf = cell.text_frame

                # Preserve formatting
                if tf.paragraphs and tf.paragraphs[0].runs:

                    tf.paragraphs[0].runs[0].text = str(value)

                else:

                    tf.text = str(value)

        print(f"[UPDATED TABLE] {object_name}")

        return True
    
    def replace_chart(self, object_name, dataframe):

        print(f"[CHART] {object_name}")

        shape = self.find_shape(object_name)

        if shape is None:

            print(f"[NOT FOUND] {object_name}")

            return False

        if not shape.has_chart:

            print(f"[NOT A CHART] {object_name}")

            return False

        chart = shape.chart

        chart_data = CategoryChartData()

        # Categories = first column
        chart_data.categories = dataframe.iloc[:, 0].tolist()

        # Remaining columns become series
        for column in dataframe.columns[1:]:

            chart_data.add_series(
                str(column),
                dataframe[column].tolist()
            )

        chart.replace_data(chart_data)

        print(f"[UPDATED CHART] {object_name}")

        return True
    
    # ---------------------------------------------------------
    # Replace multiple text objects
    # ---------------------------------------------------------

    def replace_objects(self, replacements):

        print()

        print("=" * 60)
        print("UPDATING POWERPOINT OBJECTS")
        print("=" * 60)

        for object_name, value in replacements.items():

            if value is None:
                continue

            # DataFrame -> PowerPoint table
            shape = self.find_shape(object_name)

            if shape is None:
                print(f"[NOT FOUND] {object_name}")
                continue

            if hasattr(shape, "has_chart") and shape.has_chart:

                self.replace_chart(
                    object_name,
                    value
                )

            elif hasattr(shape, "has_table") and shape.has_table:

                self.replace_table(
                    object_name,
                    value
                )

            else:

                self.replace_text(
                    object_name,
                    value
                )

    # ---------------------------------------------------------
    # Save Presentation
    # ---------------------------------------------------------

    def save(self):

        output = Path("output") / "Generated_QBR.pptx"

        self.prs.save(output)

        print()
        print("=" * 60)
        print("POWERPOINT CREATED")
        print(output)
        print("=" * 60)

        return output

    # ---------------------------------------------------------
    # Create PPT
    # ---------------------------------------------------------

    def create(self, replacements=None):

        self.load()

        if replacements:

            self.replace_objects(replacements)

        self.save()