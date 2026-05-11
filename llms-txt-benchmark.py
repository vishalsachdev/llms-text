#!/usr/bin/env python3
"""
llms.txt Benchmark — Empirical Validation for llms.txt Effectiveness
--------------------------------------------------------------------
Tests whether an llms.txt file actually improves AI assistant responses
about a website by running controlled before/after comparisons with
LLM-as-judge scoring.

De-biasing measures:
  - The judge sees the two answers in a randomized order and is *blinded*
    to which one had llms.txt context (labels are neutral "Response A/B").
  - The judge can run on a different model/provider than the one being
    tested (--judge-api / --judge-model) to reduce self-preference bias.
  - Each query can be repeated over several --trials and averaged.

Supports Claude (Anthropic), GPT (OpenAI), and Gemini (Google) APIs.

Usage:
    ./llms-txt-benchmark.py                       # auto-detect API, default queries
    ./llms-txt-benchmark.py --api claude --judge-api openai
    ./llms-txt-benchmark.py --full-txt llms-full.txt --trials 3
    ./llms-txt-benchmark.py --queries my-queries.json
    ./llms-txt-benchmark.py --auto-queries
"""

import argparse
import datetime
import json
import os
import random
import re
import statistics
import sys
import time
from functools import partial
from pathlib import Path


# ---------------------------------------------------------------------------
# Token accounting (best-effort, shared across all API calls)
# ---------------------------------------------------------------------------

TOKEN_USAGE = {"input": 0, "output": 0}


def _track(input_tokens, output_tokens):
    TOKEN_USAGE["input"] += input_tokens or 0
    TOKEN_USAGE["output"] += output_tokens or 0


# ---------------------------------------------------------------------------
# API Clients — each returns the response text and records token usage.
# ---------------------------------------------------------------------------

def call_claude(prompt, system=None, model="claude-sonnet-4-20250514", max_tokens=1024):
    import anthropic
    client = anthropic.Anthropic()
    kwargs = {"model": model, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    usage = getattr(response, "usage", None)
    if usage:
        _track(getattr(usage, "input_tokens", 0), getattr(usage, "output_tokens", 0))
    return response.content[0].text


def call_openai(prompt, system=None, model="gpt-4o", max_tokens=1024):
    import openai
    client = openai.OpenAI()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=model, messages=messages,
                                              max_tokens=max_tokens)
    usage = getattr(response, "usage", None)
    if usage:
        _track(getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0))
    return response.choices[0].message.content


