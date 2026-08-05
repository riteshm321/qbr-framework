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

# Domains that identify a person rather than an employer. Grouping accounts by
# email domain would otherwise collapse every lead using a personal address
# into a single enormous "account", so these fall back to the company name.
# None appear in the exports seen so far (B2B lead gen), but one client's data
# carrying them would badly distort every account figure in the deck.
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "yahoo.co.in",
    "hotmail.com", "hotmail.co.uk", "outlook.com", "live.com", "msn.com",
    "aol.com", "icloud.com", "me.com", "mac.com", "protonmail.com", "proton.me",
    "gmx.com", "gmx.de", "gmx.net", "web.de", "t-online.de", "orange.fr",
    "free.fr", "libero.it", "yandex.com", "yandex.ru", "mail.com", "mail.ru",
    "zoho.com", "qq.com", "163.com", "126.com", "naver.com",
}


def _email_domain(email):

    text = str(email or "").strip().lower()

    if "@" not in text:
        return None

    domain = text.rsplit("@", 1)[-1].strip()

    if not domain or "." not in domain:
        return None

    if domain in PERSONAL_EMAIL_DOMAINS:
        return None

    return domain


def canonicalise_accounts(leads):

    """
    Collapses company-name variants onto one account per email domain.

    The Purchased Leads Report carries a free-text Company name, and the same
    employer arrives spelled several ways -- "ALMAC" and "ALMAC Group",
    "Alder Hey" and "Alder Hey Children's Hospital". Counting distinct names
    therefore over-counts accounts: 878 for one campaign where the platform
    reports 755, with 110 domains carrying more than one spelling.

    The email domain is the reliable account key, and grouping on it reproduces
    the platform exactly -- 755 accounts, and per-asset account counts summing
    to 1,129, matching Asset Delivery Details' own totals asset for asset.

    Each domain keeps one display name (the most frequent spelling, the longest
    where frequency ties, so the fuller form wins) so slides still show real
    company names rather than domains. Leads with no usable domain keep their
    own name as their key, which leaves them counted separately rather than
    silently merged.
    """

    if "Email" not in leads.columns or "Account Name" not in leads.columns:
        return leads

    domains = leads["Email"].map(_email_domain)

    if domains.isna().all():
        return leads

    names = leads["Account Name"].astype(str).str.strip()

    def canonical_name(group):

        counts = group.value_counts()

        top = counts.max()

        # Longest among the equally-most-frequent spellings.
        return max(
            (name for name, n in counts.items() if n == top),
            key=len,
        )

    canonical = (
        names.groupby(domains).agg(canonical_name)
        if domains.notna().any() else {}
    )

    # Two domains can land on the same display name -- one group trading under
    # one name from two domains, e.g. "Fresenius Medical Care" from both
    # fmc-ag.com and freseniusmedicalcare.com. The platform counts those as two
    # accounts, so collapsing them onto one name would undercount by one per
    # collision. The domain is appended to make the key distinct; the display
    # layer strips a trailing "(domain.tld)" already, so slides still show the
    # clean company name.
    if len(canonical):

        seen = {}

        for domain in canonical.index:

            name = canonical[domain]

            if name in seen:
                canonical[domain] = f"{name} ({domain})"
            else:
                seen[name] = domain

    resolved = domains.map(canonical)

    before = names.nunique()

    # Rows without a usable domain keep their original name.
    leads["Account Name"] = resolved.fillna(names)

    after = leads["Account Name"].nunique()

    if after != before:
        print(
            f"  [LEADS] {before:,} company-name spellings resolved to "
            f"{after:,} accounts by email domain"
        )

    return leads


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

    leads = canonicalise_accounts(leads)

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
