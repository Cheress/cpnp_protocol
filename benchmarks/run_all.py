"""
cpnp/benchmarks/run_all.py
────────────────────────────
Master runner — executes all four CPNP evaluation experiments in sequence
and produces a consolidated results summary.

Run:
  python benchmarks/run_all.py

This runs:
  1. benchmark.py          — latency (per-operation + end-to-end)
  2. security_eval.py      — adversarial detection (13 attacks)
  3. throughput_eval.py    — operations per second
  4. expressiveness_eval.py — robots.txt vs CPNP policy dimensions

All raw data + summaries land in results/.
"""
import sys, os, subprocess, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")

EXPERIMENTS = [
    ("Latency Benchmark", "benchmark.py", ["--iterations", "1000", "--warmup", "100"]),
    ("Security Evaluation", "security_eval.py", ["--trials", "100"]),
    ("Throughput Evaluation", "throughput_eval.py", ["--duration", "5"]),
    ("Expressiveness Evaluation", "expressiveness_eval.py", []),
]

def main():
    print("\n" + "#"*72)
    print("#  CPNP FULL EVALUATION SUITE")
    print("#  Running all four experiments ")
    print("#"*72)

    for title, script, extra_args in EXPERIMENTS:
        print(f"\n\n>>> {title}  ({script})")
        subprocess.run([sys.executable, os.path.join(HERE, script)] + extra_args, check=True)

    # Consolidate headline numbers
    print("\n\n" + "#"*72)
    print("#  CONSOLIDATED RESULTS")
    print("#"*72 + "\n")

    try:
        with open(os.path.join(RESULTS, "summary_statistics.csv")) as f:
            import csv
            rows = list(csv.DictReader(f))
            e2e = next(r for r in rows if r["operation"] == "10_e2e_handshake")
            print(f"  Handshake latency (mean):     {e2e['mean_ms']} ms")
            print(f"  Handshake latency (p95):      {e2e['p95_ms']} ms")
            print(f"  Handshake latency (p99):      {e2e['p99_ms']} ms")
    except Exception as e:
        print(f"  (latency summary unavailable: {e})")

    try:
        with open(os.path.join(RESULTS, "confusion_matrix.json")) as f:
            cm = json.load(f)
            print(f"  Adversarial detection rate:   {cm['detection_rate_pct']}%")
            print(f"  False positive rate:          {cm['false_positive_legitimate_rejected']} / {cm['true_negative_legitimate_accepted'] + cm['false_positive_legitimate_rejected']}")
            print(f"  Total security trials:        {cm['total_trials']}")
    except Exception as e:
        print(f"  (security summary unavailable: {e})")

    try:
        with open(os.path.join(RESULTS, "throughput_results.csv")) as f:
            import csv
            rows = list(csv.DictReader(f))
            hs = next(r for r in rows if r["operation"] == "full_handshake")
            tv = next(r for r in rows if r["operation"] == "token_verify_per_request")
            print(f"  Sustained handshakes/sec/core: {hs['ops_per_sec']}")
            print(f"  Token checks/sec/core:         {tv['ops_per_sec']}")
    except Exception as e:
        print(f"  (throughput summary unavailable: {e})")

    try:
        with open(os.path.join(RESULTS, "expressiveness_results.csv")) as f:
            import csv
            rows = list(csv.DictReader(f))
            cpnp_yes = sum(1 for r in rows if r["cpnp"] == "YES")
            robots_yes = sum(1 for r in rows if r["robots_txt"] == "YES")
            print(f"  Policy dimensions — CPNP:      {cpnp_yes}/{len(rows)}")
            print(f"  Policy dimensions — robots.txt:{robots_yes}/{len(rows)}")
    except Exception as e:
        print(f"  (expressiveness summary unavailable: {e})")

    print(f"\n  All raw data and CSVs are in: {RESULTS}/")


if __name__ == "__main__":
    main()
