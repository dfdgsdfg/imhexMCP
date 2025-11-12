#!/usr/bin/env python3
"""
Test script for new endpoints (Options H & I):
- data/strings: Extract ASCII/UTF-16 strings
- data/magic: File type detection
- data/disassemble: Code disassembly
"""

import socket
import json
import time
import sys

def send_command(endpoint, data=None):
    """Send a command to ImHex and return the response."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(("localhost", 31337))

        request = {
            "endpoint": endpoint,
            "data": data or {}
        }

        request_json = json.dumps(request) + "\n"
        sock.sendall(request_json.encode('utf-8'))

        response_data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in response_data:
                break

        sock.close()

        response_str = response_data.decode('utf-8').strip()
        return json.loads(response_str)

    except Exception as e:
        return {"status": "error", "data": {"error": str(e)}}

def print_separator(title):
    """Print a section separator."""
    print("\n" + "=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)

def test_strings():
    """Test data/strings endpoint."""
    print_separator("data/strings - String Extraction")

    # Test ASCII strings
    print("\n  Testing ASCII string extraction...")
    response = send_command("data/strings", {
        "provider_id": 0,
        "offset": 0,
        "size": 10240,  # First 10KB
        "min_length": 4,
        "type": "ascii",
        "max_strings": 50
    })

    if response.get("status") == "success":
        data = response.get("data", {})
        strings = data.get("strings", [])
        count = data.get("count", 0)
        truncated = data.get("truncated", False)

        print(f"  ✓ Found {count} strings")
        if truncated:
            print(f"  ⚠ Results truncated to 50 strings")

        if strings:
            print(f"\n  Sample strings (first 10):")
            for i, s in enumerate(strings[:10], 1):
                offset = s.get("offset", 0)
                value = s.get("value", "")
                # Truncate long strings
                display = value if len(value) <= 60 else value[:57] + "..."
                print(f"    {i}. [0x{offset:08X}] \"{display}\"")

        print(f"\n  ✓ data/strings test PASSED")
        return True
    else:
        error = response.get("data", {}).get("error", "Unknown error")
        print(f"  ✗ Error: {error}")
        print(f"  ✗ data/strings test FAILED")
        return False

def test_magic():
    """Test data/magic endpoint."""
    print_separator("data/magic - File Type Detection")

    print("\n  Detecting file type...")
    response = send_command("data/magic", {
        "provider_id": 0,
        "offset": 0,
        "size": 512
    })

    if response.get("status") == "success":
        data = response.get("data", {})
        matches = data.get("matches", [])
        match_count = data.get("match_count", 0)

        print(f"  ✓ Detected {match_count} file type(s)")

        if matches:
            print(f"\n  Detected types:")
            for i, match in enumerate(matches, 1):
                file_type = match.get("type", "Unknown")
                description = match.get("description", "")
                offset = match.get("offset", 0)
                confidence = match.get("confidence", "medium")

                print(f"    {i}. {file_type} - {description}")
                print(f"       Offset: 0x{offset:08X} | Confidence: {confidence}")
        else:
            print(f"  ⚠ No known file type signatures detected")
            print(f"     This may be encrypted, compressed, or a custom format")

        print(f"\n  ✓ data/magic test PASSED")
        return True
    else:
        error = response.get("data", {}).get("error", "Unknown error")
        print(f"  ✗ Error: {error}")
        print(f"  ✗ data/magic test FAILED")
        return False

def test_disassemble():
    """Test data/disassemble endpoint."""
    print_separator("data/disassemble - Code Disassembly")

    # First, try to detect if it's an executable with magic
    magic_response = send_command("data/magic", {"provider_id": 0, "offset": 0, "size": 512})

    # Determine architecture based on file type
    architecture = "x86_64"  # Default
    base_address = 0x1000    # Default

    if magic_response.get("status") == "success":
        matches = magic_response.get("data", {}).get("matches", [])
        for match in matches:
            file_type = match.get("type", "")
            if file_type == "Mach-O":
                architecture = "x86_64"  # or "ARM64" depending on the file
                base_address = 0x100000000  # Typical Mach-O base
                break
            elif file_type == "PE":
                architecture = "x86_64"
                base_address = 0x400000
                break
            elif file_type == "ELF":
                architecture = "x86_64"
                base_address = 0x400000
                break

    print(f"\n  Attempting disassembly with architecture: {architecture}")
    print(f"  Base address: 0x{base_address:X}")

    response = send_command("data/disassemble", {
        "provider_id": 0,
        "offset": 0,
        "size": 64,
        "architecture": architecture,
        "base_address": base_address
    })

    if response.get("status") == "success":
        data = response.get("data", {})

        # Check if there was an architecture error
        if "error" in data:
            error_msg = data.get("error", "")
            available_archs = data.get("available_architectures", [])

            print(f"  ⚠ {error_msg}")
            if available_archs:
                print(f"\n  Available architectures:")
                for arch in available_archs[:10]:  # Show first 10
                    print(f"    - {arch}")

            print(f"\n  ℹ Retrying with first available architecture...")

            if available_archs:
                # Retry with first available architecture
                retry_response = send_command("data/disassemble", {
                    "provider_id": 0,
                    "offset": 0,
                    "size": 64,
                    "architecture": available_archs[0],
                    "base_address": base_address
                })

                if retry_response.get("status") == "success":
                    data = retry_response.get("data", {})
                else:
                    print(f"  ✗ Retry failed")
                    print(f"  ✗ data/disassemble test FAILED")
                    return False

        instructions = data.get("instructions", [])
        count = data.get("count", 0)
        used_arch = data.get("architecture", architecture)

        print(f"  ✓ Disassembled {count} instruction(s) using {used_arch}")

        if instructions:
            print(f"\n  Assembly listing:")
            print(f"  {'-' * 58}")
            for instr in instructions[:20]:  # Show first 20
                address = instr.get("address", "")
                bytes_str = instr.get("bytes", "")
                mnemonic = instr.get("mnemonic", "")
                operands = instr.get("operands", "")

                # Format nicely
                print(f"  {address:16s} {bytes_str:24s} {mnemonic:8s} {operands}")
            print(f"  {'-' * 58}")
        else:
            print(f"  ⚠ No instructions could be disassembled")
            print(f"     This may not be executable code")

        print(f"\n  ✓ data/disassemble test PASSED")
        return True
    else:
        error = response.get("data", {}).get("error", "Unknown error")
        print(f"  ✗ Error: {error}")
        print(f"  ✗ data/disassemble test FAILED")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  NEW ENDPOINTS TEST SUITE (Options H & I)")
    print("=" * 60)
    print(f"  Testing connection to ImHex on localhost:31337...")

    # Test connection
    try:
        response = send_command("file/list")
        if response.get("status") != "success":
            print(f"\n  ✗ Failed to connect to ImHex")
            print(f"  ℹ Make sure ImHex is running with Network Interface enabled")
            sys.exit(1)

        print(f"  ✓ Connected to ImHex")

        # Try to open test file programmatically
        print(f"  ℹ Opening test file /tmp/test_binary.bin...")
        open_response = send_command("file/open", {"path": "/tmp/test_binary.bin"})

        if open_response.get("status") == "success":
            print(f"  ✓ Test file opened successfully")
            time.sleep(0.5)  # Give it a moment to register
        else:
            print(f"  ⚠ Could not open test file, will try with any open files")

        # Check again for open files
        response = send_command("file/list")
        data = response.get("data", {})
        providers = data.get("providers", [])

        if not providers:
            print(f"\n  ⚠ No files open in ImHex")
            print(f"  ℹ Please open a binary file (e.g., /bin/ls) manually in ImHex")
            sys.exit(1)

        print(f"  ✓ {len(providers)} file(s) open")

        for p in providers:
            print(f"    - {p.get('name', 'unknown')} ({p.get('size', 0):,} bytes)")

    except Exception as e:
        print(f"\n  ✗ Connection error: {e}")
        print(f"  ℹ Make sure ImHex is running")
        sys.exit(1)

    # Run tests
    results = {
        "strings": test_strings(),
        "magic": test_magic(),
        "disassemble": test_disassemble()
    }

    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name:20s} {status}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print(f"\n  🎉 All new endpoint tests PASSED!")
        sys.exit(0)
    else:
        print(f"\n  ⚠ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
