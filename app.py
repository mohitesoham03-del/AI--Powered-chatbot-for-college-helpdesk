from flask import Flask, render_template, jsonify
from data import DATA
import os


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/categories')
def get_categories():
    return jsonify(list(DATA.keys()))

@app.route('/api/questions/<category>')
def get_questions(category):
    if category in DATA:
        questions = [item[0] for item in DATA[category]]
        return jsonify(questions)
    return jsonify({"error": "Category not found"}), 404

@app.route('/api/answer/<category>/<int:index>')
def get_answer(category, index):
    if category in DATA and 0 <= index < len(DATA[category]):
        return jsonify({"answer": DATA[category][index][1]})
    return jsonify({"error": "Answer not found"}), 404

from flask import request

STOP_WORDS = {"what", "are", "is", "the", "a", "an", "and", "or", "but", "if", "then", 
              "when", "why", "how", "all", "any", "some", "no", "not", "can", 
              "will", "do", "does", "did", "to", "in", "of", "for", "with", "on", "at", 
              "by", "from", "it", "this", "that", "there", "their", "about", "me", "tell"}

SYNONYM_GROUPS = [
    {"located", "locations", "location", "map", "address", "where", "place"},
    {"fee", "fees", "payment", "payments", "cost", "price", "charge", "charges"},
    {"hostel", "accommodation", "room", "stay", "mess", "food", "meals"},
    {"admission", "admissions", "apply", "application", "enroll", "enrollment", "join"},
    {"document", "documents", "certificate", "certificates", "proof", "marksheets"},
    {"placement", "placements", "job", "jobs", "career", "careers", "company", "companies", "hire", "hiring"},
    {"transport", "bus", "travel", "commute"},
    {"brochure", "brochures", "program", "programs", "pdf", "download", "syllabus", "course", "courses"},
]

import re

def extract_words(text):
    # Extract only alphanumeric words, ignoring punctuation
    return set(re.findall(r'\b\w+\b', text.lower()))

@app.route('/api/search')
def search_questions():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    # Filter out common stop words
    base_words = [w for w in query.split() if w not in STOP_WORDS]
    if not base_words:
        base_words = [query]
        
    expanded_words = set(base_words)
    for word in base_words:
        word_singular = word[:-1] if word.endswith('s') else word
        for group in SYNONYM_GROUPS:
            if word in group or word_singular in group:
                expanded_words.update(group)
    
    query_words = list(expanded_words)
        
    results = []
    for category, items in DATA.items():
        category_words = extract_words(category)
        for index, item in enumerate(items):
            question = item[0]
            question_lower = question.lower()
            question_words = extract_words(question)
            answer_words = extract_words(item[1])
            
            all_target_words = question_words.union(answer_words).union(category_words)
            
            match = False
            # Always match if the exact phrase is found
            if query in question_lower:
                match = True
            else:
                for word in query_words:
                    word_singular = word[:-1] if word.endswith('s') else word
                    
                    # Match only whole words to prevent "place" from matching "placement"
                    if word in all_target_words:
                        match = True
                        break
                    elif len(word_singular) > 2 and word_singular in all_target_words:
                        match = True
                        break
            
            if match:
                results.append({
                    "category": category,
                    "index": index,
                    "question": question
                })
    
    return jsonify(results)

# if __name__ == '__main__':
#     app.run(debug=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)