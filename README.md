# llms.txt for Gies College of Business

A working implementation of the [llms.txt standard](https://llmstxt.org/) for [Gies College of Business](https://giesbusiness.illinois.edu) at the University of Illinois Urbana-Champaign.

## What's in this repo

| File | Purpose |
|------|---------|
| [`llms.txt`](llms.txt) | Compact index — key pages and programs with descriptions (~3K tokens) |
| [`llms-full.txt`](llms-full.txt) | Comprehensive reference — all programs, AI initiatives, facilities, career resources (~5K tokens) |
| [`llms-txt-generator.py`](llms-txt-generator.py) | Python script that crawls a website (honoring robots.txt + sitemap.xml) and generates an enhanced llms.txt using the Gemini API |
| [`llms-txt-benchmark.py`](llms-txt-benchmark.py) | **Benchmark tool** — empirically measures whether llms.txt improves AI responses about your site (blinded LLM-as-judge) |
| [`validate.py`](validate.py) | Lints `llms.txt` / `llms-full.txt` against the llmstxt.org spec |
| [`llms-txt-one-pager-gies.md`](llms-txt-one-pager-gies.md) | One-pager: should Gies adopt llms.txt? Research, sources, and recommendation |

## llms.txt format

The files follow the [official spec](https://llmstxt.org/) proposed by Jeremy Howard (Answer.AI):

```
# Site Name

> Blockquote summary of the site

Optional descriptive paragraphs.

## Section Name

- [Page Title](https://url): Brief description of the page

## Optional

- [Lower-priority pages](https://url): Can be skipped for shorter context
```

When deployed, `llms.txt` lives at the website root (e.g., `giesbusiness.illinois.edu/llms.txt`) and gives AI assistants a curated map of the site's most important content.

## Generator script

The included Python script can crawl any website and produce an llms.txt file. It
honors `robots.txt`, seeds the crawl from `sitemap.xml` when available, normalizes
URLs (drops fragments and tracking params), and stays strictly on the target
host/path. With `--full` it also fetches each page and extracts its main text to
build a real `llms-full.txt` (page content, not just a link map).

```bash
# Install dependencies
pip install -r requirements.txt

# Basic usage (crawl + Gemini enhancement)
export GOOGLE_API_KEY=your_key
./llms-txt-generator.py https://your-site.com --name "Your Site" --max-pages 200

# Also produce llms-full.txt with extracted page content
./llms-txt-generator.py https://your-site.com --full

# Skip Gemini enhancement (basic site map only)
./llms-txt-generator.py https://your-site.com --skip-enhance
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `url` (positional) | `https://giesbusiness.illinois.edu` | Website to crawl |
| `--name` | derived from URL | Site name for the H1 title |
| `--max-pages` | 150 | Maximum pages to crawl |
| `--delay` | 0.2 | Seconds between requests |
| `--output-dir` | `.` | Directory for the generated files |
| `--skip-enhance` | false | Skip Gemini API enhancement |
| `--full` | false | Also generate `llms-full.txt` with extracted page content |
| `--gemini-model` | `gemini-2.0-flash` | Gemini model used for enhancement |
| `--ignore-robots` | false | Do not honor `robots.txt` (use responsibly) |

## Validating output

```bash
./validate.py                       # checks llms.txt and llms-full.txt in cwd
./validate.py path/to/llms.txt
```

`validate.py` checks the basics required by the spec: a single H1 title, a
blockquote summary, H2-only section headings (in `llms.txt`), well-formed
`- [text](url): description` link items, and no stray code fences. It exits
non-zero on any problem, so it works as a CI check.

## Benchmark tool

Does llms.txt actually improve AI responses? Don't take our word for it — measure it.

The benchmark tool runs controlled experiments: for each test query, it asks an AI assistant the same question *with* and *without* llms.txt context, then uses an LLM-as-judge to score both responses on accuracy, completeness, specificity, and actionability.

To keep the numbers honest, the judge sees the two answers in a **randomized order with neutral labels** ("Response A/B") and is **not told which one used llms.txt** — and you can run the judge on a **different model/provider** than the one being tested (`--judge-api`) to avoid self-preference bias. Use `--trials` to repeat each query and average.

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Claude (recommended)
export ANTHROPIC_API_KEY=your_key
./llms-txt-benchmark.py

# Run with OpenAI
export OPENAI_API_KEY=your_key
./llms-txt-benchmark.py --api openai

# Run with Gemini (uses same key as the generator)
export GOOGLE_API_KEY=your_key
./llms-txt-benchmark.py --api gemini

# Cross-model: Claude answers, GPT judges (reduces self-preference bias)
./llms-txt-benchmark.py --api claude --judge-api openai

# Average over 3 trials per query for a more stable estimate
./llms-txt-benchmark.py --trials 3

# Use llms-full.txt for richer context
./llms-txt-benchmark.py --full-txt llms-full.txt

# Auto-generate test queries from your llms.txt content
./llms-txt-benchmark.py --auto-queries

# Quick test with 3 queries
./llms-txt-benchmark.py --max-queries 3

# Custom test queries
./llms-txt-benchmark.py --queries my-queries.json
```

### Benchmark options

| Flag | Default | Description |
|------|---------|-------------|
| `--llms-txt` | `llms.txt` | Path to llms.txt file |
| `--full-txt` | none | Path to llms-full.txt (used as context if provided) |
| `--api` | `auto` | Backend that produces the answers: `claude`, `openai`, `gemini`, or `auto` |
| `--judge-api` | `same` | Backend for the judge: `claude`, `openai`, `gemini`, `auto`, or `same` (as `--api`) |
| `--gen-model` | backend default | Override the answer model name |
| `--judge-model` | backend default | Override the judge model name |
| `--trials` | 1 | Repeat each query N times and average the scores |
| `--seed` | random | Seed for the randomized A/B ordering (reproducibility) |
| `--queries` | none | Custom test queries JSON file |
| `--auto-queries` | false | Auto-generate queries from llms.txt content |
| `--output` | `benchmark-report.md` | Output report file |
| `--delay` | 1.0 | Seconds between API calls |
| `--max-queries` | all | Limit number of queries (for quick tests) |

### Custom queries format

```json
[
  {
    "query": "What online MBA programs does your school offer?",
    "category": "prospective_student",
    "key_facts": ["iMBA", "Coursera", "affordable", "STEM-designated"]
  }
]
```

The tool produces a markdown report (`benchmark-report.md`) with per-query scores, response excerpts, and an aggregate summary showing the percentage improvement from llms.txt.

## Who's using llms.txt

Anthropic, Cloudflare, Stripe, Vercel, Supabase, Shopify, NVIDIA, and 844,000+ other websites (BuiltWith, Oct 2025). No major university has adopted it yet — this repo is a proof of concept for Gies to be first.

## Maintenance

Regenerate quarterly or after significant website changes. The generator script handles the crawl-and-enhance cycle automatically.
