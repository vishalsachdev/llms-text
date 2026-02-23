# llms.txt for Gies College of Business

A working implementation of the [llms.txt standard](https://llmstxt.org/) for [Gies College of Business](https://giesbusiness.illinois.edu) at the University of Illinois Urbana-Champaign.

## What's in this repo

| File | Purpose |
|------|---------|
| [`llms.txt`](llms.txt) | Compact index — key pages and programs with descriptions (~3K tokens) |
| [`llms-full.txt`](llms-full.txt) | Comprehensive reference — all programs, AI initiatives, facilities, career resources (~5K tokens) |
| [`llms-txt-generator.py`](llms-txt-generator.py) | Python script that crawls a website and generates an enhanced llms.txt using the Gemini API |
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

The included Python script can crawl any website and produce an llms.txt file:

```bash
# Install dependencies
pip install -r requirements.txt

# Basic usage (crawl + Gemini enhancement)
export GOOGLE_API_KEY=your_key
./llms-txt-generator.py https://your-site.com --name "Your Site" --max-pages 200

# Skip Gemini enhancement (basic site map only)
./llms-txt-generator.py https://your-site.com --skip-enhance
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `url` (positional) | `https://giesbusiness.illinois.edu` | Website to crawl |
| `--name` | derived from URL | Site name for output |
| `--max-pages` | 150 | Maximum pages to crawl |
| `--delay` | 0.2 | Seconds between requests |
| `--skip-enhance` | false | Skip Gemini API enhancement |

## Who's using llms.txt

Anthropic, Cloudflare, Stripe, Vercel, Supabase, Shopify, NVIDIA, and 844,000+ other websites (BuiltWith, Oct 2025). No major university has adopted it yet — this repo is a proof of concept for Gies to be first.

## Maintenance

Regenerate quarterly or after significant website changes. The generator script handles the crawl-and-enhance cycle automatically.
