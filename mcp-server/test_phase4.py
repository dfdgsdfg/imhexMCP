#!/usr/bin/env python3
"""
Test Phase 4 endpoints: batch/hash, batch/search, data/entropy, data/statistics
"""
import sys
import time
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

print("="*60)
print("PHASE 4 ENDPOINT TESTS")
print("="*60)

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=15.0)
client = ImHexClient(config)

try:
    print("\n1. Connecting to ImHex...")
    client.connect()
    print("   ✓ Connected")

    # Open test files
    test_files = ["/tmp/ref.bin", "/tmp/similar.bin", "/tmp/different.bin"]

    print("\n2. Opening test files...")
    for f in test_files:
        r = client.send_command("file/open", {"path": f})
        if r.get("status") == "success":
            print(f"   ✓ Requested: {f}")
        else:
            print(f"   ⚠ Issue with {f}: {r}")

    print("\n   Waiting 2 seconds for files to open...")
    time.sleep(2)

    # Get provider list
    print("\n3. Getting provider list...")
    r = client.send_command("list/providers", {})
    if r.get("status") == "success":
        providers = r.get("data", {}).get("providers", [])
        print(f"   ✓ Found {len(providers)} providers")
        for p in providers:
            print(f"     - Provider {p['id']}: {p.get('name', 'unknown')} ({p.get('size', 0)} bytes)")
    else:
        print(f"   ✗ Failed: {r}")
        sys.exit(1)

    if len(providers) < 3:
        print(f"\n   ⚠ Need at least 3 providers for testing, found {len(providers)}")
        print("   Please open some files in ImHex GUI first")
        sys.exit(1)

    # Test 1: batch/hash
    print("\n" + "="*60)
    print("TEST 1: batch/hash")
    print("="*60)

    print("\n  Testing MD5 hashes for all providers...")
    r = client.send_command("batch/hash", {
        "provider_ids": "all",
        "algorithm": "md5"
    })

    if r.get("status") == "success":
        data = r.get("data", {})
        hashes = data.get("hashes", [])
        print(f"  ✓ Got {len(hashes)} hash results")

        for h in hashes:
            provider_id = h.get("provider_id")
            hash_value = h.get("hash", "")[:16] + "..."  # Show first 16 chars
            file_name = h.get("file", "unknown")
            print(f"    Provider {provider_id} ({file_name}): {hash_value}")

        print(f"\n  ✓ batch/hash test PASSED")
    else:
        error = r.get("data", {}).get("error", "Unknown")
        print(f"  ✗ batch/hash FAILED: {error}")

    # Test 2: batch/search
    print("\n" + "="*60)
    print("TEST 2: batch/search")
    print("="*60)

    print("\n  Searching for pattern '48656C6C6F' (Hello) in all providers...")
    r = client.send_command("batch/search", {
        "provider_ids": "all",
        "pattern": "48656C6C6F",
        "max_matches": 100
    })

    if r.get("status") == "success":
        data = r.get("data", {})
        results = data.get("results", [])
        print(f"  ✓ Searched {len(results)} providers")

        total_matches = 0
        for result in results:
            provider_id = result.get("provider_id")
            file_name = result.get("file", "unknown")
            matches = result.get("matches", [])
            match_count = len(matches)
            total_matches += match_count

            if match_count > 0:
                print(f"    Provider {provider_id} ({file_name}): {match_count} matches")
                for match in matches[:3]:  # Show first 3
                    print(f"      - Offset: 0x{match:X}")
            else:
                print(f"    Provider {provider_id} ({file_name}): 0 matches")

        print(f"\n  ✓ batch/search test PASSED (total {total_matches} matches)")
    else:
        error = r.get("data", {}).get("error", "Unknown")
        print(f"  ✗ batch/search FAILED: {error}")

    # Test 3: data/entropy
    print("\n" + "="*60)
    print("TEST 3: data/entropy")
    print("="*60)

    # Use first provider
    provider_id = providers[0]['id']
    print(f"\n  Calculating entropy for provider {provider_id}...")
    r = client.send_command("data/entropy", {
        "provider_id": provider_id,
        "offset": 0,
        "size": 1024
    })

    if r.get("status") == "success":
        data = r.get("data", {})
        entropy = data.get("entropy", 0)
        percentage = data.get("percentage", 0)
        interpretation = data.get("interpretation", "")

        print(f"  ✓ Entropy calculation completed")
        print(f"    - Entropy: {entropy:.4f} bits/byte")
        print(f"    - Percentage: {percentage:.2f}%")
        print(f"    - Interpretation: {interpretation}")
        print(f"\n  ✓ data/entropy test PASSED")
    else:
        error = r.get("data", {}).get("error", "Unknown")
        print(f"  ✗ data/entropy FAILED: {error}")

    # Test 4: data/statistics
    print("\n" + "="*60)
    print("TEST 4: data/statistics")
    print("="*60)

    print(f"\n  Calculating statistics for provider {provider_id}...")
    r = client.send_command("data/statistics", {
        "provider_id": provider_id,
        "offset": 0,
        "size": 1024,
        "include_distribution": False
    })

    if r.get("status") == "success":
        data = r.get("data", {})
        unique_bytes = data.get("unique_bytes", 0)
        most_common = data.get("most_common_byte", 0)
        most_common_count = data.get("most_common_count", 0)
        null_pct = data.get("null_percentage", 0)
        printable_pct = data.get("printable_percentage", 0)

        print(f"  ✓ Statistics calculation completed")
        print(f"    - Unique bytes: {unique_bytes}/256")
        print(f"    - Most common byte: 0x{most_common:02X} ({most_common_count} occurrences)")
        print(f"    - Null bytes: {null_pct:.2f}%")
        print(f"    - Printable chars: {printable_pct:.2f}%")
        print(f"\n  ✓ data/statistics test PASSED")
    else:
        error = r.get("data", {}).get("error", "Unknown")
        print(f"  ✗ data/statistics FAILED: {error}")

    # Summary
    print("\n" + "="*60)
    print("✅ ALL PHASE 4 TESTS COMPLETED!")
    print("="*60)
    print("\nSuccessfully tested:")
    print("  1. batch/hash - Multi-file hashing")
    print("  2. batch/search - Multi-file pattern search")
    print("  3. data/entropy - Shannon entropy calculation")
    print("  4. data/statistics - Byte frequency analysis")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
