import json

from pathlib import Path

from ai.prompt_builder import PromptBuilder
from ai.provider_chain import ProviderChain
from ai.markdown_exporter import MarkdownExporter


def strip_code_fences(text):

    """
    Models routinely wrap JSON in ```json ... ``` despite being told not to.
    Treating that as a hard failure throws away otherwise perfectly good
    content, so strip the fences before parsing.
    """

    stripped = text.strip()

    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()

    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]

    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]

    return "\n".join(lines).strip()


def parse_response(text):

    """Parsed AI JSON. Raises so ProviderChain can treat an unusable response
    as a provider failure and move to the next one."""

    parsed = json.loads(strip_code_fences(text))

    if not isinstance(parsed, dict):
        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")

    return parsed


class AIEngine:

    def __init__(self):

        self.builder = PromptBuilder()

        self.chain = ProviderChain()

        self.exporter = MarkdownExporter()

        # Which provider actually served the content -- recorded on the cache
        # entry so it's clear later where a given narrative came from.
        self.provider = None

    # ----------------------------------------------------------

    def run(self, prompt=None):

        print()
        print("=" * 60)
        print("GENERATING AI CONTENT...")
        print("=" * 60)

        # The caller normally passes the prompt it already built for the cache
        # fingerprint, so the content stored against a key was demonstrably
        # produced by that exact prompt.
        if prompt is None:
            prompt = self.builder.build()

        text, provider = self.chain.ask(prompt, validate=parse_response)

        if text is None:

            # Every provider failed. The deck is still worth building -- every
            # chart, table and KPI is independent of this -- so the AI sections
            # are left blank rather than taking the whole run down.
            print()
            print("AI content unavailable - continuing without it.")
            print()
            return None

        self.provider = provider

        ai_json = parse_response(text)

        self.exporter.export(ai_json)

        output = Path("output")
        output.mkdir(exist_ok=True)

        with open(
            output / "ai_response.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                ai_json,
                f,
                indent=4,
                ensure_ascii=False
            )

        print()
        print("=" * 60)
        print(f"AI CONTENT GENERATED (via {provider})")
        print("=" * 60)

        return ai_json
