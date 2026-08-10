import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

for test in failed_tests:
    result = classify_failure(test["name"], test["trace"])
    
    if result["confidence"] < 0.7:
        flag = "⚠️ NEEDS REVIEW"
    else:
        flag = ""
    
    print(f"{test['name']} {flag}")
    print(result)
    print("—" * 120)