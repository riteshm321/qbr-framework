"""
Framework Constants

This file contains all reusable constants used across
the Madison Logic QBR Framework.

Version: 0.2
"""

# ======================================================
# DATASET TYPES
# ======================================================

LEAD_DETAIL = "LeadDetail"

ACCOUNT_ENGAGEMENT = "AccountEngagement"

TRENDING_TOPICS = "TrendingTopics"

TRENDING_ACCOUNTS = "TrendingAccounts"

ASSET_DELIVERY = "AssetDelivery"

TARGET_ACCOUNT_HISTORY = "TargetAccountHistory"

# The Purchased Leads Report: one row per delivered lead, carrying a Lead ID
# and the date the lead was delivered to the client. This is the authoritative
# record of what was actually delivered and billed -- the Leads-by-day export
# counts materially more (it includes refunded and non-delivered activity), so
# where this report is present it, not that one, is what the deck counts.
PURCHASED_LEADS = "PurchasedLeads"

UNKNOWN = "Unknown"

# ======================================================
# CAMPAIGN TYPES
# ======================================================

LEADGEN = "LeadGen"

DISPLAY = "Display"

CTV = "CTV"

AUDIO = "Audio"

# ======================================================
# REPORT MODES
# ======================================================

CAMPAIGN = "Campaign"

MONTHLY = "Monthly"

QUARTERLY = "Quarterly"

CUSTOM = "Custom"