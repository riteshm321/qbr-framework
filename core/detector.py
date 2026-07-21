from constants import (
    LEAD_DETAIL,
    ACCOUNT_ENGAGEMENT,
    TRENDING_TOPICS,
    TRENDING_ACCOUNTS,
    ASSET_DELIVERY,
    UNKNOWN
)

def detect_dataset(df):

    """
    Detects dataset type based on column structure.
    This makes the framework independent of filenames.
    """

    columns = set(df.columns)

    # -----------------------------------------
    # Lead Detail
    # -----------------------------------------

    if {
        "Job Title",
        "Asset Name",
        "Country"
    }.issubset(columns):

        return LEAD_DETAIL

    # -----------------------------------------
    # Account Engagement
    # -----------------------------------------

    elif {
        "Display Impressions",
        "Clicks",
        "Site Visits"
    }.issubset(columns):

        return ACCOUNT_ENGAGEMENT

    # -----------------------------------------
    # Trending Topics
    # -----------------------------------------

    elif {
        "Company",
        "Topic",
        "ML Insights Score"
    }.issubset(columns):

        return TRENDING_TOPICS

    # -----------------------------------------
    # Trending Accounts
    # -----------------------------------------

    elif {
        "Targeted Accounts",
        "Trending",
        "Reached",
        "Engaged"
    }.issubset(columns):

        return TRENDING_ACCOUNTS

    # -----------------------------------------
    # Asset Delivery
    # -----------------------------------------

    elif {
        "Asset Name",
        "# Accounts",
        "Leads"
    }.issubset(columns):

        return ASSET_DELIVERY

    # -----------------------------------------

    return UNKNOWN