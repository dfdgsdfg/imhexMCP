#!/usr/bin/env python3
"""
Benchmark Comparison and Regression Testing

Compares benchmark results across multiple runs to detect performance
regressions and track improvements over time.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import glob


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark runs."""
    operation: str
    baseline_avg_ms: float
    current_avg_ms: float
    delta_ms: float
    delta_pct: float
    regression: bool  # True if performance degraded


def load_benchmark_results(filename: str) -> List[Dict[str, Any]]:
    """Load benchmark results from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)


def compare_results(baseline_file: str, current_file: str, threshold: float = 5.0) -> List[BenchmarkComparison]:
    """
    Compare two benchmark result files.

    Args:
        baseline_file: Path to baseline benchmark results
        current_file: Path to current benchmark results
        threshold: Regression threshold in percent

    Returns:
        List of benchmark comparisons
    """
    baseline_results = {r['operation']: r for r in load_benchmark_results(baseline_file)}
    current_results = {r['operation']: r for r in load_benchmark_results(current_file)}

    comparisons: List[BenchmarkComparison] = []

    for op_name in baseline_results.keys():
        if op_name in current_results:
            baseline = baseline_results[op_name]
            current = current_results[op_name]

            delta_ms = current['avg_time_ms'] - baseline['avg_time_ms']
            delta_pct = (delta_ms / baseline['avg_time_ms'] * 100) if baseline['avg_time_ms'] > 0 else 0
            regression = delta_pct > threshold

            comparison = BenchmarkComparison(
                operation=op_name,
                baseline_avg_ms=baseline['avg_time_ms'],
                current_avg_ms=current['avg_time_ms'],
                delta_ms=delta_ms,
                delta_pct=delta_pct,
                regression=regression
            )
            comparisons.append(comparison)

    return comparisons


def print_comparison_report(comparisons: List[BenchmarkComparison], threshold: float = 5.0):
    """Print comparison report."""
    print("\n" + "=" * 90)
    print("Benchmark Comparison Report")
    print("=" * 90)

    # Group by regression status
    regressions = [c for c in comparisons if c.regression]
    improvements = [c for c in comparisons if c.delta_pct < -threshold]
    stable = [c for c in comparisons if not c.regression and c.delta_pct >= -threshold]

    # Print header
    print("\n{:<35} {:>15} {:>15} {:>12} {:>10}".format(
        "Operation", "Baseline (ms)", "Current (ms)", "Delta (ms)", "Delta (%)"
    ))
    print("-" * 90)

    # Print all comparisons
    for comp in comparisons:
        status = "⚠️ " if comp.regression else "✓ "
        print("{}{:<33} {:>15.3f} {:>15.3f} {:>12.3f} {:>9.1f}%".format(
            status,
            comp.operation,
            comp.baseline_avg_ms,
            comp.current_avg_ms,
            comp.delta_ms,
            comp.delta_pct
        ))

    # Summary
    print("\n" + "=" * 90)
    print("Summary")
    print("=" * 90)
    print(f"Total operations: {len(comparisons)}")
    print(f"Regressions (>{threshold}% slower): {len(regressions)}")
    print(f"Improvements (>{threshold}% faster): {len(improvements)}")
    print(f"Stable: {len(stable)}")

    if regressions:
        print("\n⚠️  Performance Regressions Detected!")
        print("\nRegressed operations:")
        for comp in sorted(regressions, key=lambda c: c.delta_pct, reverse=True):
            print(f"  - {comp.operation}: {comp.delta_pct:+.1f}% slower")

    if improvements:
        print("\n✓ Performance Improvements:")
        for comp in sorted(improvements, key=lambda c: c.delta_pct):
            print(f"  - {comp.operation}: {abs(comp.delta_pct):.1f}% faster")

    return len(regressions) == 0


def find_latest_benchmarks(directory: str = ".") -> tuple:
    """Find the two most recent benchmark files."""
    pattern = str(Path(directory) / "benchmark_results_*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if len(files) < 2:
        return None, None

    return files[1], files[0]  # baseline (older), current (newer)


def generate_regression_report(directory: str = ".", threshold: float = 5.0) -> bool:
    """
    Generate regression report for latest benchmarks.

    Returns:
        True if no regressions, False if regressions detected
    """
    baseline_file, current_file = find_latest_benchmarks(directory)

    if not baseline_file or not current_file:
        print("Error: Need at least 2 benchmark result files to compare")
        print(f"Found files: {glob.glob('benchmark_results_*.json')}")
        return False

    print(f"\nComparing benchmarks:")
    print(f"  Baseline: {Path(baseline_file).name}")
    print(f"  Current:  {Path(current_file).name}")
    print(f"  Regression threshold: {threshold}%")

    comparisons = compare_results(baseline_file, current_file, threshold)
    return print_comparison_report(comparisons, threshold)


def main():
    """Run benchmark comparison."""
    import argparse

    parser = argparse.ArgumentParser(description="Compare benchmark results")
    parser.add_argument("--baseline", help="Baseline benchmark file")
    parser.add_argument("--current", help="Current benchmark file")
    parser.add_argument("--threshold", type=float, default=5.0,
                       help="Regression threshold in percent (default: 5.0)")
    parser.add_argument("--directory", default=".",
                       help="Directory to search for benchmark files (default: current)")
    parser.add_argument("--auto", action="store_true",
                       help="Automatically compare two latest benchmark files")

    args = parser.parse_args()

    print("\n" + "=" * 90)
    print("ImHex MCP Benchmark Comparison Tool")
    print("=" * 90)

    if args.auto or (not args.baseline and not args.current):
        # Auto mode: find and compare latest files
        passed = generate_regression_report(args.directory, args.threshold)
        return 0 if passed else 1

    elif args.baseline and args.current:
        # Manual mode: compare specific files
        print(f"\nComparing benchmarks:")
        print(f"  Baseline: {args.baseline}")
        print(f"  Current:  {args.current}")
        print(f"  Regression threshold: {args.threshold}%")

        comparisons = compare_results(args.baseline, args.current, args.threshold)
        passed = print_comparison_report(comparisons, args.threshold)
        return 0 if passed else 1

    else:
        print("\nError: Must specify both --baseline and --current, or use --auto")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
