#!/usr/bin/env python3
"""
llms.txt Benchmark — Empirical Validation for llms.txt Effectiveness
--------------------------------------------------------------------
Tests whether an llms.txt file actually improves AI assistant responses
about a website by running controlled before/after comparisons with
LLM-as-judge scoring.

Supports Claude (Anthropic), GPT (OpenAI), and Gemini (Google) APIs.
Auto-detects which API keys are available.

Usage:
    # Auto-detect available API and use default Gies test queries
    ./llms-txt-benchmark.py

    # Specify files and API
    ./llms-txt-benchmark.py --llms-txt llms.txt --full-txt llms-full.txt --api claude

    # Use custom test queries from a JSON file
    ./llms-txt-benchmark.py --queries my-queries.json

    # Auto-generate test queries from the llms.txt content
    ./llms-txt-benchmark.py --auto-queries --llms-txt llms.txt
"""

import argparse
import json
import os
import sys
import time
import datetime
import re
import statistics
from pathlib import Path


# ---------------------------------------------------------------------------
# API Clients
# ---------------------------------------------------------------------------

def call_claude(prompt, system=None, model="claude-sonnet-4-20250514", max_tokens=1024):
    """Call the Anthropic Claude API."""
    import anthropic
    client = anthropic.Anthropic()
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text


def call_openai(prompt, system=None, model="gpt-4o", max_tokens=1024):
    """Call the OpenAI API."""
    import openai
    client = openai.OpenAI()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens)
    return response.choices[0].message.content


def call_gemini(prompt, system=None, model="gemini-1.5-pro-latest", max_tokens=1024):
    """Call the Google Gemini API via REST."""
    import requests as req
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    text = f"{system}\n\n{prompt}" if system else prompt
    data = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens},
    }
    resp = req.post(f"{url}?key={api_key}", headers={"Content-Type": "application/json"}, json=data)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


API_BACKENDS = {
    "claude": {"fn": call_claude, "env_key": "ANTHROPIC_API_KEY", "label": "Claude (Anthropic)"},
    "openai": {"fn": call_openai, "env_key": "OPENAI_API_KEY", "label": "GPT (OpenAI)"},
    "gemini": {"fn": call_gemini, "env_key": "GOOGLE_API_KEY", "label": "Gemini (Google)"},
}


def detect_api():
    """Auto-detect available API from environment variables. Preference: Claude > OpenAI > Gemini."""
    for name in ("claude", "openai", "gemini"):
        if os.environ.get(API_BACKENDS[name]["env_key"]):
            return name
    return None


# ---------------------------------------------------------------------------
# Default test queries (Gies-focused, but illustrative for any university)
# ---------------------------------------------------------------------------

DEFAULT_QUERIES = [
    {
        "query": "I'm interested in an online MBA that focuses on AI. What does Gies College of Business offer?",
        "category": "prospective_student",
        "key_facts": [
            "iMBA program",
            "offered via Coursera",
            "affordable/STEM-designated",
            "AI-integrated curriculum",
            "Google partnership (Gemini, NotebookLM)",
            "Wymer Hall / AI course production",
        ],
    },
    {
        "query": "What experiential learning opportunities does Gies have for undergrad business students?",
        "category": "prospective_student",
        "key_facts": [
            "Illinois Business Consulting",
            "MakerLab",
            "iVenture Accelerator",
            "experiential learning with corporate partners",
            "30+ student organizations",
        ],
    },
    {
        "query": "Tell me about the MS in Business Analytics at the University of Illinois.",
        "category": "prospective_student",
        "key_facts": [
            "MSBA program",
            "STEM-designated",
            "data science / machine learning focus",
            "Gies College of Business",
        ],
    },
    {
        "query": "How is Gies College of Business using artificial intelligence in its programs?",
        "category": "ai_initiatives",
        "key_facts": [
            "AI-integrated curriculum across all programs",
            "Google partnership",
            "Cleo (AI interview simulator)",
            "Alma (AI chatbot for iMBA)",
            "AI avatars for course content",
            "Wymer Hall AI studios",
        ],
    },
    {
        "query": "What career support does Gies provide to its students?",
        "category": "career",
        "key_facts": [
            "Career & Professional Development office",
            "Gies Professional Pathway",
            "corporate recruiting",
            "career coaching / interview prep",
        ],
    },
    {
        "query": "I'm a company looking to recruit business students from UIUC. How do I partner with Gies?",
        "category": "corporate",
        "key_facts": [
            "Corporate Partners program",
            "on-campus recruiting / career fairs",
            "Illinois Business Consulting projects",
            "workforce development",
        ],
    },
    {
        "query": "What PhD programs does Gies College of Business offer?",
        "category": "prospective_student",
        "key_facts": [
            "PhD in Accountancy",
            "PhD in Business Administration",
            "PhD in Finance",
            "research-focused",
        ],
    },
    {
        "query": "Does Gies have any stackable credentials or certificates I can earn before committing to a full degree?",
        "category": "prospective_student",
        "key_facts": [
            "Gies Professional Credentials",
            "iAcademies",
            "stackable toward full degrees",
            "graduate certificates",
        ],
    },
]


