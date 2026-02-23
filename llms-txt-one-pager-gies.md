# Should Gies Adopt llms.txt? — A One-Pager

**Date:** February 2026 | **Audience:** Gies College of Business Leadership & Web Team

---

## What is llms.txt?

Proposed in September 2024 by Jeremy Howard (co-founder, Answer.AI), `llms.txt` is a markdown file placed at a website's root (e.g., `giesbusiness.illinois.edu/llms.txt`) that provides AI systems — ChatGPT, Claude, Gemini — with a curated, structured map of a site's most important content. Think of it as *robots.txt for the AI age*: robots.txt tells crawlers what **not** to access; llms.txt tells language models what's **worth** accessing.

## Current Adoption Landscape

| Signal | Detail |
|--------|--------|
| **Scale** | 844,000+ websites have implemented llms.txt (BuiltWith, Oct 2025) |
| **Notable adopters** | Anthropic, Cloudflare, Stripe, Vercel, Supabase, Shopify, NVIDIA, Zapier |
| **Higher ed** | No major university adoption found in research |
| **AI platform support** | Mixed — OpenAI/Anthropic/Google pledged to respect it (Aug 2025), but Google's John Mueller says no AI system at Google currently uses it |
| **Crawler evidence** | Profound (GEO analytics firm) shows OpenAI and Microsoft crawlers actively fetching llms.txt files |

**Bottom line:** The standard is gaining traction in tech/developer ecosystems but remains unproven for driving AI search visibility. No major LLM provider has confirmed it influences answer generation.

## Where Gies Stands Today

| Area | Current State |
|------|--------------|
| **robots.txt** | Wide open — allows all crawlers, no AI-specific rules |
| **llms.txt** | Does not exist (404 at `/llms.txt`) |
| **Sitemap** | Standard XML sitemap exists |
| **AI initiatives** | Strong — Google Gemini partnership, AI avatars, Cleo interview simulator, Alma chatbot for iMBA, AI-focused curriculum |
| **Web optimization for agents** | None detected — no structured metadata, `.well-known` resources, or agent-friendly content layers |

Gies is a **leader in AI education** but has done **nothing to make its own website AI-readable**. There's a gap between the college's AI brand and its web infrastructure.

## The Case FOR Adopting llms.txt at Gies

1. **Brand alignment** — Gies markets itself as an AI-first business school. Having an llms.txt file signals technical credibility to prospective students, faculty recruits, and partners who will notice.

2. **Prospective student discovery** — Students increasingly ask AI assistants "What MBA programs focus on AI?" or "Tell me about Gies online programs." A curated llms.txt ensures the right pages (programs, admissions, outcomes) surface accurately.

3. **Low cost, low risk** — We already built a generator (`llms-txt-generator.py`) that crawls the Gies site and produces an enhanced llms.txt via Gemini. Deployment is a single file upload.

4. **First-mover in higher ed** — No major university appears to have adopted llms.txt yet. Gies could own this narrative.

5. **Future-proofing** — Even if current LLMs don't actively consume it, the trajectory is clear. Early adoption means the file is refined and ready when platforms formalize support.

## The Case AGAINST (or for caution)

1. **No confirmed impact on AI answers** — Google explicitly says they don't use it. No proof it influences ChatGPT or Claude responses.

2. **Maintenance burden** — The file must stay current as programs, pages, and leadership change. Stale content is worse than none.

3. **Could resemble the `<meta keywords>` era** — Some SEO experts compare it to the discredited keywords meta tag: easy to manipulate, hard to trust.

## Recommendation

**Adopt it — but frame it correctly.** Don't expect SEO miracles. Instead:

| Action | Effort | Impact |
|--------|--------|--------|
| Deploy `llms.txt` to `giesbusiness.illinois.edu/llms.txt` using our existing generator | **Low** — 1 hour | Immediate AI discoverability signal |
| Add a `llms-full.txt` with comprehensive program/page detail (the Anthropic model) | **Medium** — 1 day | Deeper context for AI assistants |
| Update `robots.txt` with explicit AI crawler permissions (GPTBot, ClaudeBot, etc.) | **Low** — 30 min | Clear stance on AI crawling |
| Set a quarterly regeneration cadence using the generator script | **Low** — cron job | Keeps content fresh |
| Announce as part of Gies' AI leadership narrative | **Low** — comms | Brand differentiation |

