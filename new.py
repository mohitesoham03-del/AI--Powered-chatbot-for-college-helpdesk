# offline_faq_extractor_final.py

import requests
from bs4 import BeautifulSoup
import argparse
import re
import json

# -------------------------------
# Helper function: ask Ollama
# -------------------------------
def ask_llm(prompt, model="llama3"):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        resp_json = response.json()
    except Exception as e:
        raise RuntimeError(f"Error connecting to Ollama API: {e}")

    # Handle different response keys
    if "response" in resp_json:
        return resp_json["response"]
    elif "completion" in resp_json:
        return resp_json["completion"]
    elif "error" in resp_json:
        raise ValueError(f"LLM returned an error: {resp_json['error']}")
    else:
        raise ValueError(f"Unexpected response from LLM: {resp_json}")

# -------------------------------
# Scrape website content
# -------------------------------
def scrape_website(url, max_pages=10):
    print(f"🔍 Fetching website content from {url} ...")
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
        except requests.RequestException:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        # Remove scripts, styles
        for s in soup(["script", "style"]):
            s.decompose()

        # Get text
        text = soup.get_text(separator=" ", strip=True)
        content.append(text)

        # Find internal links
        for link in soup.find_all("a", href=True):
            href = link['href']
            if href.startswith("/") and url.endswith("/"):
                full_url = url.rstrip("/") + href
            elif href.startswith("http") and url in href:
                full_url = href
            else:
                continue
            if full_url not in visited:
                to_visit.append(full_url)

    full_text = " ".join(content)
    # Clean extra spaces
    full_text = re.sub(r"\s+", " ", full_text)
    return full_text

# -------------------------------
# Generate FAQs using Ollama
# -------------------------------
def generate_faqs(text, category, model="llama3"):
    prompt = f"""
You are a university knowledge base extractor.

STRICT RULES:
- Create natural student questions
- Provide **short but complete answers** (1-2 sentences)
- Group by intent
- Do NOT copy text verbatim
- No HTML, no repetition

Output ONLY in JSON array:
[
  ["question", "answer"],
  ["question", "answer"]
]

Category: {category}

Content:
{text[:8000]}
"""
    return ask_llm(prompt, model=model)

# -------------------------------
# Main function
# -------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="University URL to scrape")
    parser.add_argument("--category", default="general", help="FAQ category")
    parser.add_argument("--model", default="llama3", help="Offline LLM model (llama3/mistral/phi3)")
    args = parser.parse_args()

    text = scrape_website(args.url)
    print(f"🧠 Generating FAQs using {args.model} ...")
    faqs_json = generate_faqs(text, args.category, model=args.model)

    # Save JSON
    filename = f"{args.category}_faqs.json"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(faqs_json)
    
    print(f"✅ FAQs saved to {filename}")
    print(faqs_json)

# -------------------------------
if __name__ == "__main__":
    main()