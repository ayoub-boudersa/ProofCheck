import os
import json
import difflib
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

GUESSES_FILE = "guesses.jsonl"
STATS_FILE = "stats.json"


def call_gemini(prompt):
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt
    )
    return response.text


def call_openai(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def call_anthropic(prompt):
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


PROVIDERS = {
    "gemini": call_gemini,
    "openai": call_openai,
    "anthropic": call_anthropic,
}


def load_past_guesses():
    if not os.path.exists(GUESSES_FILE):
        return []
    past = []
    with open(GUESSES_FILE) as f:
        for line in f:
            past.append(json.loads(line))
    return past


def find_similar_guess(test_name, trace, past_guesses, trace_threshold=0.9, name_threshold=0.9):
    for guess in past_guesses:
        trace_similarity = difflib.SequenceMatcher(None, trace, guess["trace"]).ratio()
        name_similarity = difflib.SequenceMatcher(None, test_name, guess["test_name"]).ratio()
        if trace_similarity >= trace_threshold and name_similarity >= name_threshold:
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


def load_stats():
    if not os.path.exists(STATS_FILE):
        return {"new": 0, "from_memory": 0}
    with open(STATS_FILE) as f:
        return json.load(f)


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


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

    call_fn = PROVIDERS.get(LLM_PROVIDER)
    if call_fn is None:
        return {"category": "unknown", "confidence": 0.0, "reason": f"Unknown LLM_PROVIDER: '{LLM_PROVIDER}'"}

    raw_text = call_fn(prompt).strip()

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
stats = load_stats()

for test in failed_tests:
    match = find_similar_guess(test["name"], test["trace"], past_guesses)

    if match:
        result = {
            "category": match["category"],
            "confidence": match["confidence"],
            "reason": match["reason"],
        }
        from_memory = True
        stats["from_memory"] += 1
    else:
        result = classify_failure(test["name"], test["trace"])
        from_memory = False
        stats["new"] += 1
        log_guess(test["name"], test["trace"], result, from_memory)

    if result["confidence"] < 0.7:
        flag = "NEEDS REVIEW"
    else:
        flag = ""

    memory_tag = "FROM MEMORY" if from_memory else "NEW"

    print(f"{test['name']} {flag} {memory_tag}")
    print(result)
    print("—" * 120)

save_stats(stats)

total = stats["new"] + stats["from_memory"]
if total > 0:
    hit_rate = stats["from_memory"] / total * 100
    print(f"\nMemory hit rate (all-time): {stats['from_memory']}/{total} ({hit_rate:.0f}%)")