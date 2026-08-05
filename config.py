from pathlib import Path
from constants import *

# ===========================================
# Campaign Information
#
# CLIENT_NAME / PROGRAM_NAME are fallback defaults only.
# main.py overwrites them at runtime with the "Client:" /
# "Program:" metadata read from the input reports, so a new
# client's reports work without editing this file.
# ===========================================

CLIENT_NAME = "Synchrony"

PROGRAM_NAME = "Synchrony CCB2B - HIA incremental 8"

CAMPAIGN_TYPE = LEADGEN

# ===========================================
# Report Configuration
#
# REPORT_MODE / DATE_SPLITS / ANALYSIS_WINDOW are placeholders.
# main.py overwrites all three at runtime via core/period_resolver.py,
# based on the analysis period you pick when running the tool.
# ===========================================

REPORT_MODE = QUARTERLY

DATE_SPLITS = {
    "Q1": ("2026-01-07", "2026-03-31"),
    "Q2": ("2026-04-01", "2026-06-30")
}

ANALYSIS_WINDOW = None

# Month over Month: months beyond this many don't get their own dedicated
# divider+detail slide pair -- the overflow is bucketed into 2 summary
# slots for the comparison chart/table instead (see LeadGenAnalyzer).
MAX_MONTHLY_DETAIL_SLIDES = 6

# ==========================
# Paths
# ==========================

BASE_DIR = Path(__file__).parent

INPUT_DIR = BASE_DIR / "input"

OUTPUT_DIR = BASE_DIR / "output"

LOG_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)

LOG_DIR.mkdir(exist_ok=True)

# ==========================
# AI Content Generation
# ==========================

# Providers are tried in this order until one returns usable content. A
# provider whose API key isn't in .env -- or whose SDK isn't installed -- is
# skipped automatically, so this list can safely name more providers than you
# currently hold keys for. Add a key, and that provider joins the chain with
# no code change.
# "manual" serves hand-authored narrative from output/ai_manual_<mode>.json,
# for a curated override on a specific deck -- skipped like a missing API key
# when no such file exists. "deterministic" is genuinely last and never
# skipped: it computes the full narrative from qbr_package.json with no
# network, key or quota, so a colleague running the distributed .exe with no
# AI provider configured at all still gets a complete, data-grounded deck.
AI_PROVIDER_CHAIN = ["gemini", "groq", "openai", "manual", "deterministic"]

# Report modes whose AI narrative is cached and reused. Custom Date Range is
# excluded on purpose: an ad-hoc window is unlikely to be re-run with exactly
# the same dates, so its entries would accumulate without ever being reused.
# Add CUSTOM here if the per-run API cost becomes annoying.
AI_CACHE_MODES = {CAMPAIGN, MONTHLY, QUARTERLY}

# Bypass cache *reads* for one run (writes still happen), forcing fresh AI
# content for the current client/campaign/period. To regenerate just one
# entry instead, delete its file from output/ai_cache/.
AI_FORCE_REGENERATE = False