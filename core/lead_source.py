"""
Lead Source Resolution

Decides which report the deck counts leads from, and reshapes it so the rest of
the framework doesn't need to know which one won.

The Purchased Leads Report is the authoritative record of delivered leads: one
row per lead, with a Lead ID and the date it was handed to the client. The
Leads-by-day export counts materially more than that -- for one campaign, 3,702
rows against 1,372 delivered -- because it includes refunded and
non-delivered activity, and no filter on it reproduces the delivered figure
(checked against every combination of Refunded, de-duplication and unique
account/asset pairs). So where the Purchased Leads Report is present, it is
what the deck counts.

Its columns are named differently, so they are renamed to the ones the analyzer
already expects. That keeps the switch to a single substitution at load time
rather than a change rippling through every metric.
"""

import pandas as pd

from constants import LEAD_DETAIL, PURCHASED_LEADS, ACCOUNT_ENGAGEMENT


# Purchased Leads column -> the name the rest of the framework uses.
COLUMN_ALIASES = {
    "Company": "Account Name",
    "Asset": "Asset Name",
}

TOPIC_COLUMN = "Top MLI Topic (Average Over Last 7 Weeks)"


def _attach_account_topics(leads, datasets):

    """
    Adds the per-account top MLI topic, which the Purchased Leads Report does
    not carry but the deck shows ("TOP TRENDING TOPIC" on each period slide).

    The topic is an attribute of the account, not of an individual lead, so
    mapping account -> topic from a report that does carry it is a lookup rather
    than an assumption. Leaves the column absent if no source has it, and every
    consumer already treats a missing topic as blank.
    """

    if TOPIC_COLUMN in leads.columns:
        return leads

    for name in (LEAD_DETAIL, ACCOUNT_ENGAGEMENT):

        source = datasets.get(name)

        if source is None:
            continue

        if TOPIC_COLUMN not in getattr(source, "columns", []):
            continue

        if "Account Name" not in source.columns:
            continue

        topics = (
            source.dropna(subset=["Account Name", TOPIC_COLUMN])
            .groupby("Account Name")[TOPIC_COLUMN]
            .agg(lambda values: values.mode().iloc[0] if not values.mode().empty else None)
        )

        if topics.empty:
            continue

        leads[TOPIC_COLUMN] = leads["Account Name"].map(topics)

        matched = int(leads[TOPIC_COLUMN].notna().sum())

        print(
            f"  [LEADS] top-topic signal mapped from {name} "
            f"for {matched:,} of {len(leads):,} delivered leads"
        )

        return leads

    return leads


def resolve(datasets):

    """
    Replaces the lead dataset with delivered leads when that report is present.

    Returns the dataset key the deck should count from, having normalised it in
    place, so callers can report which source was used.
    """

    purchased = datasets.get(PURCHASED_LEADS)

    if purchased is None or purchased.empty:

        if LEAD_DETAIL in datasets:
            print(
                "\n  [LEADS] No Purchased Leads Report found - counting the "
                "Leads-by-day export instead."
            )
            print(
                "          That export includes refunded and non-delivered "
                "activity, so totals may exceed what was actually delivered. "
                "Export the Purchased Leads Report into input/ for delivered "
                "figures.\n"
            )

        return LEAD_DETAIL

    leads = purchased.copy()

    leads = leads.rename(
        columns={
            source: target
            for source, target in COLUMN_ALIASES.items()
            if source in leads.columns and target not in leads.columns
        }
    )

    leads = _attach_account_topics(leads, datasets)

    delivered = len(leads)

    print(f"\n  [LEADS] counting {delivered:,} delivered leads from the Purchased Leads Report")

    previous = datasets.get(LEAD_DETAIL)

    if previous is not None and len(previous) != delivered:
        print(
            f"          (the Leads-by-day export holds {len(previous):,} rows; "
            "it is used only for account-level topic signal, not for counting)"
        )

    print()

    # Substituted under the key the analyzer already reads, so no metric needs
    # to know which report it came from.
    datasets[LEAD_DETAIL] = leads

    return LEAD_DETAIL
