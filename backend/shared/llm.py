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
import asyncio
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DEFAULT_MODEL = "openai/gpt-oss-120b"


def current_model() -> str:
    """
    Resolved on EVERY call, not at import. The experiment runners select the
    model by setting GROQ_MODEL after the modules are imported; reading it
    once at import time would silently ignore that and always use the default.
    """
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL)


# Reasoning models (e.g. gpt-oss) spend part of the token budget "thinking"
# before they emit the JSON answer. The original limit of 400 truncated a
# measurable share of answers mid-object (see docs/results/strategy-comparison.md,
# first run), which silently degraded to the safe default.
MAX_TOKENS = 1500
MAX_ATTEMPTS = 2   # one retry on an unusable answer before falling back


def parse_json_object(raw_text: str) -> dict:
    """
    Pull the first complete JSON object out of an LLM reply. Tolerates
    markdown fences and prose around the object. Raises ValueError if no
    valid object is found (including a truncated one).
    """
    cleaned = (raw_text or "").replace("```json", "").replace("```", "").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    obj = json.loads(cleaned[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("reply JSON is not an object")
    return obj


async def ask_llm(prompt: str) -> dict:
    """
    Sends a prompt to Groq and returns a parsed JSON dict.

    IMPORTANT: this function ALWAYS returns a dict.
    If the LLM call fails, or keeps returning unusable text after one retry,
    we return a safe default instead of crashing the whole agent.
    This matches the rule in code-standards.md.

    The Groq client is synchronous (blocking network I/O). Run it in
    a worker thread via asyncio.to_thread so a slow/rate-limited call
    for one incident doesn't freeze the whole event loop.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw_text = ""
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=current_model(),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                temperature=0.2,   # low temperature = more consistent, less "creative"
            )
            raw_text = response.choices[0].message.content or ""
            return parse_json_object(raw_text)
        except (ValueError, json.JSONDecodeError):
            print(f"[llm.py] ⚠️  unusable LLM reply (attempt {attempt}/{MAX_ATTEMPTS}): {raw_text[:120]!r}")
        except Exception as e:
            print(f"[llm.py] ⚠️  LLM call failed (attempt {attempt}/{MAX_ATTEMPTS}): {e}")
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