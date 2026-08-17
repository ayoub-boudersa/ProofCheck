import os

def test_requires_api_url():
    api_url = os.environ.get("API_URL")
    assert api_url == "https://api.example.com"