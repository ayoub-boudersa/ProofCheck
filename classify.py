import os
import json
import difflib
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

GUESSES_FILE = "guesses.jsonl"


def load_past_guesses():
    if not os.path.exists(GUESSES_FILE):
        return []
    past = []
    with open(GUESSES_FILE) as f:
        for line in f:
            past.append(json.loads(line))
    return past


def find_similar_guess(trace, past_guesses, threshold=0.9):
    for guess in past_guesses:
        similarity = difflib.SequenceMatcher(None, trace, guess["trace"]).ratio()
        if similarity >= threshold:
            return guess
    return None


def log_guess(test_name, trace, result, from_memory):
    entry = {
        "test_name": test_name,
        "trace": trace,
        "category": result["category"],
        "confidence": result["confidence"],
        "reason": result["reason"],
        "from_memory": from_memory,
    }
    with open(GUESSES_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def classify_failure(test_name, trace):
    prompt = f"""You are analyzing a failed pytest test. Classify it into exactly one category.

Test name: {test_name}
Traceback: {trace}

Categories (choose exactly one):
- real_bug: the code's logic is genuinely wrong
- flaky: the test fails inconsistently, likely due to randomness or timing
- environment: the test fails due to missing config, env vars, or external dependencies
- test_issue: the test itself is stale or asserting outdated behavior

Respond with ONLY valid JSON in this exact shape, nothing else:
{{"category": "...", "confidence": 0.0, "reason": "..."}}

- Avoid using exactly 1.0 or 0.0 for confidence — express genuine uncertainty, even on clear-cut cases.
"""

    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )

    raw_text = response.text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1].strip()
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"category": "unknown", "confidence": 0.0, "reason": "Could not parse model response", "raw": raw_text}


with open("report.json") as f:
    data = json.load(f)

failed_tests = [t for t in data["results"]["tests"] if t["status"] == "failed"]

past_guesses = load_past_guesses()

for test in failed_tests:
    match = find_similar_guess(test["trace"], past_guesses)

    if match:
        result = {
            "category": match["category"],
            "confidence": match["confidence"],
            "reason": match["reason"],
        }
        from_memory = True
    else:
        result = classify_failure(test["name"], test["trace"])
        from_memory = False
        log_guess(test["name"], test["trace"], result, from_memory)

    
    if result["confidence"] < 0.7:
        flag = "⚠️ NEEDS REVIEW"
    else:
        flag = ""

    memory_tag = "📋 FROM MEMORY" if from_memory else "🔵 NEW"

    print(f"{test['name']} {flag} {memory_tag}")
    print(result)
    print("—" * 120)