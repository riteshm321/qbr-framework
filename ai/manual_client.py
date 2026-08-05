import json
import re

from pathlib import Path

import config


class ManualClient:

    """
    Serves hand-authored narrative from a file instead of calling an API.

    A curated override, and the last link before the deterministic generator:
    it only runs once every API provider has failed. Availability follows the
    same rule as the API clients -- a missing file is treated exactly like a
    missing API key, so the chain moves on without it.

    The filename is scoped to CLIENT, CAMPAIGN and REPORT MODE, all three of
    which the content is specific to. Scoping it on mode alone was actively
    dangerous: a file authored for one client was served into a different
    client's deck the moment that client's quota ran out, putting the wrong
    company's lead totals, countries and date range on their slides. That is the
    same mistake the content cache is deliberately keyed against, and it has to
    hold here too.
    """

    name = "manual"

    @staticmethod
    def _slug(text):

        """Filesystem-safe fragment of a client or campaign name."""

        cleaned = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-")

        return cleaned[:40] or "unknown"

    @classmethod
    def path_for(cls, mode=None):

        mode = mode or config.REPORT_MODE

        # Campaign ID where the program string carries one, so the filename
        # stays stable and short; the whole program name otherwise.
        match = re.search(r"\(ID:\s*([^)]+)\)", str(config.PROGRAM_NAME or ""))

        campaign = match.group(1).strip() if match else config.PROGRAM_NAME

        return Path("output") / (
            f"ai_manual_{cls._slug(config.CLIENT_NAME)}"
            f"_{cls._slug(campaign)}_{mode}.json"
        )

    def __init__(self):

        self.path = self.path_for()

        if not self.path.exists():
            raise ValueError(
                f"no hand-authored content at {self.path}"
            )

        # Parsed here rather than in ask() so a malformed file marks the
        # provider unavailable, letting the chain move on, instead of counting
        # as a failed attempt.
        self.content = json.loads(
            self.path.read_text(encoding="utf-8")
        )

    # --------------------------------------------------------

    def ask(self, prompt):

        # The prompt is ignored on purpose -- the content is already written.
        # It still passes through the chain's JSON validation like any other
        # provider's response.
        return json.dumps(self.content)