def call_gemini(prompt, system=None, model="gemini-1.5-pro-latest", max_tokens=1024):
    import requests as req
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    text = f"{system}\n\n{prompt}" if system else prompt
    data = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens}}
    resp = req.post(f"{url}?key={api_key}", headers={"Content-Type": "application/json"},
                    json=data, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")
    body = resp.json()
    meta = body.get("usageMetadata", {})
    _track(meta.get("promptTokenCount", 0), meta.get("candidatesTokenCount", 0))
    return body["candidates"][0]["content"]["parts"][0]["text"]


API_BACKENDS = {
    "claude": {"fn": call_claude, "env_key": "ANTHROPIC_API_KEY", "label": "Claude (Anthropic)"},
    "openai": {"fn": call_openai, "env_key": "OPENAI_API_KEY", "label": "GPT (OpenAI)"},
    "gemini": {"fn": call_gemini, "env_key": "GOOGLE_API_KEY", "label": "Gemini (Google)"},
}


def detect_api():
    for name in ("claude", "openai", "gemini"):
        if os.environ.get(API_BACKENDS[name]["env_key"]):
            return name
    return None


def resolve_backend(api_arg, role):
    """Return (call_fn, label, name) for an --api/--judge-api value."""
    name = api_arg
    if name == "auto":
        name = detect_api()
        if not name:
            print("Error: No API key found. Set one of: "
                  "ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY")
            sys.exit(1)
        print(f"Auto-detected {role} API: {API_BACKENDS[name]['label']}")
    elif not os.environ.get(API_BACKENDS[name]["env_key"]):
        print(f"Error: {API_BACKENDS[name]['env_key']} not set (required for {role} --api {name})")
        sys.exit(1)
    return API_BACKENDS[name]["fn"], API_BACKENDS[name]["label"], name


# ---------------------------------------------------------------------------
# Default test queries (Gies-focused, but illustrative for any university)
# ---------------------------------------------------------------------------

DEFAULT_QUERIES = [
    {
        "query": "I'm interested in an online MBA that focuses on AI. What does Gies College of Business offer?",
        "category": "prospective_student",
        "key_facts": [
            "iMBA program", "offered via Coursera", "affordable/STEM-designated",
            "AI-integrated curriculum", "Google partnership (Gemini, NotebookLM)",
            "Wymer Hall / AI course production",
        ],
    },
    {
        "query": "What experiential learning opportunities does Gies have for undergrad business students?",
        "category": "prospective_student",
        "key_facts": [
            "Illinois Business Consulting", "MakerLab", "iVenture Accelerator",
            "experiential learning with corporate partners", "30+ student organizations",
        ],
    },
    {
        "query": "Tell me about the MS in Business Analytics at the University of Illinois.",
        "category": "prospective_student",
        "key_facts": [
            "MSBA program", "STEM-designated", "data science / machine learning focus",
            "Gies College of Business",
        ],
    },
    {
        "query": "How is Gies College of Business using artificial intelligence in its programs?",
        "category": "ai_initiatives",
        "key_facts": [
            "AI-integrated curriculum across all programs", "Google partnership",
            "Cleo (AI interview simulator)", "Alma (AI chatbot for iMBA)",
            "AI avatars for course content", "Wymer Hall AI studios",
        ],
    },
    {
        "query": "What career support does Gies provide to its students?",
        "category": "career",
        "key_facts": [
            "Career & Professional Development office", "Gies Professional Pathway",
            "corporate recruiting", "career coaching / interview prep",
        ],
    },
    {
        "query": "I'm a company looking to recruit business students from UIUC. How do I partner with Gies?",
        "category": "corporate",
        "key_facts": [
            "Corporate Partners program", "on-campus recruiting / career fairs",
            "Illinois Business Consulting projects", "workforce development",
        ],
    },
    {
        "query": "What PhD programs does Gies College of Business offer?",
        "category": "prospective_student",
        "key_facts": [
            "PhD in Accountancy", "PhD in Business Administration", "PhD in Finance",
            "research-focused",
        ],
    },
    {
        "query": "Does Gies have any stackable credentials or certificates I can earn before committing to a full degree?",
        "category": "prospective_student",
        "key_facts": [
            "Gies Professional Credentials", "iAcademies", "stackable toward full degrees",
            "graduate certificates",
        ],
    },
]


# ---------------------------------------------------------------------------
# Query auto-generation from llms.txt content
# ---------------------------------------------------------------------------

def _extract_json(raw):
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if json_match:
        raw = json_match.group(1)
    start = min((i for i in (raw.find("["), raw.find("{")) if i != -1), default=-1)
    if start != -1:
        # Match the corresponding close bracket from the end.
        end = max(raw.rfind("]"), raw.rfind("}"))
        if end > start:
            raw = raw[start:end + 1]
    return json.loads(raw)


def auto_generate_queries(llms_content, call_fn):
    prompt = f"""Below is the contents of an llms.txt file for a website. Generate 8 realistic test queries
that a prospective student, employer, or researcher might ask an AI assistant about this organization.

For each query, also list 3-5 key facts from the llms.txt that a good answer should include.

Return ONLY valid JSON — an array of objects with keys: "query", "category", "key_facts" (array of strings).

llms.txt content:
---
{llms_content}
---"""
    raw = call_fn(prompt, system="You are a helpful assistant that returns only valid JSON.",
                  max_tokens=2048)
    return _extract_json(raw)


# ---------------------------------------------------------------------------
# Benchmarking core
# ---------------------------------------------------------------------------

BASELINE_SYSTEM = (
    "You are a helpful AI assistant answering questions about universities and business schools. "
    "Answer based on your general knowledge. If you're unsure about specific details, say so."
)


def enhanced_system(llms_content):
    return (
        "You are a helpful AI assistant answering questions about universities and business schools. "
        "You have been provided with the following structured reference about the institution. "
        "Use it to give accurate, specific, and actionable answers.\n\n"
        f"--- REFERENCE ---\n{llms_content}\n--- END REFERENCE ---"
    )


def run_query_pair(query_text, llms_content, call_fn, delay=1.0):
    """Run a query with and without llms.txt context. Returns (baseline, enhanced)."""
    baseline = call_fn(query_text, system=BASELINE_SYSTEM)
    time.sleep(delay)
    enhanced = call_fn(query_text, system=enhanced_system(llms_content))
    time.sleep(delay)
    return baseline, enhanced


JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator assessing two AI assistant responses about a university/business school.

A user asked: "{query}"

Here are the key facts that a good answer should include:
{key_facts_formatted}

---

**Response A:**
{response_a}

---

**Response B:**
{response_b}

---

Score EACH response on a scale of 1-10 for each criterion:
1. **Accuracy** — Are the stated facts correct? No hallucinations?
2. **Completeness** — How many of the key facts are covered?
3. **Specificity** — Concrete details (program names, URLs, features) vs. vague generalities?
4. **Actionability** — Does it help the user take a next step (links, contact info, clear recommendations)?

Return ONLY valid JSON with this exact structure:
{{
  "response_a": {{"accuracy": N, "completeness": N, "specificity": N, "actionability": N, "notes": "brief explanation"}},
  "response_b": {{"accuracy": N, "completeness": N, "specificity": N, "actionability": N, "notes": "brief explanation"}}
}}"""

JUDGE_SYSTEM = ("You are a rigorous, impartial evaluator. Return only valid JSON. "
                "Be strict in scoring. You do not know how either response was produced.")


def judge_responses(query_obj, baseline, enhanced, call_fn, rng):
    """Blinded LLM-as-judge: random A/B order, scores mapped back to baseline/enhanced."""
    enhanced_is_a = rng.random() < 0.5
    resp_a, resp_b = (enhanced, baseline) if enhanced_is_a else (baseline, enhanced)
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        query=query_obj["query"],
        key_facts_formatted="\n".join(f"- {f}" for f in query_obj["key_facts"]),
        response_a=resp_a, response_b=resp_b,
    )
    raw = call_fn(prompt, system=JUDGE_SYSTEM, max_tokens=1024)
    parsed = _extract_json(raw)
    a, b = parsed["response_a"], parsed["response_b"]
    return {"enhanced": a, "baseline": b} if enhanced_is_a else {"enhanced": b, "baseline": a}


CRITERIA = ["accuracy", "completeness", "specificity", "actionability"]


def average_score_sets(score_sets):
    """Average a list of {baseline:{...}, enhanced:{...}} dicts criterion-wise."""
    out = {"baseline": {}, "enhanced": {}}
    for side in ("baseline", "enhanced"):
        for c in CRITERIA:
            out[side][c] = statistics.mean(s[side][c] for s in score_sets)
        notes = [s[side].get("notes") for s in score_sets if s[side].get("notes")]
        out[side]["notes"] = notes[0] if notes else ""
    return out


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(results, gen_label, judge_label, llms_file, full_file, trials):
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    baseline_scores = {c: [] for c in CRITERIA}
    enhanced_scores = {c: [] for c in CRITERIA}
    for r in results:
        for c in CRITERIA:
            baseline_scores[c].append(r["scores"]["baseline"][c])
            enhanced_scores[c].append(r["scores"]["enhanced"][c])

    lines = ["# llms.txt Benchmark Report", "",
             f"> Generated {today}", "",
             "## Configuration", "",
             f"- **llms.txt file:** `{llms_file}`"]
    if full_file:
        lines.append(f"- **llms-full.txt file:** `{full_file}`")
    lines += [
        f"- **Test queries:** {len(results)}",
        f"- **Trials per query:** {trials}",
        f"- **Answer model:** {gen_label}",
        f"- **Judge model:** {judge_label}",
        "- **Bias controls:** judge is blinded to which answer used llms.txt; A/B order randomized per trial",
        "",
        "## Summary Scores (1-10 scale)", "",
        "| Criterion | Baseline (no context) | With llms.txt | Improvement |",
        "|-----------|----------------------|---------------|-------------|",
    ]
    total_baseline, total_enhanced = [], []
    for c in CRITERIA:
        b_avg, e_avg = statistics.mean(baseline_scores[c]), statistics.mean(enhanced_scores[c])
        diff = e_avg - b_avg
        total_baseline.append(b_avg)
        total_enhanced.append(e_avg)
        lines.append(f"| {c.capitalize()} | {b_avg:.1f} | {e_avg:.1f} | {'+' if diff > 0 else ''}{diff:.1f} |")
    overall_b, overall_e = statistics.mean(total_baseline), statistics.mean(total_enhanced)
    overall_diff = overall_e - overall_b
    lines.append(f"| **Overall** | **{overall_b:.1f}** | **{overall_e:.1f}** | "
                 f"**{'+' if overall_diff > 0 else ''}{overall_diff:.1f}** |")
    lines.append("")
    if overall_b > 0:
        lines.append(f"**Overall improvement: {((overall_e - overall_b) / overall_b) * 100:+.0f}%**")
    lines.append("")

    lines += ["## Per-Query Results", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"### Query {i}: {r['query']}")
        lines.append(f"*Category: {r['category']}*")
        lines.append("")
        lines += ["| Criterion | Baseline | Enhanced | Delta |",
                  "|-----------|----------|----------|-------|"]
        for c in CRITERIA:
            b, e = r["scores"]["baseline"][c], r["scores"]["enhanced"][c]
            d = e - b
            lines.append(f"| {c.capitalize()} | {b:.1f} | {e:.1f} | {'+' if d > 0 else ''}{d:.1f} |")
        lines.append("")
        if r["scores"]["baseline"].get("notes"):
            lines.append(f"**Baseline note:** {r['scores']['baseline']['notes']}")
        if r["scores"]["enhanced"].get("notes"):
            lines.append(f"**Enhanced note:** {r['scores']['enhanced']['notes']}")
        lines += ["", "<details>", "<summary>Response excerpts (click to expand)</summary>", "",
                  "**Baseline response:**", f"> {r['baseline'][:500]}...", "",
                  "**Enhanced response (with llms.txt):**", f"> {r['enhanced'][:500]}...", "",
                  "</details>", ""]

    lines += [
        "## Methodology", "",
        "For each test query (repeated over the configured number of trials):",
        "1. **Baseline**: the answer model replies using only its general training knowledge.",
        "2. **Enhanced**: the answer model replies with the llms.txt content injected as a system reference.",
        "3. **Judging**: a separate judge call scores both answers (1-10) on accuracy, completeness,",
        "   specificity, and actionability against known key facts. The judge sees the two answers in a",
        "   random order with neutral labels and is not told which one used llms.txt.",
        "4. Scores are averaged across trials.",
        "",
        "This simulates the real-world scenario: when a user asks an AI assistant about your",
        "organization, does having llms.txt available produce meaningfully better answers?",
        "",
        f"_Token usage (best-effort): {TOKEN_USAGE['input']:,} input + {TOKEN_USAGE['output']:,} output_",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark llms.txt effectiveness by comparing AI responses with and without context")
    parser.add_argument("--llms-txt", default="llms.txt", help="Path to llms.txt file")
    parser.add_argument("--full-txt", default=None,
                        help="Path to llms-full.txt (used as context instead of llms.txt if provided)")
    parser.add_argument("--api", choices=["claude", "openai", "gemini", "auto"], default="auto",
                        help="API backend that produces the answers")
    parser.add_argument("--judge-api", choices=["claude", "openai", "gemini", "auto", "same"],
                        default="same", help="API backend for the judge (default: same as --api)")
    parser.add_argument("--gen-model", default=None, help="Override the answer model name")
    parser.add_argument("--judge-model", default=None, help="Override the judge model name")
    parser.add_argument("--trials", type=int, default=1, help="Times to repeat each query (averaged)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for A/B ordering")
    parser.add_argument("--queries", default=None, help="Path to JSON file with custom test queries")
    parser.add_argument("--auto-queries", action="store_true",
                        help="Auto-generate test queries from the llms.txt content")
    parser.add_argument("--output", default="benchmark-report.md", help="Output report file")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between API calls (seconds)")
    parser.add_argument("--max-queries", type=int, default=None, help="Limit number of test queries")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    gen_fn, gen_label, gen_name = resolve_backend(args.api, "answer")
    if args.gen_model:
        gen_fn = partial(gen_fn, model=args.gen_model)
        gen_label += f" [{args.gen_model}]"
    if args.judge_api == "same":
        judge_fn, judge_label = gen_fn, gen_label
    else:
        judge_fn, judge_label, _ = resolve_backend(args.judge_api, "judge")
    if args.judge_model:
        judge_fn = partial(judge_fn, model=args.judge_model)
        judge_label = judge_label.split(" [")[0] + f" [{args.judge_model}]"

    llms_path = Path(args.llms_txt)
    if not llms_path.exists():
        print(f"Error: {llms_path} not found")
        sys.exit(1)
    llms_content = llms_path.read_text(encoding="utf-8")
    print(f"Loaded {llms_path} ({len(llms_content)} chars)")

    context_content, context_file, full_file = llms_content, str(llms_path), None
    if args.full_txt:
        full_path = Path(args.full_txt)
        if full_path.exists():
            context_content = full_path.read_text(encoding="utf-8")
            context_file = full_file = str(full_path)
            print(f"Using {full_path} as context ({len(context_content)} chars)")
        else:
            print(f"Warning: {full_path} not found, using {llms_path} as context")

    if args.queries:
        query_path = Path(args.queries)
        if not query_path.exists():
            print(f"Error: {query_path} not found")
            sys.exit(1)
        queries = json.loads(query_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(queries)} custom queries from {query_path}")
    elif args.auto_queries:
        print("Auto-generating test queries from llms.txt content...")
        queries = auto_generate_queries(llms_content, gen_fn)
        print(f"Generated {len(queries)} test queries")
    else:
        queries = DEFAULT_QUERIES
        print(f"Using {len(queries)} default test queries")

    if args.max_queries:
        queries = queries[:args.max_queries]
        print(f"Limited to {len(queries)} queries")

    trials = max(1, args.trials)
    print(f"\nRunning benchmark: {len(queries)} queries x {trials} trial(s)")
    print(f"  Answers: {gen_label}\n  Judge:   {judge_label}\n")
    results = []

    for i, q in enumerate(queries, 1):
        query_text = q["query"]
        print(f"[{i}/{len(queries)}] {query_text[:70]}...")
        score_sets, baselines, enhanceds = [], [], []
        try:
            for t in range(trials):
                if trials > 1:
                    print(f"  trial {t + 1}/{trials}")
                baseline, enhanced = run_query_pair(query_text, context_content, gen_fn,
                                                    delay=args.delay)
                time.sleep(args.delay)
                scores = judge_responses(q, baseline, enhanced, judge_fn, rng)
                score_sets.append(scores)
                baselines.append(baseline)
                enhanceds.append(enhanced)
        except Exception as e:  # noqa: BLE001 - skip the query, keep going
            print(f"  ✗ Error: {e}\n")
            continue

        avg = average_score_sets(score_sets)
        results.append({
            "query": query_text,
            "category": q.get("category", "general"),
            "key_facts": q.get("key_facts", []),
            "baseline": baselines[0],
            "enhanced": enhanceds[0],
            "scores": avg,
        })
        b_avg = statistics.mean(avg["baseline"][c] for c in CRITERIA)
        e_avg = statistics.mean(avg["enhanced"][c] for c in CRITERIA)
        print(f"  → Baseline: {b_avg:.1f}  Enhanced: {e_avg:.1f}  Delta: {e_avg - b_avg:+.1f}\n")

    if not results:
        print("No results collected. Check your API key and network connection.")
        sys.exit(1)

    report = generate_report(results, gen_label, judge_label, context_file, full_file, trials)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"\n{'=' * 60}\nBenchmark complete! Report saved to: {args.output}\n{'=' * 60}")

    total_b = [r["scores"]["baseline"][c] for r in results for c in CRITERIA]
    total_e = [r["scores"]["enhanced"][c] for r in results for c in CRITERIA]
    avg_b, avg_e = statistics.mean(total_b), statistics.mean(total_e)
    pct = ((avg_e - avg_b) / avg_b) * 100 if avg_b > 0 else 0
    print(f"\n  Baseline average:  {avg_b:.1f}/10")
    print(f"  Enhanced average:  {avg_e:.1f}/10")
    print(f"  Improvement:       {pct:+.0f}%")
    print(f"\n  Queries tested:    {len(results)}  (x{trials} trials)")
    print(f"  Answer model:      {gen_label}")
    print(f"  Judge model:       {judge_label}")
    print(f"  Token usage:       {TOKEN_USAGE['input']:,} in + {TOKEN_USAGE['output']:,} out\n")


if __name__ == "__main__":
    main()
