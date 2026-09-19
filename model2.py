import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
import time

import google as genai


# =========================
# CONFIG
# =========================
MAX_PAGES = 30
MAX_AI_CALLS = 8

visited = set()
category_content = {}
ai_calls_used = 0

# =========================
# GEMINI INIT
# =========================
API_KEY = os.getenv("GOOGLE_API_KEY")
USE_AI = False

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    USE_AI = True


# =========================
# CATEGORY MAP
# =========================
CATEGORY_MAP = {
    "Admissions": ["admission", "apply", "eligibility"],
    "Hostel": ["hostel", "accommodation"],
    "Fees & Payments": ["fee", "payment", "refund"],
    "Placements & Careers": ["placement", "career", "job", "internship"],
    "Transport": ["transport", "bus"],
    "Campus & Security": ["campus", "security", "facility"],
    "Documents": ["document", "certificate"],
    "Contact": ["contact", "email", "phone", "address"],
    "General Information": ["about", "overview", "university"]
}


# =========================
# FETCH PAGE
# =========================
def get_soup(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        return BeautifulSoup(res.text, "lxml")
    except:
        return None


# =========================
# CLASSIFY TEXT
# =========================
def classify_text(text):
    text = text.lower()
    for category, keywords in CATEGORY_MAP.items():
        for word in keywords:
            if word in text:
                return category
    return "General Information"


# =========================
# COLLECT CONTENT
# =========================
def collect_content(soup):
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)

        if len(text) < 80:
            continue

        category = classify_text(text)

        if category not in category_content:
            category_content[category] = []

        category_content[category].append(text)


# =========================
# CRAWLER
# =========================
def crawl(url, base_domain):
    if url in visited or len(visited) >= MAX_PAGES:
        return

    print("🔍 Crawling:", url)
    visited.add(url)

    soup = get_soup(url)
    if not soup:
        return

    collect_content(soup)

    for link in soup.find_all("a", href=True):
        next_url = urljoin(url, link["href"])

        if urlparse(next_url).netloc == base_domain:
            crawl(next_url, base_domain)


# =========================
# RULE-BASED FALLBACK
# =========================
def generate_rule_based_qa(texts, category):
    qa = []

    for text in texts[:5]:
        qa.append([
            f"What should I know about {category.lower()}?",
            text.strip()
        ])

    return qa


# =========================
# GEMINI AI Q&A (LIMITED)
# =========================
def generate_ai_qa(text_block, category):
    global ai_calls_used

    if not USE_AI or ai_calls_used >= MAX_AI_CALLS:
        return []

    try:
        prompt = f"""
You are a chatbot data generator for a university website.

Convert the content into 2–3 clear student FAQ pairs.

Category: {category}

Rules:
- Simple student questions
- Clear answers
- No explanation
- Return ONLY JSON like:
[
 ["question", "answer"]
]

Content:
{text_block[:1200]}
"""

        response = model.generate_content(prompt)

        ai_calls_used += 1
        time.sleep(1.5)

        # Gemini returns text → convert safely
        text = response.text

        return json.loads(text)

    except Exception as e:
        print(f"⚠️ Gemini failed for {category}: {e}")
        return []


# =========================
# BUILD DATASET
# =========================
def build_dataset():
    final_data = {}

    for category, texts in category_content.items():
        print(f"⚙️ Processing: {category}")

        sample_text = " ".join(texts[:2])[:1200]

        qa_pairs = []

        # try AI first
        qa_pairs = generate_ai_qa(sample_text, category)

        # fallback
        if not qa_pairs:
            qa_pairs = generate_rule_based_qa(texts, category)

        if qa_pairs:
            final_data[category] = qa_pairs

    print(f"\n🤖 Gemini AI calls used: {ai_calls_used}/{MAX_AI_CALLS}")
    return final_data


# =========================
# SAVE OUTPUT
# =========================
def save_data(data):
    with open("data.py", "w", encoding="utf-8") as f:
        f.write("DATA = ")
        json.dump(data, f, indent=4, ensure_ascii=False)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    start_url = input("Enter college website URL: ")
    domain = urlparse(start_url).netloc

    crawl(start_url, domain)

    print("\n🤖 Generating chatbot dataset using Gemini...")

    dataset = build_dataset()

    save_data(dataset)

    print("\n✅ DONE! Saved as data.py")