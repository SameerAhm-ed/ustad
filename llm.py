import os
import time

import requests

OPENROUTER_MODEL = "google/gemma-4-31b-it:free"
GOOGLE_MODEL = "gemma-4-31b-it"


def _openrouter(prompt):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}]},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"] or ""


def _google(prompt):
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return client.models.generate_content(model=GOOGLE_MODEL, contents=prompt).text


def ask(prompt):
    """Gemma 4 31B: OpenRouter free first, Google AI Studio as fallback. Retries on load errors."""
    backends = [f for f, k in ((_openrouter, "OPENROUTER_API_KEY"), (_google, "GEMINI_API_KEY")) if os.environ.get(k)]
    if not backends:
        raise RuntimeError("Set OPENROUTER_API_KEY or GEMINI_API_KEY")
    err = None
    for wait in (0, 2):  # ponytail: simple retry across backends, no circuit breaker
        for backend in backends:
            try:
                return backend(prompt)
            except Exception as e:
                err = e
        time.sleep(wait)
    raise err


if __name__ == "__main__":
    print(ask("Reply with one short sentence in Roman Urdu: what is a spindle bearing?"))
