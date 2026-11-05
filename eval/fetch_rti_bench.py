#!/usr/bin/env python3
"""Stream and reservoir-sample the RTI benchmark CSV."""

import argparse
import csv
import io
import random
import sys
import urllib.request

URL = (
    "https://huggingface.co/datasets/joyboseroy/rti-bench/resolve/main/"
    "cic_combined.csv?download=true"
)


def reservoir_sample(stream, size, seed):
    rng = random.Random(seed)
    reader = csv.DictReader(stream)
    sample = []

    for row_number, row in enumerate(reader):
        if row_number < size:
            sample.append(row)
            continue

        replacement_index = rng.randrange(row_number + 1)
        if replacement_index < size:
            sample[replacement_index] = row

    if reader.fieldnames is None:
        raise ValueError("The downloaded CSV does not contain a header.")
    return sample, reader.fieldnames


def main():
    parser = argparse.ArgumentParser(
        description="Download and reservoir-sample the RTI benchmark CSV."
    )
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="eval/rti_bench_sample.csv")
    args = parser.parse_args()
    if args.size <= 0:
        parser.error("--size must be greater than zero")

    print(f"Streaming {URL}", file=sys.stderr)
    with urllib.request.urlopen(URL, timeout=60) as response:
        text_stream = io.TextIOWrapper(response, encoding="utf-8", newline="")
        sample, fieldnames = reservoir_sample(text_stream, args.size, args.seed)

    with open(args.out, "w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample)

    print(f"Wrote {len(sample)} sampled rows to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
