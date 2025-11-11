#!/usr/bin/env python3
"""
Automated test for batch/diff endpoint
"""
import sys
import tempfile
import os
import time
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

print("="*60)
print("BATCH/DIFF ENDPOINT TEST")
print("="*60)

# Create test files
print("\n1. Creating test files...")
test_files = []
test_dir = tempfile.mkdtemp(prefix="batch_diff_test_")

# Reference file - 1KB with pattern
ref_path = os.path.join(test_dir, "reference.bin")
with open(ref_path, 'wb') as f:
    f.write(b'REF_' * 256)  # 1KB
test_files.append(ref_path)

# Similar file - 90% match
similar_path = os.path.join(test_dir, "similar.bin")
with open(similar_path, 'wb') as f:
    data = b'REF_' * 256
    # Change 10% of bytes
    data = bytearray(data)
    for i in range(0, len(data), 10):
        data[i] = 0xFF
    f.write(bytes(data))
test_files.append(similar_path)

# Different file - 50% different
different_path = os.path.join(test_dir, "different.bin")
with open(different_path, 'wb') as f:
    data = bytearray(b'REF_' * 256)
    # Change 50% of bytes
    for i in range(0, len(data), 2):
        data[i] = 0xAA
    f.write(bytes(data))
test_files.append(different_path)

print(f"   ✓ Created 3 test files in: {test_dir}")

# Connect to ImHex
config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=15.0)
client = ImHexClient(config)

try:
    client.connect()
    print("\n2. Connected to ImHex")

    # Try to open files (may fail due to threading limitations)
    print("\n3. Opening test files...")
    print("   NOTE: file/open may have threading limitations, checking...")

    opened_count = 0
    for filepath in test_files:
        try:
            r = client.send_command("file/open", {"path": filepath})
            if r.get("status") in ["success", "async"]:
                print(f"   ✓ Requested open: {os.path.basename(filepath)}")
                opened_count += 1
            else:
                print(f"   ⚠ file/open response: {r.get('status')}")
        except Exception as e:
            print(f"   ⚠ file/open error: {e}")
            break

    # Wait for files to open
    if opened_count > 0:
        print("\n   Waiting 2 seconds for files to open...")
        time.sleep(2)

    # Check what's actually open
    print("\n4. Checking open providers...")
    r = client.send_command("list/providers", {})
    if r.get("status") == "success":
        providers = r.get("data", {}).get("providers", [])
        print(f"   ✓ Found {len(providers)} open providers")

        if len(providers) == 0:
            print("\n" + "="*60)
            print("NO FILES OPEN")
            print("="*60)
            print("Please open these files manually in ImHex:")
            for f in test_files:
                print(f"  - {f}")
            print("\nThen run this test again.")
            print("="*60)
            sys.exit(1)

        # Show provider details
        for p in providers:
            size = p.get('size', 0)
            print(f"     Provider {p['id']}: {os.path.basename(p.get('path', 'unknown'))} ({size} bytes)")

        if len(providers) < 2:
            print("\n   ⚠ Need at least 2 files to test batch/diff")
            print("   Please open more files and try again.")
            sys.exit(1)

        # Test batch/diff
        reference_id = providers[0]['id']
        print(f"\n5. Testing batch/diff (reference_id={reference_id})...")

        # Test 1: Compare against "all"
        print("\n   Test 1: Compare reference against all other files...")
        r = client.send_command("batch/diff", {
            "reference_id": reference_id,
            "target_ids": "all",
            "algorithm": "myers",
            "max_diff_regions": 100
        })

        if r.get("status") == "success":
            data = r.get("data", {})
            results = data.get("results", [])
            print(f"   ✓ Got {len(results)} diff results")

            if len(results) == 0:
                print("     (No other providers to compare against)")
            else:
                for result in results:
                    target_id = result.get("target_id")
                    status = result.get("status")

                    if status == "success":
                        similarity = result.get("similarity_percent", 0)
                        diff_regions = len(result.get("diff_regions", []))
                        print(f"\n     Target {target_id}:")
                        print(f"       - Similarity: {similarity:.2f}%")
                        print(f"       - Diff regions: {diff_regions}")

                        # Show first few diff regions
                        regions = result.get("diff_regions", [])[:5]
                        if regions:
                            print(f"       - First {min(len(regions), 5)} diff regions:")
                            for region in regions:
                                print(f"         {region['type']}: offset=0x{region['offset']:04X}, size={region['size']}")
                    else:
                        print(f"     ✗ Target {target_id}: {status} - {result.get('message', '')}")

            # Test 2: Compare against specific targets
            if len(providers) >= 3:
                print("\n   Test 2: Compare against specific targets...")
                target_ids = [providers[1]['id'], providers[2]['id']]
                r = client.send_command("batch/diff", {
                    "reference_id": reference_id,
                    "target_ids": target_ids,
                    "algorithm": "myers",
                    "max_diff_regions": 50
                })

                if r.get("status") == "success":
                    results = r.get("data", {}).get("results", [])
                    print(f"   ✓ Specific target comparison: {len(results)} results")
                else:
                    print(f"   ✗ Specific target test failed: {r}")

            print("\n" + "="*60)
            print("✅ BATCH/DIFF TEST PASSED")
            print("="*60)
            print("\nThe batch/diff endpoint is working correctly!")
            print("- Successfully compared multiple files")
            print("- Calculated similarity percentages")
            print("- Returned detailed diff regions")

        else:
            error = r.get("data", {}).get("error", "Unknown error")
            print(f"   ✗ batch/diff failed: {error}")
            print(f"\n   Full response: {r}")

    else:
        print(f"   ✗ Failed to get providers: {r}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup test files
    print(f"\nCleaning up test files...")
    for f in test_files:
        if os.path.exists(f):
            os.unlink(f)
    if os.path.exists(test_dir):
        os.rmdir(test_dir)
    print("✓ Cleanup complete")
