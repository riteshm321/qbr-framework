# AI Content Enablement: Provider Fallback + Scoped Caching

**Date:** 2026-08-04
**Status:** Design — awaiting review
**Scope:** Three parts, built in two phases.
**Phase 1** — A (provider fallback) + B (scoped caching).
**Phase 2** — C (wire the 21 unwired AI text boxes, resolve the 7 dead keys).
Phase 2 is sequenced second because iterating on 21 boxes of content requires
working generation and correct caching first.

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
- Every `AI_*` text box in the deck shows content derived from the current
  client's data, or nothing at all — never another campaign's example text.

## Non-goals

- Changing which slides exist or how non-AI (chart/table/KPI) content is computed.
- Paid provider tiers.
- Migrating off the deprecated `google.generativeai` package (see final section).
- Rewriting the template. All fixes are code-side, per the project's standing rule.

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

**The `Metadata["Generated On"]` timestamp is removed from
`export/ai_export.py` outright**, rather than being filtered out at fingerprint
time.

That field is stamped with `datetime.now().strftime("%d-%b-%Y %H:%M")`, so it
changes every minute. Any fingerprint computed over a payload containing it would
change on every run, the cache would never hit, and the feature would burn quota
while appearing to work correctly. Deleting the field is simpler than
special-casing it in the hashing code, and it removes the trap permanently
instead of leaving a landmine for whoever next edits either file.

Nothing consumes the field — verified by grep, it is produced in exactly one place
and read nowhere. Provenance is not lost: each cache entry records its own
`generated_at`.

With the timestamp gone, `output/qbr_package.json` is deterministic for a given
dataset, so the fingerprint is simply a SHA-256 over the whole file, serialized
canonically (`sort_keys=True`). No field exclusions, no special cases.

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

**Phase 1 — new**
- `ai/provider_chain.py` — ordered provider chain, availability, failover
- `ai/groq_client.py` — Groq via `openai` SDK with `base_url`
- `ai/content_cache.py` — identity, fingerprint, load/store

**Phase 1 — modified**
- `config.py` — `AI_PROVIDER_CHAIN`, `AI_CACHE_MODES`, `AI_FORCE_REGENERATE`; retire `USE_CACHED_AI`
- `ai/ai_engine.py` — use the chain; fence-strip; return provider name alongside content
- `export/ai_export.py` — delete the `Generated On` timestamp field
- `engine/story_builder.py` — accept `period_meta`; consult cache; store on success
- `main.py` — pass `analysis.period_meta` into `StoryBuilder`
- `requirements.txt` — add `openai`. It is installed on the current machine and
  imported by the existing `ai/openai_client.py`, but was never declared, so a
  fresh clone would fail the moment the chain touches Groq or OpenAI.
- `.gitignore` — `output/` is already ignored, so `output/ai_cache/` needs no new rule

**Phase 2 — modified**
- `ai/prompt_builder.py` — extend the response schema with the new sections
- `engine/story_builder.py` — parse the new sections onto `presentation.ai`
- `engine/presentation_data.py` — wire the 13 AI boxes and 5 deterministic boxes;
  redirect the 6 salvageable dead keys; remove `AI_RecommendationsSummary`
- `presentation/ppt_engine.py` — add `run_index` to `replace_text()`
- `campaign_types/leadgen.py` — expose the counts the 6 deterministic boxes need,
  if not already present in `period_meta` / `results`

## Phase 1 verification

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
   `[NOT FOUND]` beyond the 7 known dead keys, which Phase 2 resolves.

## Phase 2 — Part C: wire the 21 unwired boxes

The template contains **37** `AI_*` text boxes; **16** are wired. The other **21**
display the template's own example text — from what appears to have been a
healthcare campaign — for every client, every run. Currently shipping in generated
Autodesk decks: *"'Medical billing' and 'patient payments' dominate conversation"*
(slide 17), *"All 1,719 targeted accounts showed trending intent signals"*
(slide 18), *"Twenty organizations scored 99–100 on ML intent"* (slide 19).

### The classification rule

**A box gets AI content if and only if it carries an insight or comment about the
slide's data, chart, or graph.** Anything else — a label, a subtitle stating a
count, boilerplate — is computed in code or left alone. Two reasons: a count
restated by a language model is only a chance to get it wrong, and every
unnecessary section inflates the prompt and the quota cost.

Applying that rule, the 21 split three ways.

**AI-generated (13 boxes)** — each interprets what the slide shows:

| Box | Slide | The insight it carries |
|---|---|---|
| `AI_TrendAnalysisHeading` | 13 | characterises the trajectory the chart shows |
| `AI_TrendAnalysisSummary` | 13 | 3 bullets on what the projection means |
| `AI_ContentPerformanceHeading` | 15 | characterises the spread across assets |
| `AI_ContentPerformanceSummary` | 15 | 3 bullets on what the spread tells us |
| `AI_AudienceInterestHeading` | 17 | which themes dominate the topic mix |
| `AI_AudienceInterestSummary` | 17 | what that concentration implies |
| `AI_EngagementSummary` | 18 | 3 bullets reading the funnel |
| `AI_TopAccountsFooter` | 19 | what the intent scores imply for outreach |
| `AI_OptimizationFooter` | 23 | the bottom-line lever |
| `AI_KeyLearnings` | 24 | 5 titled learnings |
| `AI_H2Recommendations` | 25 | 5 forward actions |
| `AI_PartnershipSummary` | 26 | what the intent layer means for the partnership |
| `AI_ValueAddHeading` | 26 | characterises the value delivered beyond core leads |

