#!/usr/bin/env python3
"""post-freeze, real data: label raw Backstage questions without existing gold."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
import ssl
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = None

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
load_dotenv(ROOT / ".env")
RAW = (ROOT / "real/raw/backstage").resolve()
DATASET = "post-freeze, real data"
NOTE = "labeler = gpt-oss-120b (also the grader); author review pending"
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "evidence_paths": {"type": "array", "items": {"type": "string"}},
        "short_reason": {"type": "string"},
    },
    "required": ["answer", "evidence_paths", "short_reason"],
    "additionalProperties": False,
}


def save(path, value):
    """Replace atomically so an interruption preserves the previous partial file."""
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        f.write(value)
        temp = Path(f.name)
    temp.replace(path)


def payload(question):
    evidence = {}
    for name in question["evidence_files"]:
        path = (ROOT / name).resolve()
        if not path.is_relative_to(RAW) or not path.is_file():
            raise ValueError("Evidence must be an existing raw Backstage file")
        evidence[name] = path.read_text()
    return {
        "model": MODEL,
        "temperature": 0,
        "reasoning_effort": "low",
        "max_completion_tokens": 2048,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "blind_label", "strict": True, "schema": SCHEMA},
        },
        "messages": [{"role": "user", "content": json.dumps({
            "question": question["question"], "evidence_files": evidence,
        })}],
    }


def label(response, question):
    choice = response["choices"][0]
    if choice.get("finish_reason") != "stop":
        raise ValueError("Incomplete response; cached for inspection")
    value = json.loads(choice["message"]["content"])
    if set(value) != set(SCHEMA["required"]):
        raise ValueError("Unexpected label fields")
    if not all(isinstance(value[k], str) and value[k].strip()
               for k in ("answer", "short_reason")):
        raise ValueError("Empty or invalid answer/reason")
    paths = value["evidence_paths"]
    if not isinstance(paths, list) or not paths or not all(
        isinstance(p, str) and p in question["evidence_files"] for p in paths
    ):
        raise ValueError("Label cites paths outside its evidence")
    return dict(id=question["id"], dataset=DATASET, **value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-budget", type=int, default=100000,
                        help="Cumulative token cap, including cached calls (default: 100000)")
    args = parser.parse_args()
    if args.token_budget <= 0:
        parser.error("token budget must be positive")
    cache = HERE / "cache"
    cache.mkdir(exist_ok=True)
    questions = [json.loads(line) for line in
                 (HERE / "questions.jsonl").read_text().splitlines() if line.strip()]
    if len(questions) != 10 or len({q["id"] for q in questions}) != 10:
        raise ValueError("Expected ten distinct question IDs")
    header = {"_meta": {"dataset": DATASET, "note": NOTE}}
    rows = [header]
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    used_now = 0
    status = "running"

    def checkpoint():
        save(HERE / "gold_blind.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
        save(HERE / "usage.json", json.dumps({
            "dataset": DATASET, "note": NOTE, "model": MODEL, "status": status,
            "labels": len(rows) - 1, "token_budget": args.token_budget,
            "tokens": totals, "tokens_used_this_run": used_now,
        }, indent=2) + "\n")

    checkpoint()
    try:
        for question in questions:
            request = payload(question)
            body = json.dumps(request, sort_keys=True).encode()
            key = hashlib.sha256(body).hexdigest()
            cached = cache / (key + ".json")
            if cached.exists():
                response = json.loads(cached.read_text())
            else:
                # UTF-8 bytes bound input tokens conservatively; reserve output and framing too.
                reserve = len(body) + request["max_completion_tokens"] + 512
                if totals["total_tokens"] + reserve > args.token_budget:
                    status = "token_budget_stop"
                    break
                api_key = os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY")
                if not api_key:
                    status = "missing_LLM_API_KEY"
                    break
                base_url = (os.environ.get("LLM_BASE_URL") or "https://api.groq.com/openai/v1").rstrip("/")
                endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
                http = urllib.request.Request(
                    endpoint, data=body,
                    headers={"Authorization": "Bearer " + api_key,
                             "Content-Type": "application/json",
                             "User-Agent": "OpenAI/Python"}, method="POST",
                )
                try:
                    kwargs = {"timeout": 180}
                    if SSL_CONTEXT is not None:
                        kwargs["context"] = SSL_CONTEXT
                    with urllib.request.urlopen(http, **kwargs) as result:
                        response = json.load(result)
                except urllib.error.HTTPError as exc:
                    status = "rate_limited_429" if exc.code == 429 else f"http_error_{exc.code}"
                    break  # No retries: preserve partial labels and budget.
                save(cached, json.dumps(response) + "\n")
                used_now += response.get("usage", {}).get("total_tokens", 0)
            usage = response["usage"]
            for field in totals:
                if not isinstance(usage.get(field), int) or usage[field] < 0:
                    raise ValueError("Missing or invalid token accounting")
                totals[field] += usage[field]
            if totals["total_tokens"] > args.token_budget:
                status = "token_budget_stop"
                break
            rows.append(label(response, question))
            checkpoint()
            print(f"{question['id']}: cached label saved; tokens={totals['total_tokens']}")
        else:
            status = "complete"
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        status = "error_stop; inspect local cache; no automatic retry"
    finally:
        checkpoint()
    print(json.dumps({"status": status, "labels": len(rows) - 1,
                      "tokens": totals, "tokens_used_this_run": used_now}))
    return 0 if status == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
