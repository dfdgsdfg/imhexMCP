#!/usr/bin/env python3
"""
Automated Analysis Pipeline with ImHex MCP

This example demonstrates a complete end-to-end automated analysis workflow:
- Multi-file batch processing
- Comprehensive analysis combining all previous examples
- Parallel execution for performance
- Structured JSON reporting
- Integration with external tools

Usage:
    python3 05-automated-pipeline.py <input_dir> [--output FILE] [--workers N]

Example:
    python3 05-automated-pipeline.py ./samples --output full_report.json --workers 4
"""

import socket
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def send_request(endpoint, data=None, timeout=30):
    """Send request to ImHex MCP and return response."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
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
        print(f"Error: Request to {endpoint} timed out")
        return {"status": "error", "data": {"error": "Timeout"}}


def analyze_single_file(file_path):
    """Perform comprehensive analysis on a single file."""
    print(f"  Analyzing: {Path(file_path).name}")

    analysis = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "basic_info": {},
        "strings": [],
        "file_type": None,
        "hashes": {},
        "disassembly_sample": [],
        "suspicious_indicators": [],
        "errors": []
    }

    # 1. Open file
    result = send_request("file/open", {"path": file_path})
    if result["status"] != "success":
        analysis["errors"].append(f"Failed to open: {result['data'].get('error')}")
        return analysis

    provider_id = result["data"]["provider_id"]
    file_size = result["data"]["size"]

    analysis["basic_info"]["size"] = file_size
    analysis["basic_info"]["provider_id"] = provider_id

    # 2. Compute hashes
    for algorithm in ["md5", "sha1", "sha256"]:
        result = send_request("data/hash", {
            "provider_id": provider_id,
            "offset": 0,
            "size": -1,
            "algorithm": algorithm
        })
        if result["status"] == "success":
            analysis["hashes"][algorithm] = result["data"]["hash"]

    # 3. Identify file type
    result = send_request("data/magic", {"provider_id": provider_id})
    if result["status"] == "success" and result["data"].get("matches"):
        matches = result["data"]["matches"]
        analysis["file_type"] = {
            "type": matches[0]["type"],
            "description": matches[0]["description"],
            "confidence": matches[0].get("confidence", 100)
        }

    # 4. Extract strings
    result = send_request("data/strings", {
        "provider_id": provider_id,
        "offset": 0,
        "size": min(100000, file_size),
        "min_length": 4,
        "type": "ascii"
    })

    if result["status"] == "success":
        strings = result["data"]["strings"]
        analysis["strings"] = [
            {"offset": s["offset"], "value": s["value"]}
            for s in strings[:20]  # Limit to first 20
        ]

        # Look for suspicious patterns
        suspicious_keywords = ["password", "admin", "root", "cmd.exe", "powershell",
                               "exec", "eval", "system", "shell", "backdoor"]
        for s in strings:
            if any(keyword in s["value"].lower() for keyword in suspicious_keywords):
                analysis["suspicious_indicators"].append({
                    "type": "Suspicious string",
                    "offset": s["offset"],
                    "value": s["value"][:100]
                })

    # 5. Disassemble sample (if binary/executable)
    if analysis["file_type"] and "executable" in analysis["file_type"]["description"].lower():
        result = send_request("data/disassemble", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 256,
            "architecture": "x86_64"
        })

        if result["status"] == "success":
            instructions = result["data"].get("instructions", [])
            analysis["disassembly_sample"] = [
                {
                    "address": instr["address"],
                    "mnemonic": instr["mnemonic"],
                    "operands": instr.get("operands", "")
                }
                for instr in instructions[:10]  # First 10 instructions
            ]

    # 6. Close file
    send_request("file/close", {"provider_id": provider_id})

    return analysis


def analyze_directory(directory, max_workers=4):
    """Analyze all files in directory using parallel processing."""
    files = []

    # Gather all files (not directories)
    for path in Path(directory).rglob("*"):
        if path.is_file():
            files.append(str(path))

    print(f"Found {len(files)} files to analyze")

    results = []

    # Use ThreadPoolExecutor for parallel analysis
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(analyze_single_file, file): file
            for file in files
        }

        # Collect results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                results.append({
                    "file": file_path,
                    "errors": [str(e)]
                })

    return results


def generate_summary(results):
    """Generate summary statistics from analysis results."""
    summary = {
        "total_files": len(results),
        "total_size": 0,
        "file_types": {},
        "total_strings": 0,
        "total_suspicious": 0,
        "failed": 0
    }

    for result in results:
        # Count failures
        if result.get("errors"):
            summary["failed"] += 1
            continue

        # Sum file sizes
        summary["total_size"] += result["basic_info"].get("size", 0)

        # Count file types
        if result.get("file_type"):
            file_type = result["file_type"]["type"]
            summary["file_types"][file_type] = summary["file_types"].get(file_type, 0) + 1

        # Count strings and suspicious indicators
        summary["total_strings"] += len(result.get("strings", []))
        summary["total_suspicious"] += len(result.get("suspicious_indicators", []))

    return summary


def run_pipeline(input_dir, output_file=None, max_workers=4):
    """Execute the complete analysis pipeline."""
    print(f"\n{'='*70}")
    print(f"Automated Analysis Pipeline")
    print(f"  Input:   {input_dir}")
    print(f"  Workers: {max_workers}")
    print(f"{'='*70}\n")

    start_time = time.time()

    # Test connection
    print("[1/4] Testing ImHex connection...")
    result = send_request("capabilities")
    if result["status"] != "success":
        print("  Error: Cannot connect to ImHex MCP")
        return

    endpoints = result["data"].get("endpoints", [])
    print(f"  ✓ Connected ({len(endpoints)} endpoints available)")

    # Analyze directory
    print(f"\n[2/4] Analyzing files in {input_dir}...")
    results = analyze_directory(input_dir, max_workers)

    # Generate summary
    print(f"\n[3/4] Generating summary...")
    summary = generate_summary(results)

    # Create report
    report = {
        "pipeline_version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "input_directory": input_dir,
        "duration_seconds": round(time.time() - start_time, 2),
        "summary": summary,
        "results": results
    }

    # Save report
    print(f"\n[4/4] Saving report...")
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"  ✓ Report saved to: {output_file}")

    # Print summary
    print(f"\n{'='*70}")
    print(f"ANALYSIS SUMMARY")
    print(f"{'='*70}\n")
    print(f"Files Analyzed:       {summary['total_files']}")
    print(f"Files Failed:         {summary['failed']}")
    print(f"Total Size:           {summary['total_size']:,} bytes")
    print(f"Total Strings:        {summary['total_strings']:,}")
    print(f"Suspicious Findings:  {summary['total_suspicious']}")
    print(f"Duration:             {report['duration_seconds']:.2f}s")

    if summary["file_types"]:
        print(f"\nFile Types:")
        for file_type, count in sorted(summary["file_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {file_type:30s}: {count:3d}")

    # Highlight top suspicious files
    suspicious_files = [
        (r["file"], len(r["suspicious_indicators"]))
        for r in results
        if r.get("suspicious_indicators")
    ]

    if suspicious_files:
        print(f"\nMost Suspicious Files:")
        for file_path, count in sorted(suspicious_files, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {Path(file_path).name:40s}: {count:3d} indicators")

    print(f"\n{'='*70}")
    print(f"Pipeline complete!")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Automated analysis pipeline with ImHex MCP")
    parser.add_argument("input_dir", help="Directory to analyze")
    parser.add_argument("--output", help="Save report to JSON file")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers (default: 4)")

    args = parser.parse_args()

    if not Path(args.input_dir).is_dir():
        print(f"Error: {args.input_dir} is not a directory")
        sys.exit(1)

    run_pipeline(args.input_dir, args.output, args.workers)


if __name__ == "__main__":
    main()
