#!/usr/bin/env python3
"""
Enhanced Web Crawler for LLM-optimized Site Maps
------------------------------------------------
This script crawls a website, creates a structured site map, and then enhances it
using the Gemini API to add detailed descriptions and organize content hierarchically.
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
        You are an expert at organizing website content for better understanding by both humans and AI language models.
        
        I'll provide you with a basic site map of web pages (URLs and titles). Your task is to:
        
        1. Create a well-structured, hierarchical organization of the content
        2. Add descriptive metadata about the site and its sections
        3. Group related content together under logical section headers
        4. Add brief descriptions for important pages
        5. Include a topic-based index at the end
        
        Format the output as a Markdown document with:
        - JSON metadata block at the top
        - Clear hierarchical headings (## for main sections, ### for subsections)
        - Descriptive link text and contextual notes
        - Proper nesting to show relationships between pages
        
        Here's the content to enhance:
        
        {content}
        """
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
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

def group_and_format(pages, site_name):
    """
    Group pages by section and format as markdown
    """
    grouped = defaultdict(list)
    for url, title in pages:
        path = urlparse(url).path
        parts = path.strip("/").split("/")
        # Handle empty paths (homepage)
        top_section = parts[0] if parts and parts[0] else "Home"
        grouped[top_section].append((title, url))

    # Create a basic site map
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    output = f"# {site_name} – Auto-Generated Site Map\n\n"
    output += f"> Automatically generated site map on {today} for LLM understanding.\n\n"
    
    # Sort sections alphabetically but put Home first
    sections = sorted(grouped.keys())
    if "Home" in sections:
        sections.remove("Home")
        sections = ["Home"] + sections
        
    for section in sections:
        output += f"## {section.capitalize()}\n\n"
        # Sort links by URL length (shorter URLs tend to be higher-level pages)
        links = sorted(grouped[section], key=lambda x: len(x[1]))
        for title, url in links:
            # Clean up title if needed
            clean_title = re.sub(r'\s+', ' ', title)
            output += f"- [{clean_title}]({url})\n"
        output += "\n"
    
    return output

def enhance_site_map(basic_map, site_name, api_key):
    """
    Use Gemini API to enhance the basic site map
    """
    print("Enhancing site map with Gemini API...")
    
    custom_prompt = f"""
    You are an expert at organizing website content for better understanding by both humans and AI language models.
    
    I'll provide you with a basic site map of {site_name}'s web pages (URLs and titles). Your task is to:
    
    1. Create a well-structured, hierarchical organization of the content
    2. Add descriptive metadata about the site and its sections using JSON at the top
    3. Group related content together under logical section headers
    4. Add brief descriptions for important pages and sections
    5. Include a topic-based index at the end
    6. Preserve all original URLs but improve organization and descriptions
    
    Format the output as a Markdown document with:
    - JSON metadata block at the top with institution name, website, generated date, version, and description
    - Clear hierarchical headings (## for main sections, ### for subsections, etc.)
    - Descriptive link text and contextual notes (use > blockquotes for section descriptions)
    - Proper nesting to show relationships between pages
    
    Here's the content to enhance:
    
    {basic_map}
    """
    
    enhanced_map = enhance_with_gemini(basic_map, api_key, custom_prompt)
    return enhanced_map

def main():
    parser = argparse.ArgumentParser(description="Create an enhanced site map for LLM context")
    parser.add_argument("--url", type=str, help="Website URL to crawl", 
                        default="https://giesbusiness.illinois.edu")
    parser.add_argument("--name", type=str, help="Site name for the output files",
                        default="Website")
    parser.add_argument("--max-pages", type=int, help="Maximum pages to crawl",
                        default=150)
    parser.add_argument("--delay", type=float, help="Delay between requests (seconds)",
                        default=0.2)
    parser.add_argument("--skip-enhance", action="store_true", 
                        help="Skip the enhancement step (no API call)")
    args = parser.parse_args()
    
    # Extract domain name from URL for site name if not provided
    if args.name == "Website":
        domain = urlparse(args.url).netloc
        args.name = domain.split(".")[-2].capitalize() if len(domain.split(".")) > 1 else domain

    # Crawl the site
    pages = crawl_site(args.url, max_pages=args.max_pages, delay=args.delay)
    
    # Format the basic site map
    basic_map = group_and_format(pages, args.name)
    
    # Save the basic site map
    basic_filename = "llms.txt"
    with open(basic_filename, "w", encoding="utf-8") as f:
        f.write(basic_map)
    
    print(f"✅ Basic site map saved to {basic_filename}")
    
    # Enhance the site map if not skipped
    if not args.skip_enhance:
        try:
            api_key = get_gemini_api_key()
            enhanced_map = enhance_site_map(basic_map, args.name, api_key)
            
            if enhanced_map:
                enhanced_filename = "llms-enhanced.txt"
                with open(enhanced_filename, "w", encoding="utf-8") as f:
                    f.write(enhanced_map)
                print(f"✅ Enhanced site map saved to {enhanced_filename}")
            else:
                print("⚠️ Enhancement failed. Please check your API key or try again later.")
        except Exception as e:
            print(f"Error during enhancement: {e}")
            print("⚠️ Enhancement failed. Basic site map is still available.")
    
if __name__ == "__main__":
    main()