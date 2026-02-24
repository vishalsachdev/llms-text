#!/usr/bin/env python3
"""
llms.txt Generator (llmstxt.org spec)
-------------------------------------
Crawls a website and generates spec-compliant llms.txt files.
Optionally enhances output via the Gemini API for better descriptions
and logical grouping. Outputs follow the official format:
  # Title > Summary, ## Sections, - [Link](url): description
"""

import requests
import json
import os
import time
import datetime
import argparse
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import defaultdict

# Check for Google API key in environment or prompt user
def get_gemini_api_key():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("No Gemini API key found in environment variables.")
        api_key = input("Please enter your Google API key (or set GOOGLE_API_KEY environment variable): ")
    return api_key

# Gemini API call function
def enhance_with_gemini(content, api_key, prompt_template=None):
    if not prompt_template:
        prompt_template = """
        Reorganize this site map into llms.txt spec format. Output ONLY the
        markdown content, no code fences.

        {content}
        """

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_template.format(content=content)
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }
    
    response = requests.post(
        f"{url}?key={api_key}",
        headers=headers,
        data=json.dumps(data)
    )
    
    if response.status_code != 200:
        print(f"Error calling Gemini API: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    try:
        generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
        return generated_text
    except (KeyError, IndexError) as e:
        print(f"Error parsing Gemini API response: {e}")
        print(result)
        return None

def crawl_site(base_url, max_pages=150, delay=0.1):
    """
    Crawl a website and collect page URLs and titles
    """
    print(f"Starting crawl of {base_url} (max: {max_pages} pages)")
    visited = set()
    to_visit = [base_url]
    pages = []
    count = 0

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited or not url.startswith(base_url):
            continue

        try:
            print(f"Crawling [{count+1}/{max_pages}]: {url}")
            response = requests.get(url, timeout=10)
            time.sleep(delay)  # Be nice to the server
            
            if response.status_code != 200:
                print(f"  ↳ Error: HTTP {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else url
            pages.append((url, title))
            count += 1

            # Find all links and add to crawl queue
            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                # Only follow links to the same domain
                if (base_url in full_url and 
                    full_url not in visited and 
                    full_url not in to_visit and
                    not full_url.endswith(('.pdf', '.jpg', '.png', '.gif', '.zip'))):
                    to_visit.append(full_url)

            visited.add(url)
            
        except Exception as e:
            print(f"  ↳ Error: {e}")
            continue

    print(f"Crawl complete. Found {len(pages)} pages.")
    return pages

def group_and_format(pages, site_name, base_url):
    """
    Group pages by URL path section and format as llms.txt spec-compliant markdown.
    Spec: H1 title, blockquote summary, H2 sections, - [Title](url): description links.
    """
    grouped = defaultdict(list)
    for url, title in pages:
        path = urlparse(url).path
        parts = path.strip("/").split("/")
        top_section = parts[0] if parts and parts[0] else "Home"
        grouped[top_section].append((title, url))

    # Pretty-print section names: "undergraduate-hub" -> "Undergraduate Hub"
    def section_label(slug):
        return slug.replace("-", " ").replace("_", " ").title()

    output = f"# {site_name}\n\n"
    output += f"> Site map of {site_name} ({base_url}), auto-generated for LLM context.\n\n"

    # Sort sections alphabetically but put Home first
    sections = sorted(grouped.keys())
    if "Home" in sections:
        sections.remove("Home")
        sections = ["Home"] + sections

    for section in sections:
        output += f"## {section_label(section)}\n\n"
        # Sort links by URL length (shorter = higher-level pages first)
        links = sorted(grouped[section], key=lambda x: len(x[1]))
        for title, url in links:
            clean_title = re.sub(r'\s+', ' ', title)
            output += f"- [{clean_title}]({url})\n"
        output += "\n"

    return output

def enhance_site_map(basic_map, site_name, api_key):
    """
    Use Gemini API to enhance the basic site map into llms.txt spec format.
    """
    print("Enhancing site map with Gemini API...")

    custom_prompt = f"""You are generating an llms.txt file following the official spec (llmstxt.org).

Given this raw site map of {site_name}, produce a spec-compliant llms.txt file.

STRICT FORMAT RULES — follow these exactly:
1. Line 1: # {site_name}
2. A blank line, then a single blockquote (>) with a 1-2 sentence summary of the site
3. Optionally, 1-2 plain paragraphs of additional context (NO headings here)
4. Then ## sections grouping related pages. Only use ## headings (H2), never ### or deeper
5. Inside each ## section: a markdown list where each item is:
   - [Page Title](https://full-url): Brief description of what this page contains
6. Include a ## Optional section at the end for lower-priority pages
7. Output ONLY the raw markdown. No code fences, no ```markdown blocks, no JSON metadata

CONTENT RULES:
- Preserve ALL original URLs exactly as given
- Group related pages logically (programs, student life, research, about, etc.)
- Write concise descriptions (under 15 words each) after the colon
- Merge duplicate or near-duplicate entries
- Put the most important pages first within each section

Here's the raw site map to enhance:

{basic_map}"""

    enhanced_map = enhance_with_gemini(basic_map, api_key, custom_prompt)
    if enhanced_map:
        # Strip code fences if Gemini wraps output despite instructions
        enhanced_map = enhanced_map.strip()
        if enhanced_map.startswith("```"):
            lines = enhanced_map.split("\n")
            # Remove first line (```markdown) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            enhanced_map = "\n".join(lines).strip()
    return enhanced_map

def main():
    parser = argparse.ArgumentParser(
        description="Generate llms.txt files following the llmstxt.org spec")
    parser.add_argument("url", type=str, nargs="?", help="Website URL to crawl",
                        default="https://giesbusiness.illinois.edu")
    parser.add_argument("--name", type=str, help="Site name for the H1 title",
                        default="Website")
    parser.add_argument("--max-pages", type=int, help="Maximum pages to crawl",
                        default=150)
    parser.add_argument("--delay", type=float, help="Delay between requests (seconds)",
                        default=0.2)
    parser.add_argument("--skip-enhance", action="store_true",
                        help="Skip the Gemini enhancement step (basic spec-compliant output only)")
    parser.add_argument("--full", action="store_true",
                        help="Also generate llms-full.txt with higher page limit")
    args = parser.parse_args()

    # Extract domain name from URL for site name if not provided
    if args.name == "Website":
        domain = urlparse(args.url).netloc
        args.name = domain.split(".")[-2].capitalize() if len(domain.split(".")) > 1 else domain

    # Crawl the site
    pages = crawl_site(args.url, max_pages=args.max_pages, delay=args.delay)

    # Format the basic site map (now spec-compliant)
    basic_map = group_and_format(pages, args.name, args.url)

    if args.skip_enhance:
        with open("llms.txt", "w", encoding="utf-8") as f:
            f.write(basic_map)
        print(f"✅ Basic llms.txt saved ({len(pages)} pages)")
    else:
        print(f"✅ Crawled {len(pages)} pages, sending to Gemini for enhancement...")
        try:
            api_key = get_gemini_api_key()
            enhanced_map = enhance_site_map(basic_map, args.name, api_key)

            if enhanced_map:
                with open("llms.txt", "w", encoding="utf-8") as f:
                    f.write(enhanced_map)
                print("✅ Enhanced llms.txt saved")
            else:
                # Fall back to basic map on API failure
                with open("llms.txt", "w", encoding="utf-8") as f:
                    f.write(basic_map)
                print("⚠️ Enhancement failed, saved basic llms.txt instead")
        except Exception as e:
            print(f"Error during enhancement: {e}")
            with open("llms.txt", "w", encoding="utf-8") as f:
                f.write(basic_map)
            print("⚠️ Enhancement failed, saved basic llms.txt instead")

    # Generate llms-full.txt with all crawled pages (no truncation)
    if args.full:
        full_map = group_and_format(pages, args.name, args.url)
        with open("llms-full.txt", "w", encoding="utf-8") as f:
            f.write(full_map)
        print("✅ llms-full.txt saved (comprehensive version)")
    
if __name__ == "__main__":
    main()