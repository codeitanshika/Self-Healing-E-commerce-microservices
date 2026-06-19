"""
llm.py
======
The ONE place in this codebase that calls the LLM (Groq).

Why centralize this?
- If we ever switch providers/models, we change ONE file.
- Every agent that needs AI reasoning imports `ask_llm` from here.
- We handle the "LLM sometimes returns broken JSON" problem
  in exactly one place, with one safe fallback.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def ask_llm(prompt: str) -> dict:
    """
    Sends a prompt to Groq and returns a parsed JSON dict.

    IMPORTANT: this function ALWAYS returns a dict.
    If the LLM call fails, or returns text that isn't valid JSON,
    we return a safe default instead of crashing the whole agent.
    This matches the rule in code-standards.md.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.2,   # low temperature = more consistent, less "creative"
        )
        raw_text = response.choices[0].message.content

        # LLMs sometimes wrap JSON in ```json ... ``` — strip that if present
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()

        return json.loads(cleaned)

    except json.JSONDecodeError:
        print(f"[llm.py] ⚠️  LLM returned invalid JSON: {raw_text[:200]}")
        return _safe_default()

    except Exception as e:
        print(f"[llm.py] ⚠️  LLM call failed: {e}")
        return _safe_default()


def _safe_default() -> dict:
    """
    Fallback diagnosis when the LLM fails for any reason.
    Defaulting to 'restart' is safe because restart fixes
    the most common failure type (crashes).
    """
    return {
        "root_cause":      "unknown",
        "confidence":      0,
        "fix":             "restart",
        "business_impact": "unknown — LLM diagnosis failed",
        "explanation":     "Defaulted because the LLM call failed or returned invalid JSON.",
    }