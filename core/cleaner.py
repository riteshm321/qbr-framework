import pandas as pd

def clean_dataframe(df):

    df.columns = df.columns.str.strip()

    return df