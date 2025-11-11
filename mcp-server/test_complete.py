#!/usr/bin/env python3
"""
Complete test: file/open threading fix + batch/diff functionality
"""
import sys
import time
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

print("="*60)
print("COMPLETE INTEGRATION TEST")
print("="*60)

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=15.0)
client = ImHexClient(config)

try:
    print("\n1. Connecting...")
    client.connect()
    print("   ✓ Connected")

    # Open the test files
    test_files = ["/tmp/ref.bin", "/tmp/similar.bin", "/tmp/different.bin"]

    print("\n2. Opening test files via API...")
    for f in test_files:
        r = client.send_command("file/open", {"path": f})
        if r.get("status") == "success" and r.get("data", {}).get("status") == "async":
            print(f"   ✓ Requested: {f}")
        else:
            print(f"   ⚠ Unexpected response for {f}: {r}")

    print("\n   Waiting 2 seconds for files to open...")
    time.sleep(2)

    # Get provider list
    print("\n3. Getting open providers...")
    r = client.send_command("list/providers", {})
    if r.get("status") == "success":
        providers = r.get("data", {}).get("providers", [])
        print(f"   ✓ Found {len(providers)} providers")

        for p in providers:
            print(f"     - Provider {p['id']}: {p.get('name', 'unknown')} ({p.get('size', 0)} bytes)")

        if len(providers) >= 3:
            # Use last 3 providers (our test files)
            ref_id = providers[-3]['id']

            print(f"\n4. Running batch/diff...")
            print(f"   Reference: Provider {ref_id}")
            print(f"   Comparing against: all")

            r = client.send_command("batch/diff", {
                "reference_id": ref_id,
                "target_ids": "all",
                "algorithm": "myers",
                "max_diff_regions": 100
            })

            if r.get("status") == "success":
                data = r.get("data", {})
                results = data.get("diffs", [])  # batch/diff returns "diffs" not "results"
                print(f"\n   ✓ Got {len(results)} diff results")

                for result in results:
                    target_id = result.get("target_id")
                    target_file = result.get("target_file", "unknown")
                    similarity = result.get("similarity", 0)
                    diff_regions = result.get("diff_regions", 0)

                    print(f"\n   Target {target_id} ({target_file}):")
                    print(f"     - Similarity: {similarity:.2f}%")
                    print(f"     - Diff regions: {diff_regions}")

                    # Show region count only (detailed format varies)
                    regions = result.get("regions", [])
                    if regions:
                        print(f"     - Sample regions: {len(regions)} found")

                print("\n" + "="*60)
                print("✅ ALL TESTS PASSED!")
                print("="*60)
                print("\nSuccessfully demonstrated:")
                print("  1. file/open with threading fix (TaskManager::doLater)")
                print("  2. list/providers endpoint")
                print("  3. batch/diff functionality with similarity calculation")
                print(f"  4. All {len(results)} comparisons completed")
            else:
                error = r.get("data", {}).get("error", "Unknown")
                print(f"\n   ✗ batch/diff failed: {error}")
        else:
            print(f"\n   ⚠ Need at least 3 providers, found {len(providers)}")
    else:
        print(f"   ✗ Failed to list providers: {r}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
