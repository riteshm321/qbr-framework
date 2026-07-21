import pandas as pd
import csv

def load_csv(file):

    header_row = None

    with open(file, "r", encoding="utf-8", errors="ignore") as f:

        lines = f.readlines()

    # -------------------------------------------------
    # Find the first real table header
    # -------------------------------------------------

    for i, line in enumerate(lines):

        line = line.strip().strip('"')

        if not line:
            continue

        # Skip LinkedIn metadata
        if line.startswith("Client:"):
            continue

        if line.startswith("Program:"):
            continue

        # Candidate header
        cols = next(csv.reader([line]))

        # A real table header has multiple columns
        if len(cols) >= 3:

            header_row = i
            break

    if header_row is None:
        raise ValueError(
            f"Could not detect table header in {file}"
        )

    print(f"{file} -> header detected at row {header_row}")

    return pd.read_csv(
        file,
        skiprows=header_row,
        encoding="utf-8",
        low_memory=False
    )
    
    print(f"{file} -> header detected at row {header_row}")

    return pd.read_csv(
        file,
        skiprows=header_row,
        encoding="utf-8",
        low_memory=False
    )


def load_excel(file):

    return pd.read_excel(
        file,
        skiprows=3
    )