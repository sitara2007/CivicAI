import json
import sys
import urllib.request

API = "http://localhost:8000/api/v1/process"
GT = "eval/ground_truth_classification.jsonl"

# FIX: Added with context manager
with open(GT) as f:
    rows = [json.loads(line) for line in f if line.strip()]

if not rows:
    print("Empty ground truth")
    sys.exit(1)

correct, total, errors = 0, 0, []
for row in rows:
    text, truth = row.get("text", ""), row.get("label", "")
    if not text or not truth:
        continue
    try:
        req = urllib.request.Request(
            API,
            data=json.dumps({"text": text, "source_type": "text"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        pred = resp["decision"]["category"] if resp.get("decision") else "None"
    except Exception as e:
        print(f"API err: {e}", file=sys.stderr)
        continue
    total += 1
    if pred == truth:
        correct += 1
    else:
        errors.append({"id": row["id"], "truth": truth, "pred": pred})

acc = correct / total * 100 if total else 0
print(f"Classification accuracy: {acc:.2f}% ({correct}/{total})")

# FIX: Added with context manager
with open("eval/metrics_classification.json", "w") as f:
    json.dump(
        {"accuracy": acc, "correct": correct, "total": total, "errors": errors},
        f,
        indent=2,
    )
