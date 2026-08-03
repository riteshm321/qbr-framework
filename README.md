# ML QBR Framework

An engine that turns Madison Logic campaign exports into a fully populated
Quarterly Business Review PowerPoint deck — no per-client or per-quarter
hardcoding. Drop in a client's reports, pick an analysis window, and it
detects the datasets, computes every KPI/table/chart, and fills the
existing QBR template automatically.

**Vision for the finished tool:** drop the campaign's report exports into
`input/`, run the packaged application, get a finished QBR deck out — no
setup, no prompts beyond picking the analysis window. Today that's a
Python script you run with `python main.py`; packaging it as a
standalone executable is planned. The analysis engine is also built to
extend to every Madison Logic campaign type — **Lead Gen** (built out
today), **Display**, **Lead Gen + Display**, **Audio**, and **CTV** (all
planned) — so the same tool covers any campaign type a client is running,
not just lead gen.

## What it does

1. **Loads** whatever reports you drop into `input/` and classifies each
   one by its column structure (`core/detector.py`) — not by filename —
   so it doesn't matter what the exports happen to be named.
2. **Resolves a reporting period** (`core/period_resolver.py`) from one
   of four analysis modes (see below), auto-detected from the actual
   date range in the data.
3. **Runs the analysis** (`campaign_types/leadgen.py`, today's built-out
   analyzer) — KPIs, funnel, buying-stage distribution, trending
   topics/accounts, asset performance, period-over-period comparisons,
   and a trend/forecast projection.
4. **Generates AI narrative content** (executive summary, recommendations,
   speaker notes, etc.) via Gemini, cached to `output/ai_response.json`
   so you aren't re-billed on every run.
5. **Builds the deck** (`presentation/`) by reshaping and filling the
   PowerPoint template — adding or removing per-period detail slides,
   resizing comparison tables/charts, and writing every chart/table/text
   placeholder — entirely through `python-pptx`/OOXML. **The template
   file itself is never edited by hand** — only the code that fills it.
6. Also exports a companion Excel workbook and a set of standalone chart
   images.

## Analysis modes

Picked interactively when you run `main.py`:

| Mode | What it does |
|---|---|
| **Full Campaign** | One slot covering the entire campaign; the comparison/trend slides break it down by calendar month (or quarter, if 4+ months) automatically. |
| **Month over Month** | One detail slide per real calendar month with data (empty months are skipped). Beyond `MAX_MONTHLY_DETAIL_SLIDES` (default 6), the overflow is bucketed into the comparison view only. |
| **Quarter over Quarter** | Every real calendar quarter in the campaign, analyzed automatically — no manual quarter picking. Falls back to Month over Month if the data doesn't span at least 2 full quarters. |
| **Custom Date Range** | You supply a single start/end date. That period gets one detail slide; the comparison/trend slides auto-bisect it into "Period 1"/"Period 2" for a before/after view. |

## Project structure

```
ai/              Gemini client, prompt building, AI response -> Markdown export
campaign_types/  Per-campaign-type analyzers (LeadGen is built out; Display/Audio/CTV are placeholder stubs)
chart_engine/    Standalone chart image export
core/            Report loading/cleaning/validation, date splitting, period resolution
datasets/        Typed wrappers around individual report datasets
engine/          Campaign/analysis-type selection, presentation data model, AI story building
export/          AI content export (JSON/prompt dump)
presentation/    PowerPoint template filling + slide/table reshaping (python-pptx + OOXML)
workbook/        Excel workbook export
templates/       The QBR PowerPoint template the engine fills (tracked in git — required to run)
input/           Drop this client's raw report exports here (gitignored contents)
logs/            (gitignored contents)
output/          Generated deck, workbook, charts, AI exports (gitignored, regenerated per run)
```

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Gemini API key:

```
GEMINI_API_KEY=your-key-here
```

(AI generation is cache-first — see below — so this is only required the
very first time, or after deleting `output/ai_response.json`.)

## Running

1. Put the client's report exports (Lead Detail, Account Engagement,
   Trending Topics, Trending Accounts, Asset Delivery, and optionally
   Target Account List History) into `input/`.
2. Run:

   ```bash
   python main.py
   ```
3. Choose an analysis mode when prompted. Custom Date Range will also
   ask for a start/end date.
4. Find the generated deck at `output/Generated_QBR.pptx`, the workbook
   at `output/QBR_Workbook.xlsx`, and chart images under
   `output/charts/`.

### AI content caching

`config.USE_CACHED_AI` (default `True`) means the AI narrative is
generated once and reused from `output/ai_response.json` on every
subsequent run, regardless of which client/period you're analyzing next.
Delete that file (or set `USE_CACHED_AI = False`) to force fresh AI
content — useful when you've changed to a genuinely different client's
data.

## Roadmap

This is the direction the project is headed — not yet built:

- **Standalone executable.** Package the tool so a user just adds the
  client's report exports to `input/` and runs the app — no Python
  environment, no manual dependency install.
- **Full campaign-type coverage.** Extend the analyzer layer beyond Lead
  Gen to also support:
  - Display
  - Lead Gen + Display (combined)
  - Audio
  - CTV

  `campaign_types/audio.py`, `campaign_types/ctv.py`, and
  `campaign_types/display.py` exist today as empty placeholders for this.

## Ground rules for contributing

- **Never edit the PowerPoint template** (`templates/LeadGen_QBR_Template.pptx`)
  directly — adapt the code that fills it instead.
- **No hardcoded client/campaign/period logic.** Everything client- or
  period-specific must be derived from the loaded reports at runtime.
- Business logic (KPI calculations, period grouping, trend projection)
  belongs in the analyzer layer (`campaign_types/leadgen.py`), not in
  the presentation layer.
