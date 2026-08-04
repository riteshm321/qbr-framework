# AI Content Enablement: Provider Fallback + Scoped Caching

**Date:** 2026-08-04
**Status:** Design — awaiting review
**Scope:** Parts A and B only. Part C (wiring the 21 unwired AI text boxes) is a
separate spec, deliberately deferred — see [Deferred: Part C](#deferred-part-c).

## Context

AI narrative generation is currently **paused**. `config.USE_CACHED_AI = True`
makes `engine/story_builder.py` reuse `output/ai_response.json` unconditionally,
regardless of which client, campaign, or period is being analyzed. Gemini is only
called when that one file is absent. This was a deliberate temporary measure taken
during heavy QA iteration to avoid exhausting the Gemini free-tier rate limit
(`429 RESOURCE_EXHAUSTED`, 5 requests/min), which had previously crashed the
whole pipeline mid-run.

Two consequences we now need to fix:

1. **Wrong content is reused across clients.** The single cache file has no notion
   of who it was generated for. Running the tool for a new client silently reuses
   the previous client's narrative.
2. **A single provider is a single point of failure.** When the Gemini free quota
   is exhausted, no AI content is produced at all.

## Goals

- Re-enable AI generation, with generation scoped correctly to one
  client + campaign + period + dataset.
- Survive exhaustion of any one provider's free quota by failing over to another
  free provider.
- Never regenerate when nothing relevant changed — repeated deck generation on
  unchanged data must cost zero API calls.
- Never crash the pipeline because AI failed. A deck with blank AI sections is an
  acceptable degraded outcome; a traceback is not.

## Non-goals

- Wiring the 21 currently-unwired `AI_*` text boxes (Part C).
- Extending the prompt schema to cover those boxes (Part C).
- Changing which slides exist or how non-AI content is computed.
- Paid provider tiers.

## A. Provider fallback chain

### Design

A new `ai/provider_chain.py` exposes an ordered chain of providers. Each provider
is a small class with `name`, an `available` check, and `ask(prompt) -> str`,
matching the existing one-file-per-client convention already established by
`ai/gemini_client.py` and `ai/openai_client.py`.

| Order | Provider | Model | Transport |
|---|---|---|---|
| 1 | Gemini | `gemini-2.5-flash` | `google.generativeai` (already installed, key already set) |
| 2 | Groq | `llama-3.3-70b-versatile` | `openai` SDK pointed at `https://api.groq.com/openai/v1` |
| 3 | OpenAI | existing `openai_client.py` | `openai` SDK |

Groq is chosen as the fallback because its free tier is generous and its API is
OpenAI-compatible, so it reuses the already-installed `openai` SDK via a
`base_url` override — **no new dependency**.

Chain order is a list in `config.py`, so reordering or removing a provider is a
one-line edit.

### Availability

A provider is skipped, silently and without error, when either:

- its API key environment variable is unset, or
- its SDK is not importable.

Each provider is therefore **lazily imported inside its own guarded block**. This
matters: `ai/openai_client.py` imports `openai` at module top level, so an eager
import of the whole chain would hard-crash on a machine without that SDK.

Consequence: this ships working today on Gemini alone, and gains real fallback the
moment a `GROQ_API_KEY` is added to `.env`. Nothing about this design blocks on
obtaining that key.

### Failover triggers

The chain advances to the next provider on:

- quota / rate limit — HTTP `429`, or `RESOURCE_EXHAUSTED` in the error text
- authentication failure
- transient network / connection error
- a response that fails JSON validation after one retry against the same provider

### Response hygiene

Before parsing, strip Markdown code fences (```` ```json ... ``` ````) from the
response. Models wrap JSON in fences routinely despite instructions not to, and
today `ai/ai_engine.py` treats that as an outright failure and discards otherwise
valid content.

Validation requires the parsed result to be a `dict`. Missing schema sections are
tolerated — `story_builder.py` already `.get()`s every section with a default.

### Total failure

If every available provider fails, `AIEngine.run()` returns `None`. This path
already exists and is handled: `story_builder.build()` returns the presentation
with its stub `ai` dict, and every AI text box is left at its template value. The
deck still generates. No change needed beyond preserving that behaviour.

## B. Scoped content cache

### Cache identity

A new `ai/content_cache.py` computes identity from:

| Field | Source | Why |
|---|---|---|
| `client` | `config.CLIENT_NAME` (read from report metadata) | separates clients |
| `campaign_id` | ID parsed from `config.PROGRAM_NAME` | separates campaigns for the *same* client |
| `program` | `config.PROGRAM_NAME` (full string) | readability; fallback identity if no ID parses |
| `mode` | `config.REPORT_MODE` | Full Campaign / Monthly / Quarterly are different narratives |
| `window` | `config.ANALYSIS_WINDOW` start + end | separates periods |
| `periods` | ordered slot labels from `period_meta` | distinguishes e.g. 6-month vs 7-month Monthly runs |
| `data_fingerprint` | SHA-256 of the prompt input (see below) | prevents narrative citing stale numbers |

`campaign_id` is the field that solves the "same client, different campaign" case.
`PROGRAM_NAME` for the current dataset is
`"Combined View Julia 2025 (Q2-Q4) (ID: 133708)"`, which yields `133708`. When no
`(ID: …)` is present, the full program string is used as the discriminator
instead, so identity is never silently weaker than the client alone.

### Data fingerprint

The fingerprint is a SHA-256 over `output/qbr_package.json` — the exact analytics
payload embedded in the prompt — serialized canonically (`sort_keys=True`),
**with `Metadata["Generated On"]` removed**.

That exclusion is essential, not cosmetic. `export/ai_export.py` stamps that field
with `datetime.now().strftime("%d-%b-%Y %H:%M")`, so including it would change the
fingerprint every minute and the cache would effectively never hit — silently
defeating the entire feature while appearing to work.

The rest of `Metadata` (Client / Program / Campaign Type / Report Mode) is also
excluded from the fingerprint, because those values are already explicit identity
fields; including them twice adds nothing and makes debugging a mismatch harder.

Effect: re-running deck generation on unchanged data always hits cache (zero API
calls — the primary use case). A genuine data refresh produces a new fingerprint
and regenerates, so slide text can never quote numbers that disagree with the
slide it sits on.

### Storage

```
output/ai_cache/<sha256-of-identity>.json
```

Each file contains:

```json
{
  "identity": { "client": "...", "campaign_id": "...", "mode": "...",
                "window": ["...", "..."], "periods": ["..."],
                "data_fingerprint": "..." },
  "provider": "gemini",
  "generated_at": "2026-08-04T10:15:00",
  "content": { ...the AI JSON... }
}
```

Storing readable identity *inside* the file (rather than encoding it into the
filename) keeps filenames valid on Windows while leaving every entry inspectable
and individually deletable.

`output/ai_response.json` continues to be written on every generation as the
"most recently used" copy, preserving `ai/markdown_exporter.py` and existing
debugging workflows unchanged.

### Migration of the existing cache file

The current `output/ai_response.json` is **not** adopted into the cache. Its
provenance is unknown — we cannot tell which client, campaign, period, or dataset
produced it. Labelling it with an identity we are guessing at would poison the
first cache entry with content that silently belongs to something else. The cache
starts empty; the first run per identity generates.

### Custom Date Range mode

Excluded from caching, per instruction: Custom mode generates fresh every run and
writes no cache entry. Rationale for keeping it out is that an ad-hoc window is
unlikely to be re-run identically, so entries would accumulate without being
reused.

Implemented as a set of cacheable modes in `config.py`
(`AI_CACHE_MODES = {CAMPAIGN, MONTHLY, QUARTERLY}`), so including Custom later is
adding one name to that set.

### Force regeneration

`config.AI_FORCE_REGENERATE = False`. When `True`, the cache is bypassed for
reads but still written. Deleting a single file under `output/ai_cache/` remains
the targeted way to regenerate one identity.

## Data flow

```
main.py
  AIExporter(analysis).export()          -> output/qbr_package.json
  StoryBuilder(period_meta=...).build()
      |
      +- ContentCache.identity(period_meta)      # client, campaign, mode, window, periods, fingerprint
      +- ContentCache.load(identity)
      |     hit  -> reuse content, no API call
      |     miss -> AIEngine.run()
      |               +- ProviderChain.ask(prompt)   # gemini -> groq -> openai
      |               +- strip fences, parse, validate
      |               +- MarkdownExporter.export()
      |               +- write output/ai_response.json
      |            -> ContentCache.store(identity, content, provider)
      |
      +- map sections onto presentation.ai{}
```

`StoryBuilder` gains a `period_meta` constructor argument. It is already
constructed in `main.py` after `analysis` exists, so this needs no reordering.

## Error handling

| Failure | Behaviour |
|---|---|
| One provider out of quota | Failover to next provider; log which one served the request |
| All providers fail | `None` returned; deck builds with template AI text intact |
| Response not valid JSON after fence-strip + 1 retry | Treated as provider failure; failover |
| `qbr_package.json` missing | Cache identity cannot be computed → skip cache, attempt direct generation |
| Cache file corrupt / unreadable | Treated as a miss; regenerate and overwrite |
| Cache write fails (disk/permission) | Warn, continue — generation already succeeded |

## Files touched

**New**
- `ai/provider_chain.py` — ordered provider chain, availability, failover
- `ai/groq_client.py` — Groq via `openai` SDK with `base_url`
- `ai/content_cache.py` — identity, fingerprint, load/store

**Modified**
- `config.py` — `AI_PROVIDER_CHAIN`, `AI_CACHE_MODES`, `AI_FORCE_REGENERATE`; retire `USE_CACHED_AI`
- `ai/ai_engine.py` — use the chain; fence-strip; return provider name alongside content
- `engine/story_builder.py` — accept `period_meta`; consult cache; store on success
- `main.py` — pass `analysis.period_meta` into `StoryBuilder`
- `requirements.txt` — add `openai`. It is installed on the current machine and
  imported by the existing `ai/openai_client.py`, but was never declared, so a
  fresh clone would fail the moment the chain touches Groq or OpenAI.
- `.gitignore` — `output/` is already ignored, so `output/ai_cache/` needs no new rule

## Verification

1. **Cache hit is genuinely free.** Run the pipeline twice, unchanged data, same
   mode. Second run must log a cache hit and make zero API calls. This is the
   check that would have caught the `Generated On` timestamp trap.
2. **Mode scoping.** Full Campaign, then Monthly, then Quarterly on the same
   dataset must produce three distinct cache entries, not one reused three times.
3. **Client/campaign scoping.** Verified by constructing identities directly for
   the same client with two different campaign IDs and asserting the hashes
   differ — cheaper and more definitive than swapping full datasets.
4. **Data change regenerates.** Alter one metric in `qbr_package.json`, confirm
   the fingerprint changes and the run regenerates.
5. **Failover.** Force the primary to fail (invalid `GEMINI_API_KEY`) and confirm
   the chain advances and reports which provider served the request. With no
   fallback key configured, confirm graceful degradation to blank AI and a deck
   that still generates.
6. **Custom mode.** Confirm no cache entry is written and no cache is read.
7. **Existing modes unaffected.** Full pipeline run per mode, exit 0, no new
   `[NOT FOUND]` beyond the 7 known dead keys documented below.

## Deferred: Part C

Audit finding, recorded here so it is not lost. The template contains **37**
`AI_*` text boxes. **16** are wired. The remaining **21** display the template's
own static example text for every client and every run — currently visible in
generated decks as e.g. *"'Medical billing' and 'patient payments' dominate
conversation"* (slide 17), *"All 1,719 targeted accounts showed trending intent
signals"* (slide 18), and *"Twenty organizations scored 99–100 on ML intent"*
(slide 19).

Unwired: `AI_AudienceInterestHeading`, `AI_AudienceInterestSummary`,
`AI_BuyingStageHeading1`, `AI_BuyingStageHeading2`, `AI_BuyingStageSummary`,
`AI_ClosingMessage`, `AI_ContentPerformanceHeading`,
`AI_ContentPerformanceSummary`, `AI_EngagementHeading`, `AI_EngagementSummary`,
`AI_H2Recommendations`, `AI_KeyLearnings`, `AI_OptimizationFooter`,
`AI_OptimizationHighlightsSummary`, `AI_PartnershipSummary`,
`AI_TopAccountsFooter`, `AI_TopAccountsHeading`, `AI_TopAccountsSummary`,
`AI_TrendAnalysisHeading`, `AI_TrendAnalysisSummary`, `AI_ValueAddHeading`.

Dead keys — set by `engine/presentation_data.py` but no such shape exists, so the
content is silently discarded: `AI_RecommendationsSummary`,
`AI_Recommendation1`–`AI_Recommendation5`, `AI_ValueAddSummary`. The template's
real equivalents are the single box `AI_H2Recommendations` and
`AI_PartnershipSummary`.

Part C must extend the prompt schema to produce this content before the boxes can
be wired, then verify formatting slide by slide. It is sequenced after A+B because
iterating on 21 boxes of content requires working generation and correct caching
first.

## Known issue noted in passing

`google.generativeai` now emits a `FutureWarning` that the package is end-of-life
and superseded by `google.genai`. It still functions. Migrating is out of scope
here; the provider-chain abstraction introduced by this design is what makes that
migration a single-file change later.
