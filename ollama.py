import requests
from bs4 import BeautifulSoup
import argparse
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor

OLLAMA_URL = "http://localhost:11434/api/generate"

# -------------------------------
# Ask Ollama (robust + retry)
# -------------------------------
def ask_llm(prompt, model="llama3:8b", retries=3):
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )

            response.raise_for_status()
            data = response.json()

            return data.get("response") or data.get("completion") or ""

        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed: {e}")
            time.sleep(2)

    return ""

# -------------------------------
# Scrape website (cleaned)
# -------------------------------
def scrape_website(url, max_pages=5):
    print(f"🔍 Fetching content from {url} ...")

    visited = set()
    to_visit = [url]
    content = []

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)

        try:
            r = requests.get(current_url, timeout=10)
            r.raise_for_status()
        except:
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        # Remove junk
        for s in soup(["script", "style", "nav", "footer", "header"]):
            s.decompose()

        text = soup.get_text(separator=" ", strip=True)

        # Skip very small or useless pages
        if len(text) > 300:
            content.append(text)

        # Crawl internal links
        for link in soup.find_all("a", href=True):
            href = link['href']

            if href.startswith("/"):
                full_url = url.rstrip("/") + href
            elif href.startswith("http") and url in href:
                full_url = href
            else:
                continue

            if full_url not in visited:
                to_visit.append(full_url)

    full_text = " ".join(content)
    full_text = re.sub(r"\s+", " ", full_text)

    return full_text


# -------------------------------
# Chunk text (optimized)
# -------------------------------
def chunk_text(text, max_chars=1500):
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]


# -------------------------------
# Extract JSON safely
# -------------------------------
def extract_json(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []

    try:
        return json.loads(match.group())
    except:
        return []


# -------------------------------
# Prompt template
# -------------------------------
def build_prompt(chunk, category):
    return f"""
You are a university FAQ generator.

Return ONLY valid JSON. No explanation.

STRICT FORMAT:
[
  ["question", "answer"],
  ["question", "answer"]
]

Rules:
- Max 5 FAQs
- Questions must sound natural
- Answers must be 1 sentence
- No duplicate questions

Category: {category}

Content:
{chunk}
"""


# -------------------------------
# Process single chunk
# -------------------------------
def process_chunk(args):
    chunk, category, model = args

    prompt = build_prompt(chunk, category)
    response = ask_llm(prompt, model=model)

    parsed = extract_json(response)

    if not parsed:
        print("⚠️ Failed to parse chunk")

    return parsed


# -------------------------------
# Generate FAQs (parallel)
# -------------------------------
def generate_faqs(text, category, model="llama3:8b"):
    chunks = chunk_text(text)

    # Limit chunks for speed (adjust if needed)
    chunks = chunks[:6]

    print(f"🧠 Processing {len(chunks)} chunks in parallel...")

    all_faqs = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(
            process_chunk,
            [(chunk, category, model) for chunk in chunks]
        )

    for res in results:
        all_faqs.extend(res)

    # Remove duplicates
    seen = set()
    unique_faqs = []

    for q, a in all_faqs:
        if q not in seen:
            seen.add(q)
            unique_faqs.append([q, a])

    return json.dumps(unique_faqs, indent=2, ensure_ascii=False)


# -------------------------------
# Main
# -------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="University URL")
    parser.add_argument("--category", default="general")
    parser.add_argument("--model", default="llama3:8b")

    args = parser.parse_args()

    text = scrape_website(args.url)

    print(f"🧠 Generating FAQs using {args.model} ...")

    faqs_json = generate_faqs(
        text,
        args.category,
        model=args.model
    )

    filename = f"{args.category}_faqs.json"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(faqs_json)

    print(f"✅ FAQs saved to {filename}")


# -------------------------------
if __name__ == "__main__":
    main()