**Total investment:** ~1-2 days of web team effort for a meaningful signal that aligns with Gies' AI-first positioning — and positions the college as the first major business school to adopt the standard.

---

## Working Demo

We've built ready-to-deploy files in our GitHub repo:

**[github.com/vishalsachdev/llms-text](https://github.com/vishalsachdev/llms-text)**

| File | Tokens | Purpose |
|------|--------|---------|
| [`llms.txt`](https://github.com/vishalsachdev/llms-text/blob/main/llms.txt) | ~3K | Compact index for quick AI context |
| [`llms-full.txt`](https://github.com/vishalsachdev/llms-text/blob/main/llms-full.txt) | ~5K | Comprehensive reference with all programs, AI initiatives, and details |

Both files follow the [official llms.txt specification](https://llmstxt.org/) and can be deployed to `giesbusiness.illinois.edu` with a single file upload.

---

## Simulated Demo: Before vs. After

Here's what happens when a prospective student asks an AI assistant about Gies — with and without llms.txt available as context.

### Prompt: *"I'm interested in an online MBA that focuses on AI. What does Gies offer?"*

#### WITHOUT llms.txt (AI relies on general web crawl)

> Gies College of Business at the University of Illinois offers an online MBA called
> the iMBA. It's available through Coursera and is considered affordable compared to
> other programs. I don't have specific details about their AI curriculum — you may
> want to check their website for the latest information.

*Generic, hedged, incomplete. No mention of AI integration, Google partnership, or specific resources.*

#### WITH llms.txt (AI has structured context)

> Gies College of Business offers the **iMBA**, a fully online, STEM-designated MBA
> through Coursera — one of the most affordable accredited online MBAs available.
>
> What makes Gies stand out for AI:
> - **AI-integrated curriculum** across all programs, not just electives
> - **Google partnership** giving students access to Gemini and NotebookLM
> - **AI-driven facilities** — Wymer Hall has sound stages for AI-powered course production
> - **Cleo** — an AI interview simulator for career prep
> - **Stackable credentials** — you can start with an iAcademy or certificate and build toward the full MBA
>
> You can explore more at their [AI initiatives page](https://giesbusiness.illinois.edu/about/artificial-intelligence)
> or [talk to an advisor](https://giesbusiness.illinois.edu/graduate-hub/talk-to-an-advisor).

*Specific, accurate, action-oriented. Surfaces Gies' actual differentiators and links to the right pages.*

### Why this matters

The "without" response is what prospective students get today. The "with" response is what they'd get if Gies deployed llms.txt. The difference is the difference between a student clicking through to learn more — or moving on to a competitor whose AI presence is better.

---

## Sources

- [The Complete Guide to llms.txt](https://getpublii.com/blog/llms-txt-complete-guide.html) — Publii
- [What Is llms.txt? (2026 Guide)](https://www.bluehost.com/blog/what-is-llms-txt/) — Bluehost
- [llms.txt Adoption Stalls as Major AI Platforms Ignore Standard](https://ppc.land/llms-txt-adoption-stalls-as-major-ai-platforms-ignore-proposed-standard/) — PPC Land
- [Is llms.txt Dead? Current State of Adoption](https://llms-txt.io/blog/is-llms-txt-dead) — llms-txt.io
- [Real llms.txt Examples from Leading Tech Companies](https://www.mintlify.com/blog/real-llms-txt-examples) — Mintlify
- [What Is llms.txt, and Should You Care?](https://ahrefs.com/blog/what-is-llms-txt/) — Ahrefs
- [llms.txt: The Emerging Standard Reshaping AI-First Content Strategy](https://scalemath.com/blog/llms-txt/) — ScaleMath
- [llms.txt in 2026: What It Does (and Doesn't) Do](https://searchsignal.online/blog/llms-txt-2026) — Search Signal
- [How a Gies Business Chatbot Is Transforming Learning](https://giesbusiness.illinois.edu/news/2025/04/10/how-a-gies-business-chatbot-is-transforming-learning-and-winning-awards) — Gies News
- [Gies AI Initiatives Page](https://giesbusiness.illinois.edu/about/artificial-intelligence) — Gies College of Business
- [The Value of llms.txt: Hype or Real?](https://www.mintlify.com/blog/the-value-of-llms-txt-hype-or-real) — Mintlify
- [What Is LLMs.txt? Do You Need One?](https://neilpatel.com/blog/llms-txt-files-for-seo/) — Neil Patel
