import json

from pathlib import Path

from ai.deterministic_narrative import DeterministicNarrativeBuilder


class DeterministicClient:

    """
    Computes the full narrative from qbr_package.json instead of calling an
    LLM. No network, no API key, no quota -- this is what keeps AI content
    working forever, on any machine, once every API provider (and any
    hand-authored override) is exhausted or simply not configured.

    Always "available": there is no key to be missing and no SDK to fail to
    import, so this provider never gets skipped by the chain's availability
    check the way the API clients do.
    """

    name = "deterministic"

    PACKAGE_PATH = Path("output") / "qbr_package.json"

    def ask(self, prompt):

        # The prompt is ignored -- the payload it was built from is read
        # directly, the same file ai/prompt_builder.py embeds in the prompt.
        with open(self.PACKAGE_PATH, encoding="utf-8") as f:
            package = json.load(f)

        narrative = DeterministicNarrativeBuilder(package).build()

        return json.dumps(narrative)
