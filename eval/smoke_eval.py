#!/usr/bin/env python3
"""Run a local API smoke test against a sampled RTI-Bench input CSV."""

import csv
import json
import math
import time
import urllib.error
import urllib.request
from collections import Counter

INPUT_PATH = "eval/smoke_sample.csv"
OUTPUT_PATH = "eval/smoke_results.json"
PROCESS_URL = "http://127.0.0.1:8000/api/v1/process"
TIMEOUT_SECONDS = 60


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def read_samples():
    with open(INPUT_PATH, "r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "information_sought" not in reader.fieldnames:
            raise ValueError(f"{INPUT_PATH} must contain information_sought column")
        rows = [row for row in reader if (row.get("information_sought") or "").strip()]
    if not rows:
        raise ValueError(f"{INPUT_PATH} contains no non-empty information_sought rows")
    return rows


def classify(text):
    request = urllib.request.Request(
        PROCESS_URL,
        data=json.dumps({"text": text, "source_type": "text"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            http_code = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        http_code = error.code
        body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"error": body}
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        return {
            "http_code": None,
            "status": None,
            "decision": {
                "category": None,
                "priority": None,
                "department": None,
                "confidence": None,
            },
            "requires_review": None,
            "pii_entities_masked": 0,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "error": str(error),
        }, {}

    latency_ms = (time.perf_counter() - started) * 1000
    if not isinstance(payload, dict):
        payload = {"error": "API response was not a JSON object"}

    raw_decision = payload.get("decision")
    if not isinstance(raw_decision, dict):
        raw_decision = {}
    decision = {
        "category": raw_decision.get("category"),
        "priority": raw_decision.get("priority"),
        "department": raw_decision.get("department"),
        "confidence": raw_decision.get("confidence"),
    }

    pii_masked = payload.get("pii_entities_masked", 0)
    if not isinstance(pii_masked, int) or isinstance(pii_masked, bool):
        pii_masked = 0

    record = {
        "http_code": http_code,
        "status": payload.get("status"),
        "decision": decision,
        "requires_review": payload.get("requires_review"),
        "pii_entities_masked": pii_masked,
        "latency_ms": latency_ms,
    }
    if "error" in payload or http_code >= 400:
        record["error"] = payload.get("detail", payload.get("error", payload))
    return record, raw_decision


def main():
    samples = read_samples()
    results = []
    latencies = []
    categories = Counter()
    departments = Counter()
    decision_signatures = set()
    successful = 0
    pii_total = 0

    for row in samples:
        record, raw_decision = classify(row["information_sought"].strip())
        record["hf_id"] = row.get("hf_id", "")
        results.append(record)
        latencies.append(record["latency_ms"])
        pii_total += record["pii_entities_masked"]

        if record["http_code"] is not None and 200 <= record["http_code"] < 300:
            if record["status"] == "completed" and raw_decision:
                successful += 1
            if raw_decision:
                decision_signatures.add(
                    json.dumps(raw_decision, sort_keys=True, separators=(",", ":"))
                )
                category = raw_decision.get("category")
                department = raw_decision.get("department")
                if category is not None:
                    categories[str(category)] += 1
                if department is not None:
                    departments[str(department)] += 1

    summary = {
        "sample_size": len(samples),
        "successful": successful,
        "success_rate_percent": successful / len(samples) * 100,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "category_distribution": dict(sorted(categories.items())),
        "department_distribution": dict(sorted(departments.items())),
        "total_pii_entities_masked": pii_total,
        "distinct_decisions": len(decision_signatures),
        "same_decision_for_every_successful_input": (
            successful > 0 and len(decision_signatures) == 1
        ),
    }
    output = {
        "label": "smoke test, MOCK_LLM=true, not accuracy",
        "endpoint": PROCESS_URL,
        "summary": summary,
        "results": results,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as destination:
        json.dump(output, destination, ensure_ascii=False, indent=2)
        destination.write("\n")

    print("smoke test, MOCK_LLM=true, not accuracy")
    print(
        f"Success rate: {successful}/{len(samples)} ({summary['success_rate_percent']:.2f}%)"
    )
    print(f"Latency p50: {summary['p50_latency_ms']:.2f} ms")
    print(f"Latency p95: {summary['p95_latency_ms']:.2f} ms")
    print(f"Category distribution: {summary['category_distribution']}")
    print(f"Distinct categories: {sorted(categories)}")
    print(f"Department distribution: {summary['department_distribution']}")
    print(f"Distinct departments: {sorted(departments)}")
    print(f"Total PII masked: {pii_total}")
    print(f"Distinct full decisions: {summary['distinct_decisions']}")
    print(
        "Same decision for every successful input: "
        f"{summary['same_decision_for_every_successful_input']}"
    )
    print(f"Results written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
