import json
import sys
import time
import urllib.error
import urllib.request

API = "http://localhost:8000/api/v1/process"

# FIX: Added with context manager
with open("eval/eval_set_50.jsonl") as f:
    rows = [json.loads(l) for l in f if l.strip()]


def call(text, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                API,
                data=json.dumps({"text": text, "source_type": "text"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
            return resp["decision"]["category"], None
        except urllib.error.HTTPError as e:
            if e.code == 500 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return None, f"HTTP {e.code}"
        except Exception as ex:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return None, str(ex)
    return None, "max retries"


c, t, e = 0, 0, []
for i, r in enumerate(rows):
    pred, err = call(r["text"])
    if err:
        e.append({"id": r["id"], "error": err})
        print(f"[{i + 1}/50] {r['id']} ERROR: {err}", file=sys.stderr)
        continue
    t += 1
    if pred == r["label"]:
        c += 1
    else:
        e.append({"id": r["id"], "truth": r["label"], "pred": pred})
    print(
        f"[{i + 1}/50] {r['id']} -> {pred} ({'OK' if pred == r['label'] else 'WRONG'})",
        file=sys.stderr,
    )
    time.sleep(1.5)  # rate limit ke liye

acc = c / t * 100 if t else 0
out = {
    "model": "openai/gpt-oss-120b",
    "eval_set": "eval_set_50_synthetic",
    "accuracy": acc,
    "correct": c,
    "total": t,
    "errors": e,
}

# FIX: Added with context manager
with open("eval/metrics_real.json", "w") as f:
    json.dump(out, f, indent=2)

print(f"\nREAL LLM accuracy: {acc:.2f}% ({c}/{t})")
print(f"Total attempted: 50 | Succeeded: {t} | Failed: {len(e)}")