# ---------------------------------------------------------------------------
# Query auto-generation from llms.txt content
# ---------------------------------------------------------------------------

def auto_generate_queries(llms_content, call_fn):
    """Use the AI API to generate test queries from llms.txt content."""
    prompt = f"""Below is the contents of an llms.txt file for a website. Generate 8 realistic test queries
that a prospective student, employer, or researcher might ask an AI assistant about this organization.

For each query, also list 3-5 key facts from the llms.txt that a good answer should include.

Return ONLY valid JSON — an array of objects with keys: "query", "category", "key_facts" (array of strings).

llms.txt content:
---
{llms_content}
---"""
    raw = call_fn(prompt, system="You are a helpful assistant that returns only valid JSON.", max_tokens=2048)
    # Extract JSON from response (handle markdown code fences)
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if json_match:
        raw = json_match.group(1)
    # Try to find array in response
    bracket_start = raw.find("[")
    bracket_end = raw.rfind("]")
    if bracket_start != -1 and bracket_end != -1:
        raw = raw[bracket_start : bracket_end + 1]
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Benchmarking core
# ---------------------------------------------------------------------------

def run_query_pair(query_text, llms_content, call_fn, delay=1.0):
    """Run a single query with and without llms.txt context. Returns (baseline, enhanced) response texts."""
    # Baseline: no context
    baseline_prompt = query_text
    baseline_system = (
        "You are a helpful AI assistant answering questions about universities and business schools. "
        "Answer based on your general knowledge. If you're unsure about specific details, say so."
    )
    baseline = call_fn(baseline_prompt, system=baseline_system)
    time.sleep(delay)

    # Enhanced: with llms.txt context
    enhanced_system = (
        "You are a helpful AI assistant answering questions about universities and business schools. "
        "You have been provided with the following structured reference about the institution. "
        "Use it to give accurate, specific, and actionable answers.\n\n"
        f"--- REFERENCE ---\n{llms_content}\n--- END REFERENCE ---"
    )
    enhanced = call_fn(query_text, system=enhanced_system)
    time.sleep(delay)

    return baseline, enhanced


JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator assessing AI assistant responses about a university/business school.

A user asked: "{query}"

Here are the key facts that a good answer should include:
{key_facts_formatted}

---

**Response A (Baseline — no structured context provided):**
{baseline}

---

**Response B (Enhanced — llms.txt structured context provided):**
{enhanced}

---

Score EACH response on a scale of 1-10 for each criterion:
1. **Accuracy** — Are the stated facts correct? No hallucinations?
2. **Completeness** — How many of the key facts are covered?
3. **Specificity** — Does it give concrete details (program names, URLs, features) vs. vague generalities?
4. **Actionability** — Does it help the user take a next step (links, contact info, clear recommendations)?

