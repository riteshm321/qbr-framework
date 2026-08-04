import os

from dotenv import load_dotenv


load_dotenv()


class GroqClient:

    """
    Groq, reached through its OpenAI-compatible endpoint.

    Talking to it via the `openai` SDK with a base_url override means this
    needs no extra dependency -- that SDK is already here for
    ai/openai_client.py.
    """

    name = "groq"

    MODEL = "llama-3.3-70b-versatile"

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in .env"
            )

        # Imported here rather than at module level so a machine without the
        # openai SDK just reports this provider as unavailable (see
        # ai/provider_chain.py) instead of failing to import at all.
        from openai import OpenAI

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL
        )

    # --------------------------------------------------------

    def ask(self, prompt):

        response = self.client.chat.completions.create(

            model=self.MODEL,

            messages=[
                {"role": "user", "content": prompt}
            ]

        )

        return response.choices[0].message.content
