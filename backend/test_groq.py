import os, json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

resp = client.chat.completions.create(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    messages=[{"role": "user", "content": 'Reply ONLY with JSON: {"ok": true}'}],
    max_tokens=50,
)
print(resp.choices[0].message.content)