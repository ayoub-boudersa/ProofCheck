import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMENI_API_KEY"))

response = client.models.generate_content(
    model="gemini-flash-lite-latest",
    contents="Say hello in one sentence."
)

print(response.text)