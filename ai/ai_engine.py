import json

from ai.prompt_builder import PromptBuilder
from ai.gemini_client import GeminiClient
from ai.markdown_exporter import MarkdownExporter
from pathlib import Path

class AIEngine:

    def __init__(self):

        self.builder = PromptBuilder()

        self.client = GeminiClient()

        self.exporter = MarkdownExporter()

    # ----------------------------------------------------------

    def run(self):

        print()
        print("=" * 60)
        print("GENERATING AI CONTENT...")
        print("=" * 60)

        prompt = self.builder.build()

        try:

            response = self.client.ask(prompt)

        except Exception as e:

            # A transient AI-service failure (rate limit, network,
            # auth) shouldn't take down the whole deck generation --
            # everything except the AI narrative text is independent of
            # this call. Leave those sections blank (same fallback as
            # an unparseable response below) rather than crashing.
            print(f"\nAI request failed: {e}\n")
            return None

        try:

            ai_json = json.loads(response)

        except json.JSONDecodeError:

            print("\nAI did not return valid JSON.\n")
            print(response)
            return

        self.exporter.export(ai_json)

        print()

        print("=" * 60)
        print("AI CONTENT GENERATED")
        print("=" * 60)

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

        return ai_json