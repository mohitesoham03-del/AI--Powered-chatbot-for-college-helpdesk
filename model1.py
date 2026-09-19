import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import re

visited = set()
data_store = []

MAX_PAGES = 30   # prevent overload


def get_soup(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        return BeautifulSoup(res.text, "lxml")
    except:
        return None


def is_valid(url, base_domain):
    parsed = urlparse(url)
    return parsed.netloc == base_domain


def extract_data(soup, url):
    page_data = {
        "url": url,
        "title": soup.title.text.strip() if soup.title else "",
        "headings": [],
        "paragraphs": [],
        "tables": [],
        "faqs": [],
        "emails": [],
        "phones": []
    }

    # headings
    for tag in soup.find_all(['h1', 'h2', 'h3']):
        page_data["headings"].append(tag.get_text(strip=True))

    # paragraphs
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 50:
            page_data["paragraphs"].append(text)

    # tables
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            rows.append(cols)
        page_data["tables"].append(rows)

    # emails & phones
    text = soup.get_text()
    page_data["emails"] = list(set(re.findall(r'\S+@\S+', text)))
    page_data["phones"] = list(set(re.findall(r'\+?\d[\d -]{8,}\d', text)))

    # FAQ detection
    for q in soup.find_all(['h2', 'h3', 'strong']):
        question = q.get_text()
        if "?" in question:
            ans_tag = q.find_next_sibling()
            answer = ans_tag.get_text(strip=True) if ans_tag else ""
            page_data["faqs"].append({
                "question": question,
                "answer": answer
            })

    return page_data


def crawl(url, base_domain):
    if url in visited or len(visited) >= MAX_PAGES:
        return

    print(f"🔍 Visiting: {url}")
    visited.add(url)

    soup = get_soup(url)
    if not soup:
        return

    # extract data
    page_info = extract_data(soup, url)
    data_store.append(page_info)

    # find more links
    for link in soup.find_all("a", href=True):
        next_url = urljoin(url, link["href"])

        if is_valid(next_url, base_domain):
            crawl(next_url, base_domain)


def save_json():
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data_store, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    start_url = input("Enter college website URL: ")
    domain = urlparse(start_url).netloc

    crawl(start_url, domain)
    save_json()

    print("\n✅ Scraping completed. Data saved to data.json")