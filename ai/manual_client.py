import json

from pathlib import Path

import config


class ManualClient:

    """
    Serves hand-authored narrative from a file instead of calling an API.

    This is the last link in the provider chain: it only ever runs when every
    real provider has failed, which in practice means all their free quotas are
    exhausted. Without it, a quota-exhausted day produces a deck with every
    narrative box blank; with it, previously authored content can stand in until
    a provider is available again.

    Availability follows the same rule as the API clients -- a missing input
    file is treated exactly like a missing API key, so the chain skips this
    provider silently and the blank-AI degradation still applies when there is
    nothing to serve.

    The file is per report mode (output/ai_manual_Campaign.json,
    ai_manual_Monthly.json, ...) because the narrative describes a specific
    period breakdown; serving Monthly text for a Quarterly run would put the
    wrong periods on the slides.
    """

    name = "manual"

    @staticmethod
    def path_for(mode=None):

        mode = mode or config.REPORT_MODE

        return Path("output") / f"ai_manual_{mode}.json"

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
