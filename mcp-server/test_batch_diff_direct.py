#!/usr/bin/env python3
"""
Direct test for batch/diff endpoint - assumes files are already open in ImHex GUI
"""
import sys
import tempfile
import os
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

# First, create some test files for the user to open
print("Creating test files...")
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

# Different file - completely different
different_path = os.path.join(test_dir, "different.bin")
with open(different_path, 'wb') as f:
    f.write(b'DIFF' * 256)  # 1KB
test_files.append(different_path)

print(f"✓ Created test files in: {test_dir}")
for i, f in enumerate(test_files):
    print(f"  {i+1}. {f}")

print("\n" + "="*60)
print("MANUAL STEP REQUIRED:")
print("="*60)
print("Please open these files in ImHex:")
print("  File > Open... and select each file above")
print("")
print("Once all 3 files are open, press Enter to continue...")
print("="*60)
input()

# Now connect and test
config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=10.0)
client = ImHexClient(config)

try:
    client.connect()
    print("✓ Connected to ImHex")

    # Get list of open providers
    print("\n1. Getting list of providers...")
    r = client.send_command("list/providers", {})
    if r.get("status") == "success":
        providers = r.get("data", {}).get("providers", [])
        print(f"✓ Got {len(providers)} open providers")

        if len(providers) < 2:
            print("✗ Need at least 2 files open to test batch/diff")
            sys.exit(1)

        # Show provider details
        for p in providers:
            print(f"  Provider {p['id']}: {p.get('path', 'unknown')}")

        # Use first provider as reference, compare against all others
        reference_id = providers[0]['id']
        print(f"\n2. Testing batch/diff with reference_id={reference_id}...")

        # Test 1: Compare against "all"
        print("\n   Test 1: Compare against all other files...")
        r = client.send_command("batch/diff", {
            "reference_id": reference_id,
            "target_ids": "all",
            "algorithm": "myers",
            "max_diff_regions": 1000
        })

        if r.get("status") == "success":
            data = r.get("data", {})
            results = data.get("results", [])
            print(f"   ✓ Got {len(results)} diff results")

            for result in results:
                target_id = result.get("target_id")
                similarity = result.get("similarity_percent", 0)
                diff_regions = len(result.get("diff_regions", []))
                status = result.get("status")

                if status == "success":
                    print(f"     - Target {target_id}: {similarity:.2f}% similar, {diff_regions} diff regions")

                    # Show first few diff regions
                    regions = result.get("diff_regions", [])[:3]
                    for region in regions:
                        print(f"       {region['type']}: offset=0x{region['offset']:X}, size={region['size']}")
                else:
                    print(f"     - Target {target_id}: {status} - {result.get('message', '')}")
        else:
            print(f"   ✗ batch/diff failed: {r}")

        # Test 2: Compare against specific targets
        if len(providers) >= 3:
            print("\n   Test 2: Compare against specific target...")
            target_ids = [providers[1]['id'], providers[2]['id']]
            r = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": target_ids,
                "algorithm": "myers"
            })

            if r.get("status") == "success":
                data = r.get("data", {})
                results = data.get("results", [])
                print(f"   ✓ Got {len(results)} diff results for specific targets")
            else:
                print(f"   ✗ batch/diff failed: {r}")

        print("\n" + "="*60)
        print("BATCH/DIFF TEST COMPLETE")
        print("="*60)

    else:
        print(f"✗ Failed to get providers: {r}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup test files
    print(f"\nCleaning up test files in {test_dir}...")
    for f in test_files:
        if os.path.exists(f):
            os.unlink(f)
    os.rmdir(test_dir)
    print("✓ Cleanup complete")
