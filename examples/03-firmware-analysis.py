#!/usr/bin/env python3
"""
Firmware Analysis with ImHex MCP

This example demonstrates IoT/embedded firmware analysis:
- Identifying firmware format and architecture
- Extracting embedded strings and URLs
- Finding cryptographic constants
- Analyzing memory regions
- Detecting common vulnerabilities

Usage:
    python3 03-firmware-analysis.py <firmware_file> [--output FILE]

Example:
    python3 03-firmware-analysis.py router_firmware.bin --output firmware_report.json
"""

import socket
import json
import sys
import argparse
import re
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


def analyze_firmware(firmware_path, output_file=None):
    """Perform comprehensive firmware analysis."""
    print(f"\n{'='*70}")
    print(f"Firmware Analysis: {firmware_path}")
    print(f"{'='*70}\n")

    report = {
        "timestamp": datetime.now().isoformat(),
        "firmware": firmware_path,
        "file_info": {},
        "architecture": None,
        "strings": {
            "urls": [],
            "ips": [],
            "emails": [],
            "interesting": []
        },
        "crypto_constants": [],
        "vulnerabilities": []
    }

    # 1. Open firmware file
    print("[1/7] Opening firmware file...")
    result = send_request("file/open", {"path": firmware_path})

    if result["status"] != "success":
        print(f"  Error: {result['data']['error']}")
        return

    provider_id = result["data"]["provider_id"]
    file_size = result["data"]["size"]
    print(f"  ✓ File opened (Provider ID: {provider_id}, Size: {file_size} bytes)")

    report["file_info"]["size"] = file_size
    report["file_info"]["provider_id"] = provider_id

    # 2. Identify firmware type via magic bytes
    print("\n[2/7] Identifying firmware type...")
    result = send_request("data/magic", {"provider_id": provider_id})

    if result["status"] == "success" and result["data"]["matches"]:
        matches = result["data"]["matches"]
        print(f"  ✓ Found {len(matches)} signature match(es):")
        for i, match in enumerate(matches[:3], 1):
            print(f"    [{i}] {match['type']}: {match['description']}")
            if i == 1:
                report["file_info"]["type"] = match["type"]
                report["file_info"]["description"] = match["description"]
    else:
        print("  No firmware signatures matched - may be custom format")

    # 3. Extract ALL strings
    print("\n[3/7] Extracting strings...")
    result = send_request("data/strings", {
        "provider_id": provider_id,
        "offset": 0,
        "size": file_size,
        "min_length": 4,
        "type": "ascii"
    })

    all_strings = []
    if result["status"] == "success":
        all_strings = result["data"]["strings"]
        print(f"  ✓ Found {len(all_strings)} strings")

        # Extract URLs
        url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        for s in all_strings:
            urls = url_pattern.findall(s["value"])
            report["strings"]["urls"].extend(urls)

        # Extract IP addresses
        ip_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
        for s in all_strings:
            ips = ip_pattern.findall(s["value"])
            # Filter out obvious non-IPs like version numbers
            valid_ips = [ip for ip in ips if all(0 <= int(octet) <= 255 for octet in ip.split('.'))]
            report["strings"]["ips"].extend(valid_ips)

        # Extract email addresses
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        for s in all_strings:
            emails = email_pattern.findall(s["value"])
            report["strings"]["emails"].extend(emails)

        # Find interesting keywords
        interesting_keywords = ["password", "passwd", "admin", "root", "key", "secret",
                               "token", "api", "debug", "telnet", "ssh", "backdoor"]
        for s in all_strings:
            if any(keyword in s["value"].lower() for keyword in interesting_keywords):
                report["strings"]["interesting"].append({
                    "offset": s["offset"],
                    "value": s["value"]
                })

        # Deduplicate
        report["strings"]["urls"] = list(set(report["strings"]["urls"]))
        report["strings"]["ips"] = list(set(report["strings"]["ips"]))
        report["strings"]["emails"] = list(set(report["strings"]["emails"]))

        print(f"  ✓ URLs found: {len(report['strings']['urls'])}")
        print(f"  ✓ IP addresses found: {len(report['strings']['ips'])}")
        print(f"  ✓ Email addresses found: {len(report['strings']['emails'])}")
        print(f"  ✓ Interesting strings: {len(report['strings']['interesting'])}")

    # 4. Detect architecture via disassembly
    print("\n[4/7] Detecting architecture...")
    architectures = ["arm", "aarch64", "mips", "x86", "x86_64", "powerpc"]
    best_arch = None
    max_valid_instructions = 0

    for arch in architectures:
        result = send_request("data/disassemble", {
            "provider_id": provider_id,
            "offset": 0,
            "size": 512,
            "architecture": arch
        })

        if result["status"] == "success":
            instructions = result["data"].get("instructions", [])
            if len(instructions) > max_valid_instructions:
                max_valid_instructions = len(instructions)
                best_arch = arch

    if best_arch:
        print(f"  ✓ Likely architecture: {best_arch} ({max_valid_instructions} valid instructions)")
        report["architecture"] = best_arch
    else:
        print("  Could not reliably detect architecture")

    # 5. Search for cryptographic constants
    print("\n[5/7] Searching for cryptographic constants...")

    # Known crypto constants (first few bytes)
    crypto_patterns = {
        "AES S-Box": "637c777b",
        "MD5": "67452301",
        "SHA-256": "6a09e667",
        "RSA (e=65537)": "00010001"
    }

    result = send_request("data/read", {
        "provider_id": provider_id,
        "offset": 0,
        "size": min(100000, file_size)
    })

    if result["status"] == "success":
        hex_data = result["data"]["data"]
        for crypto_name, pattern in crypto_patterns.items():
            if pattern in hex_data.lower():
                offset = hex_data.lower().index(pattern) // 2
                print(f"  ✓ Found {crypto_name} constant at offset 0x{offset:x}")
                report["crypto_constants"].append({
                    "type": crypto_name,
                    "offset": offset
                })

    # 6. Compute hashes
    print("\n[6/7] Computing firmware hashes...")
    for algorithm in ["md5", "sha1", "sha256"]:
        result = send_request("data/hash", {
            "provider_id": provider_id,
            "offset": 0,
            "size": -1,
            "algorithm": algorithm
        })

        if result["status"] == "success":
            hash_value = result["data"]["hash"]
            print(f"  {algorithm.upper():8s}: {hash_value}")
            report["file_info"][algorithm] = hash_value

    # 7. Vulnerability assessment
    print("\n[7/7] Assessing potential vulnerabilities...")

    # Check for hardcoded credentials
    credential_keywords = ["password=", "passwd=", "pwd=", "secret=", "token="]
    for s in all_strings:
        if any(keyword in s["value"].lower() for keyword in credential_keywords):
            report["vulnerabilities"].append({
                "type": "Hardcoded Credentials",
                "severity": "HIGH",
                "offset": s["offset"],
                "evidence": s["value"][:100]
            })

    # Check for insecure protocols
    insecure_protocols = ["telnet", "ftp://", "http://"]
    for protocol in insecure_protocols:
        if any(protocol in s["value"].lower() for s in all_strings):
            report["vulnerabilities"].append({
                "type": "Insecure Protocol",
                "severity": "MEDIUM",
                "protocol": protocol
            })

    # Check for debug strings
    debug_strings = ["debug", "test", "backdoor", "development"]
    debug_count = sum(1 for s in all_strings if any(d in s["value"].lower() for d in debug_strings))
    if debug_count > 5:
        report["vulnerabilities"].append({
            "type": "Debug/Development Code",
            "severity": "LOW",
            "count": debug_count
        })

    print(f"  ✓ Found {len(report['vulnerabilities'])} potential vulnerabilities")

    # 8. Generate report
    print("\n" + "="*70)
    print("FIRMWARE ANALYSIS REPORT")
    print("="*70 + "\n")

    print(f"File: {Path(firmware_path).name}")
    print(f"Size: {file_size:,} bytes")
    if "type" in report["file_info"]:
        print(f"Type: {report['file_info']['type']} - {report['file_info']['description']}")
    if report["architecture"]:
        print(f"Architecture: {report['architecture']}")

    print(f"\n--- Network Indicators ---")
    if report["strings"]["urls"]:
        print(f"URLs ({len(report['strings']['urls'])}):")
        for url in report["strings"]["urls"][:5]:
            print(f"  - {url}")
    if report["strings"]["ips"]:
        print(f"IP Addresses ({len(report['strings']['ips'])}):")
        for ip in report["strings"]["ips"][:5]:
            print(f"  - {ip}")

    if report["crypto_constants"]:
        print(f"\n--- Cryptographic Constants ---")
        for const in report["crypto_constants"]:
            print(f"  - {const['type']} at offset 0x{const['offset']:x}")

    if report["strings"]["interesting"]:
        print(f"\n--- Interesting Strings ---")
        for s in report["strings"]["interesting"][:10]:
            print(f"  0x{s['offset']:08x}: {s['value'][:60]}")

    if report["vulnerabilities"]:
        print(f"\n--- Potential Vulnerabilities ({len(report['vulnerabilities'])}) ---")
        for vuln in report["vulnerabilities"]:
            severity_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(vuln["severity"], "⚪")
            print(f"  {severity_icon} [{vuln['severity']}] {vuln['type']}")

    # Save report
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_file}")

    # Close file
    send_request("file/close", {"provider_id": provider_id})

    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Firmware analysis with ImHex MCP")
    parser.add_argument("firmware", help="Firmware file to analyze")
    parser.add_argument("--output", help="Save report to JSON file")

    args = parser.parse_args()

    if not Path(args.firmware).exists():
        print(f"Error: {args.firmware} not found")
        sys.exit(1)

    analyze_firmware(args.firmware, args.output)


if __name__ == "__main__":
    main()
