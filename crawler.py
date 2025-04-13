import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import defaultdict

def crawl_site(base_url, max_pages=100):
    visited = set()
    to_visit = [base_url]
    pages = []

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited or not url.startswith(base_url):
            continue

        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else url
            pages.append((url, title))

            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                if base_url in full_url and full_url not in visited:
                    to_visit.append(full_url)

            visited.add(url)
        except Exception:
            continue

    return pages

def group_and_format(pages):
    grouped = defaultdict(list)
    for url, title in pages:
        path = urlparse(url).path
        top_section = path.strip("/").split("/")[0] or "Home"
        grouped[top_section].append((title, url))

    output = "# Gies College of Business – Auto-Generated llms.txt\n\n"
    output += "> Automatically generated site map for LLM understanding.\n\n"
    for section, links in grouped.items():
        output += f"## {section.capitalize()}\n\n"
        for title, url in links:
            output += f"- [{title}]({url})\n"
        output += "\n"
    return output

if __name__ == "__main__":
    # Use a default URL
    base_url = "https://giesbusiness.illinois.edu"
    print(f"Crawling {base_url}...")
    pages = crawl_site(base_url)
    print(f"Found {len(pages)} pages. Formatting output...")
    llms_txt = group_and_format(pages)
    
    with open("llms.txt", "w", encoding="utf-8") as f:
        f.write(llms_txt)
    
    print("✅ llms.txt generated successfully.")