import requests, os, json
import dotenv
dotenv.load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
message = "Fixed API latency issue, reviewed PR #112, started DB schema changes."

payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {"role": "system", "content": "Extract work tasks from text. Return STRICT JSON only."},
        {"role": "user", "content": f'{{"text": "{message}"}}'}
    ]
}

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
print(res.status_code, res.text)
