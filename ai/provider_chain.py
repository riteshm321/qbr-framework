"""
Provider Chain

Tries each AI provider named in config.AI_PROVIDER_CHAIN, in order, until one
returns usable content. A provider is skipped when its API key is missing or
its SDK isn't installed, so the chain uses whichever providers are genuinely
usable on this machine rather than requiring every one to be configured.

This is what keeps deck generation working once a free tier is exhausted: the
run continues on the next provider instead of losing all AI narrative.
"""

import config


# Each provider module imports its own SDK at module level, so these are
# deferred into factories: importing the whole chain eagerly would crash on a
# machine that happens to be missing one SDK, even for a provider not in use.

def _gemini():
    from ai.gemini_client import GeminiClient
    return GeminiClient()


def _groq():
    from ai.groq_client import GroqClient
    return GroqClient()


def _openai():
    from ai.openai_client import OpenAIClient
    return OpenAIClient()


FACTORIES = {
    "gemini": _gemini,
    "groq": _groq,
    "openai": _openai,
}


# Failures that won't be fixed by asking the same provider again -- no point
# spending a second call on them, move to the next provider immediately.
_PERMANENT = (
    "429",
    "resource_exhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "insufficient_quota",
    "unauthorized",
    "authentication",
    # Bad-credential wording differs per provider: Gemini reports
    # "API key not valid" / API_KEY_INVALID, OpenAI-compatible endpoints
    # report invalid_api_key. Match all of them, or a permanently broken key
    # costs a wasted retry on every run.
    "api key not valid",
    "api_key_invalid",
    "invalid api key",
    "invalid_api_key",
    "permission",
    "forbidden",
)


class ProviderChain:

    def __init__(self, order=None):

        self.order = list(order or config.AI_PROVIDER_CHAIN)

        self.last_provider = None

    # --------------------------------------------------------

    @staticmethod
    def _is_permanent(error):

        text = f"{type(error).__name__} {error}".lower()

        return any(marker in text for marker in _PERMANENT)

    def _build(self, name):

        factory = FACTORIES.get(name)

        if factory is None:
            print(f"  [AI] '{name}' is not a known provider - check AI_PROVIDER_CHAIN")
            return None

        try:
            return factory()

        except Exception as error:

            # A missing key raises ValueError from the client's __init__; a
            # missing SDK raises ImportError. Both just mean "not usable
            # here", which is an expected, non-fatal condition.
            print(f"  [AI] {name} unavailable ({type(error).__name__}), skipping")
            return None

    # --------------------------------------------------------

    def ask(self, prompt, validate=None):

        """
        Returns (text, provider_name), or (None, None) when every provider
        failed.

        `validate` is an optional callable that raises to reject a response
        that arrived successfully but is unusable -- used to reject content
        that isn't parseable JSON, so the chain treats it as a provider
        failure and moves on rather than silently returning junk.
        """

        usable = 0

        for name in self.order:

            client = self._build(name)

            if client is None:
                continue

            usable += 1

            # Two attempts per provider, but only for failures that might
            # genuinely differ next time (a malformed response, a dropped
            # connection). Quota and auth failures skip straight on.
            for attempt in (1, 2):

                try:

                    text = client.ask(prompt)

                    if not text or not text.strip():
                        raise ValueError("provider returned an empty response")

                    if validate is not None:
                        validate(text)

                    suffix = f" (attempt {attempt})" if attempt > 1 else ""
                    print(f"  [AI] {name} responded{suffix}")

                    self.last_provider = name

                    return text, name

                except Exception as error:

                    detail = str(error).replace("\n", " ")[:160]

                    if attempt == 1 and not self._is_permanent(error):

                        print(
                            f"  [AI] {name} attempt 1 failed "
                            f"({type(error).__name__}: {detail}) - retrying"
                        )
                        continue

                    print(
                        f"  [AI] {name} failed "
                        f"({type(error).__name__}: {detail})"
                    )
                    break

        if usable == 0:
            print("  [AI] no providers available - check the API keys in .env")

        return None, None
