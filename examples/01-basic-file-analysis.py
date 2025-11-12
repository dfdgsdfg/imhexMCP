#!/usr/bin/env python3
"""
Basic File Analysis with ImHex MCP

This example demonstrates fundamental operations:
- Connecting to ImHex network interface
- Opening a binary file
- Reading file data
- Extracting strings
- Computing hashes
- Identifying file type

Usage:
    python3 01-basic-file-analysis.py <file_path>

Example:
    python3 01-basic-file-analysis.py /bin/ls
"""

import socket
import json
import sys
from pathlib import Path


def send_request(endpoint, data=None):
    """Send request to ImHex MCP and return response."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
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
        print("Error: Cannot connect to ImHex. Is it running with network interface enabled?")
        sys.exit(1)
    except socket.timeout:
        print("Error: Request timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def analyze_file(file_path):
    """Perform basic analysis on a binary file."""
    print(f"\n{'='*70}")
    print(f"Basic File Analysis: {file_path}")
    print(f"{'='*70}\n")

    # 1. Check file exists
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        return

    # 2. Open file
    print("[1/5] Opening file...")
    result = send_request("file/open", {"path": file_path})

    if result["status"] != "success":
        print(f"  Error: {result['data']['error']}")
        return

    provider_id = result["data"]["provider_id"]
    file_size = result["data"]["size"]
    print(f"  ✓ File opened (Provider ID: {provider_id}, Size: {file_size} bytes)")

    # 3. Read first 256 bytes
    print("\n[2/5] Reading file header...")
    result = send_request("data/read", {
        "provider_id": provider_id,
        "offset": 0,
        "size": min(256, file_size)
    })

    if result["status"] == "success":
        hex_data = result["data"]["data"]
        print(f"  ✓ Read {len(hex_data)//2} bytes")
        print(f"  First 64 bytes: {hex_data[:128]}...")

    # 4. Identify file type
    print("\n[3/5] Identifying file type...")
    result = send_request("data/magic", {"provider_id": provider_id})

    if result["status"] == "success" and result["data"]["matches"]:
        matches = result["data"]["matches"]
        print(f"  ✓ Found {len(matches)} signature match(es):")
        for i, match in enumerate(matches[:3], 1):
            print(f"    [{i}] {match['type']}: {match['description']}")
    else:
        print("  No file type signatures matched")

    # 5. Extract strings
    print("\n[4/5] Extracting strings...")
    result = send_request("data/strings", {
        "provider_id": provider_id,
        "offset": 0,
        "size": min(100000, file_size),  # First 100KB
        "min_length": 4,
        "type": "ascii"
    })

    if result["status"] == "success":
        strings = result["data"]["strings"]
        print(f"  ✓ Found {len(strings)} strings")
        if strings:
            print("  Sample strings:")
            for s in strings[:5]:
                value = s["value"][:50] + "..." if len(s["value"]) > 50 else s["value"]
                print(f"    0x{s['offset']:08x}: {value}")

    # 6. Compute hashes
    print("\n[5/5] Computing hashes...")
    for algorithm in ["md5", "sha256"]:
        result = send_request("data/hash", {
            "provider_id": provider_id,
            "offset": 0,
            "size": -1,  # Entire file
            "algorithm": algorithm
        })

        if result["status"] == "success":
            hash_value = result["data"]["hash"]
            print(f"  {algorithm.upper():6s}: {hash_value}")

    # 7. Close file
    send_request("file/close", {"provider_id": provider_id})
    print(f"\n{'='*70}")
    print("Analysis complete!")
    print(f"{'='*70}\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 01-basic-file-analysis.py <file_path>")
        print("\nExample:")
        print("  python3 01-basic-file-analysis.py /bin/ls")
        sys.exit(1)

    file_path = sys.argv[1]
    analyze_file(file_path)


if __name__ == "__main__":
    main()