Note `AI_TrendAnalysisHeading` is AI, not computed: "growth trajectory" is a claim
about direction that would be wrong on a declining campaign, and it sits in the
same role as the slide-15 and slide-17 headings above it.

**Deterministic — computed in code, no AI (5 boxes)** — labels and boilerplate,
none of which interpret anything:

| Box | Slide | Content | Why not AI |
|---|---|---|---|
| `AI_BuyingStageHeading1` | 21 | label naming the grouped stages | names which stages the adjacent KPI counts |
| `AI_BuyingStageHeading2` | 21 | as above, second grouping | same |
| `AI_BuyingStageSummary` | 21 | subtitle stating the account count | a count, not a comment |
| `AI_OptimizationHighlightsSummary` | 23 | subtitle with period labels | template sentence + period name |
| `AI_ClosingMessage` | 27 | closing boilerplate | no data reference at all |

The two currently period-hardcoded ones must also drop their directional
assumptions: "Turning H1 signals into H2 action" and "build on H1 momentum" both
presume growth, so the computed versions use direction-neutral wording.

**Leave as-is (3 boxes)** — inspected and confirmed to contain no client data, no
figures, and no directional claim, so there is nothing to go stale:
`AI_EngagementHeading` ("From intent-based targeting to active engagement"),
`AI_TopAccountsHeading` ("TOP ENGAGED ACCOUNTS (BY LEADS)"),
`AI_TopAccountsSummary` ("The organizations showing the strongest engagement and
buying intent").

### Resolving the 7 dead keys

The content for most of these is already generated and already parsed — it is
merely written to shape names that do not exist. Redirecting is the fix; only one
is genuinely surplus.

| Dead key | Resolution |
|---|---|
| `AI_Recommendation1`–`5` | Redirect to `AI_H2Recommendations` paragraphs 1–5. `Recommendations.actions` already exists in the prompt schema and is already parsed by `story_builder.py` — nothing new to generate. |
| `AI_ValueAddSummary` | Redirect to `AI_PartnershipSummary` paragraph 2. |
| `AI_RecommendationsSummary` | **Remove.** No target box exists, and its content duplicates the five actions. Slide 25's paragraph 0 is the section title, not narrative. |

### Paragraph and run structure

These boxes are not single-run text boxes, and writing them naively would destroy
the template's formatting. Verified structure:

| Box | Structure |
|---|---|
| `AI_EngagementSummary`, `AI_ContentPerformanceSummary`, `AI_TrendAnalysisSummary` | para 0 = bold fixed label (keep), para 1 = blank spacer, paras 2–4 = three body lines |
| `AI_KeyLearnings` | five pairs — even paras = bold title, odd paras = detail |
| `AI_H2Recommendations` | para 0 = section title (keep). Paras 1–5 have **two runs**: run 0 = bold `"01   "` number prefix (keep), run 1 = the text |
| `AI_PartnershipSummary` | para 0 = bold fixed label (keep), para 2 = body |

**Engine requirement:** `PowerPointEngine.replace_text()` currently writes
`paragraphs[paragraph_index].runs[0]`. `AI_H2Recommendations` needs run 1, so a
`run_index` parameter is required. Without it, writing a recommendation would
overwrite the `"01"` numbering.

### Prompt schema extension

New sections, added to `ai/prompt_builder.py`'s schema. `Recommendations.actions`
and `ValueAdd` already exist and are reused rather than duplicated.

```
"TrendAnalysis":        { "heading": "", "bullets": [3] }
"ContentPerformance":   { "heading": "", "bullets": [3] }
"AudienceInterest":     { "heading": "", "summary": "" }
"Engagement":           { "bullets": [3] }
"TopAccounts":          { "footer": "" }
"OptimizationHighlights": { "footer": "" }
"KeyLearnings":         { "items": [ { "title": "", "detail": "" } x5 ] }
"Partnership":          { "summary": "" }
"ValueAdd":             { "heading": "", "summary": "" }   # heading added
```

Bullet and item counts are fixed to match the template's paragraph slots. The
prompt states these counts explicitly, and the wiring code tolerates receiving
fewer (remaining paragraphs are blanked, matching the table-row behaviour
established in `replace_table`) or more (extras dropped).

### Phase 2 verification

Content quality cannot be asserted from a console log. Each of the 11 affected
slides (13, 15, 17, 18, 19, 21, 23, 24, 25, 26, 27) is exported to PNG via
PowerPoint COM and inspected for: text fitting its box without overflow or
clipping, no leftover template sentences, numbers in the narrative agreeing with
the numbers in the adjacent charts and tables, and preserved bold/size formatting
on the fixed label paragraphs and number prefixes.

## Known issue noted in passing

`google.generativeai` now emits a `FutureWarning` that the package is end-of-life
and superseded by `google.genai`. It still functions. Migrating is out of scope
here; the provider-chain abstraction introduced by this design is what makes that
migration a single-file change later.
