import base64
import os
import socket
import time

import requests

OPENROUTER_MODEL = "google/gemma-4-31b-it:free"
GOOGLE_MODEL = "gemma-4-31b-it"


class GemmaError(Exception):
    """A Gemma failure explained in plain words. kind is one of MESSAGES' keys or 'unknown'."""
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind, self.message = kind, message


MESSAGES = {
    "no_internet": "Can't reach Gemma: no internet connection or the network is blocking it. Check Wi-Fi and try again.",
    "timeout": "Gemma took too long to answer (network or model is slow). Try again.",
    "credits": "Gemma request refused: no credits left or a billing/pricing limit on the API account. "
               "Top up or switch the API key.",
    "quota": "Gemma free-tier limit reached (too many requests or daily quota used). Wait a minute or use the other API key.",
    "auth": "Gemma API key is missing, wrong or expired. Check OPENROUTER_API_KEY / GEMINI_API_KEY.",
    "provider": "Gemma model isn't available on this account (provider or guardrail settings). "
                "Check OpenRouter privacy/guardrail settings.",
    "busy": "Gemma servers are busy or having an outage. Try again in a moment.",
}
NO_RETRY = {"auth", "credits", "provider"}  # retrying these never helps


class _HTTPStatus(Exception):
    """OpenRouter sometimes returns 200 with an error body; carry its code like google's APIError.code."""
    def __init__(self, code, text):
        super().__init__(text)
        self.code = code


def _chain(exc):
    while exc is not None:
        yield exc
        exc = exc.__cause__ or exc.__context__


def _kind(exc):
    names = " ".join(c.__name__ for e in _chain(exc) for c in type(e).__mro__)
    if isinstance(exc, (requests.Timeout, socket.timeout, TimeoutError)) or "Timeout" in names:
        return "timeout"
    if isinstance(exc, (requests.ConnectionError, ConnectionError, socket.gaierror)) \
            or any(n in names for n in ("ConnectError", "RemoteProtocolError", "NetworkError", "gaierror")):
        return "no_internet"
    code, text = None, str(exc)
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        code, text = exc.response.status_code, f"{exc.response.text} {exc}"
    code = code or getattr(exc, "code", None) or getattr(exc, "status_code", None)
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = None
    low = text.lower()
    if "server disconnected" in low or "getaddrinfo" in low or "name or service not known" in low:
        return "no_internet"
    # status code wins over text (OpenRouter's 429 body says "add credits", but it's a rate limit)
    by_code = {402: "credits", 429: "quota", 401: "auth", 403: "auth", 404: "provider"}
    if code in by_code:
        return by_code[code]
    if code and code >= 500:
        return "busy"
    words = [("quota", ("resource_exhausted", "rate limit", "rate-limit", "quota")),
             ("credits", ("credit", "insufficient", "payment", "billing")),
             ("auth", ("api key", "api_key", "unauthorized", "unauthenticated", "permission_denied", "expired")),
             ("provider", ("no allowed providers", "guardrail", "model not found", "no endpoints found")),
             ("busy", ("internal", "unavailable", "overloaded"))]
    return next((kind for kind, ws in words if any(w in low for w in ws)), "unknown")


def explain(exc):
    """Turn any backend exception into a GemmaError with a plain-words message."""
    if isinstance(exc, GemmaError):
        return exc
    kind = _kind(exc)
    msg = MESSAGES.get(kind) or f"Gemma failed: {(str(exc) or type(exc).__name__)[:150]}"
    return GemmaError(kind, msg)


def _messages(prompt, image=None):
    """OpenAI-style chat messages; image is (bytes, mime) and goes in as a data URL."""
    if not image:
        return [{"role": "user", "content": prompt}]
    url = f"data:{image[1]};base64,{base64.b64encode(image[0]).decode()}"
    return [{"role": "user", "content": [{"type": "text", "text": prompt},
                                         {"type": "image_url", "image_url": {"url": url}}]}]


def _openrouter(prompt, image=None):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={"model": OPENROUTER_MODEL, "messages": _messages(prompt, image)},
        timeout=40,
    )
    r.raise_for_status()
    data = r.json()
    if "choices" not in data:
        err = data.get("error") or {}
        raise _HTTPStatus(err.get("code"), str(err.get("message") or data)[:300])
    return data["choices"][0]["message"]["content"] or ""


def _ollama_payload(prompt, image, model):
    msg = {"role": "user", "content": prompt}
    if image:
        msg["images"] = [base64.b64encode(image[0]).decode()]
    return {"model": model, "messages": [msg], "stream": False, "think": False}  # think off: JSON only, faster


def _ollama(prompt, image=None):
    """Gemma 4 running locally in Ollama: no internet, no rate limits, data stays on this PC."""
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    r = requests.post(f"{host}/api/chat", json=_ollama_payload(prompt, image, os.environ["OLLAMA_MODEL"]),
                      timeout=180)  # ponytail: CPU inference is slow; 180s ceiling
    r.raise_for_status()
    return r.json()["message"]["content"] or ""


def _google(prompt, image=None):
    from google import genai
    from google.genai import types
    contents = [prompt, types.Part.from_bytes(data=image[0], mime_type=image[1])] if image else prompt
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return client.models.generate_content(model=GOOGLE_MODEL, contents=contents).text


def ask(prompt, image=None):
    """Gemma 4 31B: OpenRouter free first, Google AI Studio as fallback. Retries on load errors.
    Raises GemmaError with a plain-words reason."""
    backends = [(name, f) for name, f, k in (("Local Gemma", _ollama, "OLLAMA_MODEL"),
                                              ("OpenRouter", _openrouter, "OPENROUTER_API_KEY"),
                                              ("Google", _google, "GEMINI_API_KEY")) if os.environ.get(k)]
    if not backends:
        raise GemmaError("auth", "No Gemma API key set. Set OPENROUTER_API_KEY or GEMINI_API_KEY.")
    errs = {}
    for wait in (0, 2):  # ponytail: simple retry across backends, no circuit breaker
        live = [(n, f) for n, f in backends if n not in errs or errs[n].kind not in NO_RETRY]
        if not live:
            break
        time.sleep(wait)
        for name, backend in live:
            try:
                return backend(prompt, image)
            except Exception as e:
                errs[name] = explain(e)
    found = [errs[n] for n, _ in backends]
    best = next((e for e in found if e.kind != "unknown"), found[0])
    if len(found) > 1 and found[0].kind != found[1].kind:
        raise GemmaError(best.kind, " · ".join(f"{n}: {e.message}" for (n, _), e in zip(backends, found)))
    raise best


if __name__ == "__main__":
    print(ask("Reply with one short sentence in Roman Urdu: what is a spindle bearing?"))
