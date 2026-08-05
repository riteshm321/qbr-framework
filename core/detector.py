from constants import (
    LEAD_DETAIL,
    ACCOUNT_ENGAGEMENT,
    TRENDING_TOPICS,
    TRENDING_ACCOUNTS,
    ASSET_DELIVERY,
    TARGET_ACCOUNT_HISTORY,
    PURCHASED_LEADS,
    UNKNOWN
)

def detect_dataset(df):

    """
    Detects dataset type based on column structure.
    This makes the framework independent of filenames.
    """

    columns = set(df.columns)

    # -----------------------------------------
    # Purchased Leads (delivered leads)
    #
    # Checked before Lead Detail: this report also carries Job Title and
    # Country, so the more specific signature has to win. "Lead ID" plus a
    # delivered-date column is unique to it -- no other export identifies
    # individual leads or records when they were handed to the client.
    # -----------------------------------------

    if {
        "Lead ID",
        "Client Delivered Date"
    }.issubset(columns):

        return PURCHASED_LEADS

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
    # Target Account List History
    # -----------------------------------------

    elif {
        "Accounts Targeted",
        "New Accounts",
        "Removed Accounts"
    }.issubset(columns):

        return TARGET_ACCOUNT_HISTORY

    # -----------------------------------------

    return UNKNOWN