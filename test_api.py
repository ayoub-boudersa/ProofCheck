import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

test_name = "fake_suite/test_real_bug.py::test_cart_total"
trace = """def test_cart_total():
>       assert calculate_total(10, 2) == 20
E       assert 21 == 20
E        +  where 21 = calculate_total(10, 2)"""

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

print(response.text)