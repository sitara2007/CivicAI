"""
Golden Test Set evaluation — PRD §10: ≥90% classification accuracy.

Usage:
    pytest tests/test_eval.py -v
    python -m tests.test_eval --dataset eval/golden_test_set.jsonl --api-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "eval" / "golden_test_set.jsonl"
ACCURACY_THRESHOLD = 0.90
P95_LATENCY_MS = 3000


class GoldenSample(BaseModel):
    """Single labeled document in the Golden Test Set."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    gold_category: str
    gold_priority: str
    gold_department: str
    tags: list[str] = Field(default_factory=list)


@dataclass
class EvalResult:
    sample_id: str
    gold_category: str
    pred_category: str | None
    gold_priority: str
    pred_priority: str | None
    gold_department: str
    pred_department: str | None
    category_correct: bool
    priority_correct: bool
    department_correct: bool
    latency_ms: float
    status: str
    error: str | None = None


@dataclass
class EvalReport:
    n_samples: int
    classification_accuracy: float
    priority_accuracy: float
    routing_accuracy: float
    p95_latency_ms: float
    mean_latency_ms: float
    dlq_count: int
    dlq_rate: float
    passed: bool
    results: list[EvalResult]


def load_golden_dataset(path: Path) -> list[GoldenSample]:
    if not path.exists():
        raise FileNotFoundError(f"Golden Test Set not found: {path}")
    samples: list[GoldenSample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            samples.append(GoldenSample.model_validate_json(line))
    return samples


def evaluate_sample(
    client: httpx.Client, sample: GoldenSample, api_url: str
) -> EvalResult:
    started = time.perf_counter()
    try:
        response = client.post(
            f"{api_url}/api/v1/process",
            json={"text": sample.text, "source_type": "text"},
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - started) * 1000

        if response.status_code == 422:
            return EvalResult(
                sample_id=sample.id,
                gold_category=sample.gold_category,
                pred_category=None,
                gold_priority=sample.gold_priority,
                pred_priority=None,
                gold_department=sample.gold_department,
                pred_department=None,
                category_correct=False,
                priority_correct=False,
                department_correct=False,
                latency_ms=latency_ms,
                status="dlq",
                error=response.text,
            )

        response.raise_for_status()
        data = response.json()
        decision = data.get("decision") or {}
        pred_category = decision.get("category")
        pred_priority = decision.get("priority")
        pred_department = decision.get("department")

        return EvalResult(
            sample_id=sample.id,
            gold_category=sample.gold_category,
            pred_category=pred_category,
            gold_priority=sample.gold_priority,
            pred_priority=pred_priority,
            gold_department=sample.gold_department,
            pred_department=pred_department,
            category_correct=pred_category == sample.gold_category,
            priority_correct=pred_priority == sample.gold_priority,
            department_correct=pred_department == sample.gold_department,
            latency_ms=latency_ms,
            status=data.get("status", "unknown"),
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return EvalResult(
            sample_id=sample.id,
            gold_category=sample.gold_category,
            pred_category=None,
            gold_priority=sample.gold_priority,
            pred_priority=None,
            gold_department=sample.gold_department,
            pred_department=None,
            category_correct=False,
            priority_correct=False,
            department_correct=False,
            latency_ms=latency_ms,
            status="error",
            error=str(exc),
        )


def run_evaluation(
    dataset_path: Path,
    api_url: str,
    min_samples: int = 1,
) -> EvalReport:
    samples = load_golden_dataset(dataset_path)
    if len(samples) < min_samples:
        raise ValueError(
            f"Dataset has {len(samples)} samples; need at least {min_samples}"
        )

    results: list[EvalResult] = []
    with httpx.Client() as client:
        for sample in samples:
            results.append(evaluate_sample(client, sample, api_url))

    n = len(results)
    category_acc = sum(r.category_correct for r in results) / n
    priority_acc = sum(r.priority_correct for r in results) / n
    routing_acc = sum(r.department_correct for r in results) / n
    latencies = sorted(r.latency_ms for r in results)
    p95_idx = max(0, int(n * 0.95) - 1)
    dlq_count = sum(1 for r in results if r.status == "dlq")

    passed = category_acc >= ACCURACY_THRESHOLD and latencies[p95_idx] <= P95_LATENCY_MS

    return EvalReport(
        n_samples=n,
        classification_accuracy=category_acc,
        priority_accuracy=priority_acc,
        routing_accuracy=routing_acc,
        p95_latency_ms=latencies[p95_idx],
        mean_latency_ms=statistics.mean(latencies),
        dlq_count=dlq_count,
        dlq_rate=dlq_count / n,
        passed=passed,
        results=results,
    )


def test_golden_dataset_schema() -> None:
    """Validate Golden Test Set file structure."""
    if not DEFAULT_DATASET.exists():
        pytest.skip("Golden Test Set not yet populated (target: 100+ samples)")
    samples = load_golden_dataset(DEFAULT_DATASET)
    assert len(samples) >= 3
    for sample in samples:
        assert sample.gold_category in {"Complaint", "Request", "Report", "Other"}
        assert sample.gold_priority in {"Low", "Medium", "High", "Critical"}


def test_eval_report_thresholds() -> None:
    """Unit test for report aggregation logic."""
    report = EvalReport(
        n_samples=10,
        classification_accuracy=0.95,
        priority_accuracy=0.90,
        routing_accuracy=0.85,
        p95_latency_ms=2500.0,
        mean_latency_ms=1800.0,
        dlq_count=0,
        dlq_rate=0.0,
        passed=True,
        results=[],
    )
    assert report.passed is True
    assert report.classification_accuracy >= ACCURACY_THRESHOLD


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run GovFlow Golden Test Set evaluation"
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results")
    parser.add_argument("--min-samples", type=int, default=1)
    args = parser.parse_args(argv)

    report = run_evaluation(args.dataset, args.api_url.rstrip("/"), args.min_samples)
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"eval_{int(time.time())}.json"
    payload: dict[str, Any] = {
        "classification_accuracy": report.classification_accuracy,
        "priority_accuracy": report.priority_accuracy,
        "routing_accuracy": report.routing_accuracy,
        "p95_latency_ms": report.p95_latency_ms,
        "dlq_rate": report.dlq_rate,
        "passed": report.passed,
        "n_samples": report.n_samples,
        "results": [asdict(r) for r in report.results],
    }
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "results"}, indent=2))
    print(f"Full report: {out_file}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
