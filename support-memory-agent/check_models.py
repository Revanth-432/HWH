import os
import requests
from dotenv import load_dotenv

load_dotenv('backend/.env')
api_key = os.environ.get("GROQ_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)

print("\n=== YOUR ACTIVE GROQ MODELS ===")
for m in response.json().get("data", []):
    print(m["id"])