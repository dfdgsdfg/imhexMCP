#!/usr/bin/env python3
"""
Simple test for batch/diff - assumes files are already open in ImHex
"""
import sys
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=10.0)
client = ImHexClient(config)

try:
    print("Connecting to ImHex...")
    client.connect()
    print("✓ Connected")

    # Get list of open providers
    print("\nGetting open providers...")
    r = client.send_command("list/providers", {})
    if r.get("status") == "success":
        providers = r.get("data", {}).get("providers", [])
        print(f"✓ Found {len(providers)} open providers")

        if len(providers) == 0:
            print("\nNo files open. Please open some files in ImHex GUI and try again.")
            sys.exit(0)

        for p in providers:
            print(f"  Provider {p['id']}: {p.get('path', 'unknown')} ({p.get('size', 0)} bytes)")

        if len(providers) >= 2:
            print("\n" + "="*60)
            print("Testing batch/diff...")
            print("="*60)

            # Use first provider as reference
            reference_id = providers[0]['id']
            print(f"\nReference: Provider {reference_id}")
            print("Comparing against all other providers...")

            r = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": "all",
                "algorithm": "myers",
                "max_diff_regions": 100
            })

            if r.get("status") == "success":
                data = r.get("data", {})
                results = data.get("results", [])
                print(f"\n✓ Got {len(results)} diff results\n")

                for result in results:
                    target_id = result.get("target_id")
                    status = result.get("status")

                    if status == "success":
                        similarity = result.get("similarity_percent", 0)
                        diff_regions = len(result.get("diff_regions", []))
                        print(f"Target {target_id}:")
                        print(f"  Similarity: {similarity:.2f}%")
                        print(f"  Diff regions: {diff_regions}")

                        # Show first 3 diff regions
                        regions = result.get("diff_regions", [])[:3]
                        if regions:
                            print(f"  First {len(regions)} diff regions:")
                            for region in regions:
                                print(f"    {region['type']}: offset=0x{region['offset']:04X}, size={region['size']}")
                        print()
                    else:
                        print(f"Target {target_id}: {status} - {result.get('message', '')}\n")

                print("="*60)
                print("✅ BATCH/DIFF TEST PASSED")
                print("="*60)
            else:
                error = r.get("data", {}).get("error", "Unknown error")
                print(f"✗ batch/diff failed: {error}")
        else:
            print(f"\nNeed at least 2 files open to test batch/diff. Currently have {len(providers)}.")
    else:
        print(f"✗ Failed to get providers: {r}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