Return ONLY valid JSON with this exact structure:
{{
  "baseline": {{"accuracy": N, "completeness": N, "specificity": N, "actionability": N, "notes": "brief explanation"}},
  "enhanced": {{"accuracy": N, "completeness": N, "specificity": N, "actionability": N, "notes": "brief explanation"}}
}}"""


def judge_responses(query_obj, baseline, enhanced, call_fn):
    """Use LLM-as-judge to score baseline vs enhanced responses."""
    key_facts_formatted = "\n".join(f"- {f}" for f in query_obj["key_facts"])
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        query=query_obj["query"],
        key_facts_formatted=key_facts_formatted,
        baseline=baseline,
        enhanced=enhanced,
    )
    raw = call_fn(
        prompt,
        system="You are a rigorous, impartial evaluator. Return only valid JSON. Be strict in scoring.",
        max_tokens=1024,
    )
    # Extract JSON
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if json_match:
        raw = json_match.group(1)
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end != -1:
        raw = raw[brace_start : brace_end + 1]
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

CRITERIA = ["accuracy", "completeness", "specificity", "actionability"]


def generate_report(results, api_label, llms_file, full_file):
    """Generate a markdown benchmark report."""
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Aggregate scores
    baseline_scores = {c: [] for c in CRITERIA}
    enhanced_scores = {c: [] for c in CRITERIA}
    for r in results:
        for c in CRITERIA:
            baseline_scores[c].append(r["scores"]["baseline"][c])
            enhanced_scores[c].append(r["scores"]["enhanced"][c])

    lines = []
    lines.append("# llms.txt Benchmark Report")
    lines.append("")
    lines.append(f"> Generated {today} using {api_label}")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- **llms.txt file:** `{llms_file}`")
    if full_file:
        lines.append(f"- **llms-full.txt file:** `{full_file}`")
    lines.append(f"- **Test queries:** {len(results)}")
    lines.append(f"- **AI backend:** {api_label}")
    lines.append(f"- **Scoring method:** LLM-as-judge (same backend)")
    lines.append("")

    # Summary table
    lines.append("## Summary Scores (1-10 scale)")
    lines.append("")
    lines.append("| Criterion | Baseline (no context) | With llms.txt | Improvement |")
    lines.append("|-----------|----------------------|---------------|-------------|")
    total_baseline = []
    total_enhanced = []
    for c in CRITERIA:
        b_avg = statistics.mean(baseline_scores[c])
        e_avg = statistics.mean(enhanced_scores[c])
        diff = e_avg - b_avg
        sign = "+" if diff > 0 else ""
        total_baseline.append(b_avg)
        total_enhanced.append(e_avg)
        lines.append(f"| {c.capitalize()} | {b_avg:.1f} | {e_avg:.1f} | {sign}{diff:.1f} |")

    overall_b = statistics.mean(total_baseline)
    overall_e = statistics.mean(total_enhanced)
    overall_diff = overall_e - overall_b
    sign = "+" if overall_diff > 0 else ""
    lines.append(f"| **Overall** | **{overall_b:.1f}** | **{overall_e:.1f}** | **{sign}{overall_diff:.1f}** |")
    lines.append("")

    # Improvement percentage
    if overall_b > 0:
        pct = ((overall_e - overall_b) / overall_b) * 100
        lines.append(f"**Overall improvement: {pct:+.0f}%**")
    lines.append("")

    # Per-query details
    lines.append("## Per-Query Results")
    lines.append("")
    for i, r in enumerate(results, 1):
        lines.append(f"### Query {i}: {r['query']}")
        lines.append(f"*Category: {r['category']}*")
        lines.append("")

        # Score mini-table
        lines.append("| Criterion | Baseline | Enhanced | Delta |")
        lines.append("|-----------|----------|----------|-------|")
        for c in CRITERIA:
            b = r["scores"]["baseline"][c]
            e = r["scores"]["enhanced"][c]
            d = e - b
            s = "+" if d > 0 else ""
            lines.append(f"| {c.capitalize()} | {b} | {e} | {s}{d} |")
        lines.append("")

        # Judge notes
        if r["scores"]["baseline"].get("notes"):
            lines.append(f"**Baseline note:** {r['scores']['baseline']['notes']}")
        if r["scores"]["enhanced"].get("notes"):
            lines.append(f"**Enhanced note:** {r['scores']['enhanced']['notes']}")
        lines.append("")

        # Show response excerpts (first 300 chars)
        lines.append("<details>")
        lines.append("<summary>Response excerpts (click to expand)</summary>")
        lines.append("")
        lines.append("**Baseline response:**")
        lines.append(f"> {r['baseline'][:500]}...")
        lines.append("")
        lines.append("**Enhanced response (with llms.txt):**")
        lines.append(f"> {r['enhanced'][:500]}...")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Methodology
    lines.append("## Methodology")
    lines.append("")
    lines.append("This benchmark measures whether providing an llms.txt file as context to an AI assistant")
    lines.append("improves the quality of its responses about the website/organization.")
    lines.append("")
    lines.append("For each test query:")
    lines.append("1. **Baseline**: The AI answers using only its general training knowledge (no llms.txt context)")
    lines.append("2. **Enhanced**: The AI answers with the llms.txt content injected as a system-level reference")
    lines.append("3. **Judging**: A separate LLM call scores both responses on accuracy, completeness,")
    lines.append("   specificity, and actionability (1-10 scale) against known key facts")
    lines.append("")
    lines.append("This simulates the real-world scenario: when a user asks an AI assistant about your")
    lines.append("organization, does having llms.txt available produce meaningfully better answers?")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark llms.txt effectiveness by comparing AI responses with and without context"
    )
    parser.add_argument(
        "--llms-txt", type=str, default="llms.txt",
        help="Path to llms.txt file (default: llms.txt)",
    )
    parser.add_argument(
        "--full-txt", type=str, default=None,
        help="Path to llms-full.txt file (optional — if provided, used as context instead of llms.txt)",
    )
    parser.add_argument(
        "--api", type=str, choices=["claude", "openai", "gemini", "auto"], default="auto",
        help="AI API backend to use (default: auto-detect)",
    )
    parser.add_argument(
        "--queries", type=str, default=None,
        help="Path to JSON file with custom test queries",
    )
    parser.add_argument(
        "--auto-queries", action="store_true",
        help="Auto-generate test queries from the llms.txt content using the AI API",
    )
    parser.add_argument(
        "--output", type=str, default="benchmark-report.md",
        help="Output file for the benchmark report (default: benchmark-report.md)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Delay between API calls in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--max-queries", type=int, default=None,
        help="Limit the number of test queries to run (useful for quick tests)",
    )
    args = parser.parse_args()

    # --- Resolve API backend ---
    api_name = args.api
    if api_name == "auto":
        api_name = detect_api()
        if not api_name:
            print("Error: No API key found. Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY")
            sys.exit(1)
        print(f"Auto-detected API: {API_BACKENDS[api_name]['label']}")
    else:
        env_key = API_BACKENDS[api_name]["env_key"]
        if not os.environ.get(env_key):
            print(f"Error: {env_key} not set. Required for --api {api_name}")
            sys.exit(1)

    call_fn = API_BACKENDS[api_name]["fn"]
    api_label = API_BACKENDS[api_name]["label"]

    # --- Load llms.txt ---
    llms_path = Path(args.llms_txt)
    if not llms_path.exists():
        print(f"Error: {llms_path} not found")
        sys.exit(1)
    llms_content = llms_path.read_text(encoding="utf-8")
    print(f"Loaded {llms_path} ({len(llms_content)} chars)")

    # Use llms-full.txt as context if provided
    context_content = llms_content
    context_file = str(llms_path)
    full_file = None
    if args.full_txt:
        full_path = Path(args.full_txt)
        if full_path.exists():
            context_content = full_path.read_text(encoding="utf-8")
            context_file = str(full_path)
            full_file = str(full_path)
            print(f"Using {full_path} as context ({len(context_content)} chars)")
        else:
            print(f"Warning: {full_path} not found, using {llms_path} as context")

    # --- Load or generate test queries ---
    if args.queries:
        query_path = Path(args.queries)
        if not query_path.exists():
            print(f"Error: {query_path} not found")
            sys.exit(1)
        queries = json.loads(query_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(queries)} custom queries from {query_path}")
    elif args.auto_queries:
        print("Auto-generating test queries from llms.txt content...")
        queries = auto_generate_queries(llms_content, call_fn)
        print(f"Generated {len(queries)} test queries")
    else:
        queries = DEFAULT_QUERIES
        print(f"Using {len(queries)} default test queries")

    if args.max_queries:
        queries = queries[: args.max_queries]
        print(f"Limited to {len(queries)} queries")

    # --- Run benchmark ---
    print(f"\nRunning benchmark with {len(queries)} queries using {api_label}...\n")
    results = []

    for i, q in enumerate(queries, 1):
        query_text = q["query"]
        print(f"[{i}/{len(queries)}] {query_text[:70]}...")

        try:
            # Get baseline and enhanced responses
            print(f"  Generating baseline response...")
            baseline, enhanced = run_query_pair(query_text, context_content, call_fn, delay=args.delay)
            print(f"  Generating enhanced response...")

            # Judge the responses
            print(f"  Scoring with LLM judge...")
            time.sleep(args.delay)
            scores = judge_responses(q, baseline, enhanced, call_fn)

            results.append({
                "query": query_text,
                "category": q.get("category", "general"),
                "key_facts": q.get("key_facts", []),
                "baseline": baseline,
                "enhanced": enhanced,
                "scores": scores,
            })

            # Print quick summary
            b_avg = statistics.mean([scores["baseline"][c] for c in CRITERIA])
            e_avg = statistics.mean([scores["enhanced"][c] for c in CRITERIA])
            print(f"  → Baseline: {b_avg:.1f}  Enhanced: {e_avg:.1f}  Delta: {e_avg - b_avg:+.1f}")
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            print()
            continue

    if not results:
        print("No results collected. Check your API key and network connection.")
        sys.exit(1)

    # --- Generate report ---
    report = generate_report(results, api_label, context_file, full_file)
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Benchmark complete! Report saved to: {output_path}")
    print(f"{'='*60}")

    # Print summary to terminal
    total_b = []
    total_e = []
    for r in results:
        for c in CRITERIA:
            total_b.append(r["scores"]["baseline"][c])
            total_e.append(r["scores"]["enhanced"][c])
    avg_b = statistics.mean(total_b)
    avg_e = statistics.mean(total_e)
    pct = ((avg_e - avg_b) / avg_b) * 100 if avg_b > 0 else 0

    print(f"\n  Baseline average:  {avg_b:.1f}/10")
    print(f"  Enhanced average:  {avg_e:.1f}/10")
    print(f"  Improvement:       {pct:+.0f}%")
    print(f"\n  Queries tested:    {len(results)}")
    print(f"  API backend:       {api_label}")
    print()


if __name__ == "__main__":
    main()
