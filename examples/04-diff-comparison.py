#!/usr/bin/env python3
"""
Binary Diff Comparison with ImHex MCP

This example demonstrates binary diffing for patch analysis:
- Comparing two binary files
- Identifying modified regions
- Analyzing patch size and distribution
- Detecting security-relevant changes

Usage:
    python3 04-diff-comparison.py <file1> <file2> [--output FILE]

Example:
    python3 04-diff-comparison.py original.bin patched.bin --output diff_report.json
"""

import socket
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime


def send_request(endpoint, data=None):
    """Send request to ImHex MCP and return response."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(("localhost", 31337))

        request = json.dumps({
            "endpoint": endpoint,
            "data": data or {}
        }) + "\n"

        sock.sendall(request.encode())

        response = b""
        while b"\n" not in response:
            response += sock.recv(4096)

        sock.close()
        return json.loads(response.decode().strip())

    except ConnectionRefusedError:
        print("Error: Cannot connect to ImHex. Is it running?")
        sys.exit(1)
    except socket.timeout:
        print("Error: Request timed out")
        sys.exit(1)


def compare_binaries(file1_path, file2_path, output_file=None):
    """Compare two binary files and analyze differences."""
    print(f"\n{'='*70}")
    print(f"Binary Diff Analysis")
    print(f"  Original: {file1_path}")
    print(f"  Modified: {file2_path}")
    print(f"{'='*70}\n")

    report = {
        "timestamp": datetime.now().isoformat(),
        "file1": file1_path,
        "file2": file2_path,
        "differences": [],
        "statistics": {}
    }

    # 1. Open both files
    print("[1/5] Opening files...")

    result1 = send_request("file/open", {"path": file1_path})
    if result1["status"] != "success":
        print(f"  Error opening {file1_path}: {result1['data']['error']}")
        return
    provider1 = result1["data"]["provider_id"]
    size1 = result1["data"]["size"]
    print(f"  ✓ File 1 opened: {size1} bytes (Provider ID: {provider1})")

    result2 = send_request("file/open", {"path": file2_path})
    if result2["status"] != "success":
        print(f"  Error opening {file2_path}: {result2['data']['error']}")
        return
    provider2 = result2["data"]["provider_id"]
    size2 = result2["data"]["size"]
    print(f"  ✓ File 2 opened: {size2} bytes (Provider ID: {provider2})")

    report["statistics"]["size1"] = size1
    report["statistics"]["size2"] = size2
    report["statistics"]["size_diff"] = abs(size2 - size1)

    # 2. Compute hashes
    print("\n[2/5] Computing file hashes...")
    for provider_id, file_label in [(provider1, "file1"), (provider2, "file2")]:
        result = send_request("data/hash", {
            "provider_id": provider_id,
            "offset": 0,
            "size": -1,
            "algorithm": "sha256"
        })
        if result["status"] == "success":
            hash_value = result["data"]["hash"]
            print(f"  {file_label}: {hash_value}")
            report[file_label + "_hash"] = hash_value

    # 3. Perform binary diff
    print("\n[3/5] Computing binary diff...")

    # Use batch/diff endpoint
    result = send_request("batch/diff", {
        "provider1_id": provider1,
        "provider2_id": provider2
    })

    if result["status"] == "success":
        differences = result["data"].get("differences", [])
        print(f"  ✓ Found {len(differences)} difference region(s)")

        report["differences"] = differences
        total_bytes_changed = sum(d["size"] for d in differences)
        report["statistics"]["bytes_changed"] = total_bytes_changed
        report["statistics"]["regions_changed"] = len(differences)

        if size1 > 0:
            percent_changed = (total_bytes_changed / size1) * 100
            report["statistics"]["percent_changed"] = round(percent_changed, 2)
            print(f"  ✓ {total_bytes_changed:,} bytes changed ({percent_changed:.2f}%)")
    else:
        print(f"  Error: {result['data'].get('error', 'Unknown error')}")

    # 4. Analyze change patterns
    print("\n[4/5] Analyzing change patterns...")

    if differences:
        # Group nearby changes
        change_clusters = []
        current_cluster = None

        for diff in sorted(differences, key=lambda x: x["offset"]):
            if current_cluster is None:
                current_cluster = {"start": diff["offset"], "end": diff["offset"] + diff["size"], "count": 1}
            elif diff["offset"] - current_cluster["end"] < 256:  # Cluster if within 256 bytes
                current_cluster["end"] = diff["offset"] + diff["size"]
                current_cluster["count"] += 1
            else:
                change_clusters.append(current_cluster)
                current_cluster = {"start": diff["offset"], "end": diff["offset"] + diff["size"], "count": 1}

        if current_cluster:
            change_clusters.append(current_cluster)

        report["statistics"]["change_clusters"] = len(change_clusters)
        print(f"  ✓ Changes grouped into {len(change_clusters)} cluster(s)")

        # Detect large changes
        large_changes = [d for d in differences if d["size"] > 1024]
        report["statistics"]["large_changes"] = len(large_changes)
        print(f"  ✓ Found {len(large_changes)} large change(s) (>1KB)")

    # 5. Check for security-relevant changes
    print("\n[5/5] Detecting security-relevant changes...")

    security_findings = []

    # Check if changes affect executable regions (heuristic: first 10KB often contains code)
    code_region_changes = [d for d in differences if d["offset"] < 10240]
    if code_region_changes:
        security_findings.append({
            "type": "Code Region Modified",
            "severity": "HIGH",
            "count": len(code_region_changes),
            "description": "Changes detected in potential code region (first 10KB)"
        })

    # Check for significant size changes
    if report["statistics"]["size_diff"] > 0:
        security_findings.append({
            "type": "Binary Size Changed",
            "severity": "MEDIUM",
            "bytes": report["statistics"]["size_diff"],
            "description": f"File size changed by {report['statistics']['size_diff']} bytes"
        })

    # Check for concentrated changes (potential backdoor)
    if change_clusters and len(change_clusters) < 5 and total_bytes_changed > 1024:
        security_findings.append({
            "type": "Concentrated Changes",
            "severity": "MEDIUM",
            "description": f"Large changes ({total_bytes_changed} bytes) in few locations ({len(change_clusters)})"
        })

    report["security_findings"] = security_findings
    print(f"  ✓ Found {len(security_findings)} security-relevant finding(s)")

    # Generate report
    print("\n" + "="*70)
    print("DIFF ANALYSIS REPORT")
    print("="*70 + "\n")

    print(f"Files Compared:")
    print(f"  Original: {Path(file1_path).name} ({size1:,} bytes)")
    print(f"  Modified: {Path(file2_path).name} ({size2:,} bytes)")

    if "percent_changed" in report["statistics"]:
        print(f"\nChanges:")
        print(f"  Regions: {report['statistics']['regions_changed']}")
        print(f"  Bytes:   {report['statistics']['bytes_changed']:,}")
        print(f"  Percent: {report['statistics']['percent_changed']}%")
        print(f"  Clusters: {report['statistics'].get('change_clusters', 'N/A')}")

    if differences and len(differences) <= 20:
        print(f"\nDifference Details:")
        for i, diff in enumerate(differences[:20], 1):
            print(f"  [{i}] Offset: 0x{diff['offset']:08x}, Size: {diff['size']} bytes")

    if security_findings:
        print(f"\nSecurity Findings:")
        for finding in security_findings:
            severity_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(finding["severity"], "⚪")
            print(f"  {severity_icon} [{finding['severity']}] {finding['type']}")
            print(f"      {finding['description']}")

    # Save report
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_file}")

    # Close files
    send_request("file/close", {"provider_id": provider1})
    send_request("file/close", {"provider_id": provider2})

    print("\n" + "="*70)
    print("Diff analysis complete!")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Binary diff comparison with ImHex MCP")
    parser.add_argument("file1", help="Original binary file")
    parser.add_argument("file2", help="Modified binary file")
    parser.add_argument("--output", help="Save report to JSON file")

    args = parser.parse_args()

    if not Path(args.file1).exists():
        print(f"Error: {args.file1} not found")
        sys.exit(1)

    if not Path(args.file2).exists():
        print(f"Error: {args.file2} not found")
        sys.exit(1)

    compare_binaries(args.file1, args.file2, args.output)


if __name__ == "__main__":
    main()
