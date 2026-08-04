"""
AI Content Cache

One entry per (client, campaign, report mode, period, dataset). Regenerating
the same deck repeatedly then costs nothing, while a different client -- or the
same client's different campaign, or a refreshed dataset -- can never reuse
another's narrative.

Entries live in output/ai_cache/, one JSON file each, named by a hash of the
identity. Each file carries its own identity in readable form, so an entry can
be inspected or deleted individually.
"""

import hashlib
import json
import re

from datetime import datetime
from pathlib import Path

import config


CACHE_DIR = Path("output") / "ai_cache"


# ------------------------------------------------------------
# Identity
# ------------------------------------------------------------

def _campaign_id(program_name):

    """
    The "(ID: 133708)" inside a Program string is what separates two different
    campaigns belonging to the same client -- the case where reusing the
    previous narrative would be flatly wrong.

    Falls back to the whole program string when no ID is present, so identity
    is never silently weaker than the client name alone.
    """

    match = re.search(r"\(ID:\s*([^)]+)\)", program_name or "")

    if match:
        return match.group(1).strip()

    return (program_name or "").strip()


def _prompt_fingerprint(prompt):

    """
    SHA-256 of the exact prompt that would be sent.

    Fingerprinting the whole prompt -- not just the analytics payload it
    embeds -- means the cache also notices changes to the instructions:
    the response schema, the section length limits, the rules about which
    dataset each section must read. Hashing only the data left every one of
    those invisible, so editing the prompt silently kept serving content
    written under the previous version of it.

    Stable for a given dataset because export/ai_export.py deliberately writes
    no generation timestamp into the payload -- a value changing every run
    would change this hash every run and stop the cache ever hitting.
    """

    if not prompt:
        return None

    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_identity(period_meta=None, prompt=None):

    """Everything that should make AI content count as "different". Returns
    None when the run can't be identified (no prompt to fingerprint)."""

    fingerprint = _prompt_fingerprint(prompt)

    if fingerprint is None:
        return None

    slots = (period_meta or {}).get("slots", [])

    window = config.ANALYSIS_WINDOW or ("", "")

    return {

        "client": config.CLIENT_NAME,

        "campaign_id": _campaign_id(config.PROGRAM_NAME),

        "program": config.PROGRAM_NAME,

        "mode": config.REPORT_MODE,

        "window": list(window),

        "periods": [slot.get("label", "") for slot in slots],

        # Covers both the campaign data and the prompt instructions.
        "prompt_fingerprint": fingerprint,

    }


def cache_key(identity):

    canonical = json.dumps(identity, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def path_for(identity):

    return CACHE_DIR / f"{cache_key(identity)}.json"


def is_cacheable():

    return config.REPORT_MODE in config.AI_CACHE_MODES


def describe(identity):

    """One-line human summary, for console output."""

    periods = ", ".join(identity["periods"]) or "-"

    return (
        f"{identity['client']} / campaign {identity['campaign_id']} / "
        f"{identity['mode']} / {periods}"
    )


# ------------------------------------------------------------
# Read / write
# ------------------------------------------------------------

def load(identity):

    """The cached AI content for this identity, or None on a miss."""

    path = path_for(identity)

    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)

    except (OSError, json.JSONDecodeError) as error:

        # A corrupt entry is a miss, not a crash -- it gets overwritten by the
        # regeneration this return triggers.
        print(f"  [AI CACHE] ignoring unreadable entry {path.name} ({type(error).__name__})")
        return None

    content = entry.get("content")

    if not isinstance(content, dict) or not content:
        print(f"  [AI CACHE] ignoring entry {path.name} (no usable content)")
        return None

    provider = entry.get("provider", "?")
    generated = entry.get("generated_at", "?")

    print(f"  [AI CACHE] HIT  {describe(identity)}")
    print(f"             generated {generated} via {provider}")

    return content


def store(identity, content, provider):

    """Writes one cache entry. A failure here is reported but not raised --
    the content was generated successfully and the deck should still build."""

    path = path_for(identity)

    entry = {

        "identity": identity,

        "provider": provider,

        "generated_at": datetime.now().isoformat(timespec="seconds"),

        "content": content,

    }

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=4, ensure_ascii=False)

        print(f"  [AI CACHE] STORED {path.name}")
        return True

    except OSError as error:
        print(f"  [AI CACHE] could not write {path.name} ({type(error).__name__}) - continuing")
        return False
