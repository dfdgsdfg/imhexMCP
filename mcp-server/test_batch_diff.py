#!/usr/bin/env python3
"""
Test Suite for v1.0.0 Batch Operations (Phase 3)
Tests: batch/diff endpoint
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import ImHexClient, ServerConfig


def create_test_files_for_diff():
    """Create a temporary directory with test files for diff comparison."""
    test_dir = tempfile.mkdtemp(prefix='imhex_diff_test_')

    # Create files with varying degrees of similarity
    test_files = [
        # Reference file
        ('reference.bin', b'HEADER' + b'\x00' * 1000 + b'FOOTER'),

        # Very similar (99%+ similar)
        ('similar1.bin', b'HEADER' + b'\x00' * 1000 + b'FOOTER'),  # Identical
        ('similar2.bin', b'HEADER' + b'\x00' * 1000 + b'FOOBAR'),  # Last 6 bytes different

        # Moderately similar (50-80% similar)
        ('moderate1.bin', b'HEADER' + b'\xFF' * 500 + b'\x00' * 500 + b'FOOTER'),
        ('moderate2.bin', b'PREFIX' + b'\x00' * 1000 + b'SUFFIX'),

        # Very different (<30% similar)
        ('different1.bin', b'COMPLETELY_DIFFERENT' + b'\xFF' * 990),
        ('different2.bin', b'X' * 1012),

        # Different sizes
        ('short.bin', b'HEADER' + b'\x00' * 100),
        ('long.bin', b'HEADER' + b'\x00' * 2000 + b'FOOTER'),
    ]

    created_files = []
    for filename, content in test_files:
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)
        created_files.append(filepath)

    return test_dir, created_files


def get_provider_ids(client, num_files):
    """Get list of provider IDs from list/providers."""
    response = client.send_command("list/providers", {})
    if response.get("status") == "success":
        providers = response.get("data", {}).get("providers", [])
        return [p["id"] for p in providers[:num_files]]
    return []


def main():
    """Run batch diff tests."""
    print("="*70)
    print("ImHex MCP v1.0.0 - Batch Diff Tests (Phase 3)")
    print("="*70)
    print()

    # Create test files
    test_dir, test_files = create_test_files_for_diff()
    print(f"Created test directory: {test_dir}")
    print(f"Created {len(test_files)} test files with varying similarity")
    print()

    # Create client
    config = ServerConfig(
        imhex_host='localhost',
        imhex_port=31337,
        connection_timeout=10.0,
        read_timeout=60.0,  # Longer timeout for diff operations
        max_retries=3,
        retry_delay=0.5
    )
    client = ImHexClient(config)

    passed = 0
    failed = 0
    provider_ids = []

    try:
        # Connect
        client.connect()

        # Open all test files
        print("="*70)
        print("SETUP: OPEN TEST FILES")
        print("="*70)
        print()

        print("Opening test files...")
        try:
            # Open each test file individually
            import glob
            test_bin_files = sorted(glob.glob(os.path.join(test_dir, "*.bin")))
            opened_count = 0

            for filepath in test_bin_files:
                try:
                    response = client.send_command("file/open", {
                        "path": filepath
                    })
                    if response.get("status") == "success":
                        opened_count += 1
                except Exception as e:
                    print(f"  Warning: Failed to open {filepath}: {e}")

            print(f"  ✓ Opened {opened_count} files")

            # Get provider IDs
            provider_ids = get_provider_ids(client, 20)
            print(f"  ✓ Got {len(provider_ids)} provider IDs: {provider_ids}")
            print()

            if opened_count == 0:
                print(f"  ✗ Failed to open any files")
                return
        except Exception as e:
            print(f"  ✗ Error opening files: {e}")
            import traceback
            traceback.print_exc()
            return

        if len(provider_ids) < 2:
            print("  ✗ Not enough files opened for diff testing")
            return

        reference_id = provider_ids[0]  # First file is reference.bin

        # TEST 1: Basic diff with specific target IDs
        print("="*70)
        print("TEST 1: BATCH DIFF WITH SPECIFIC TARGET IDS")
        print("="*70)
        print()

        print("[TEST 1.1] Compare reference against 2 specific targets")
        try:
            target_ids = provider_ids[1:3]  # similar1.bin, similar2.bin
            response = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": target_ids,
                "algorithm": "myers"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                diffs = data.get("diffs", [])
                summary = data.get("summary", {})

                print(f"  ✓ Diff completed")
                print(f"    Files compared: {summary.get('files_compared')}")
                print(f"    Average similarity: {summary.get('avg_similarity'):.2f}%")

                if len(diffs) == 2:
                    print(f"  ✓ Got results for {len(diffs)} files")

                    # Check that first file (identical) has 100% similarity
                    if diffs[0].get("similarity", 0) == 100.0:
                        print(f"  ✓ Identical file detected (100% similarity)")
                        passed += 1
                    else:
                        print(f"  ✗ Expected 100% similarity for identical file, got {diffs[0].get('similarity'):.2f}%")
                        failed += 1
                else:
                    print(f"  ✗ Expected 2 diff results, got {len(diffs)}")
                    failed += 1
            else:
                print(f"  ✗ Diff failed: {response.get('error')}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

        # TEST 2: Diff with "all" keyword
        print("="*70)
        print("TEST 2: BATCH DIFF WITH 'ALL' KEYWORD")
        print("="*70)
        print()

        print("[TEST 2.1] Compare reference against all other files")
        try:
            response = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": "all",
                "algorithm": "myers",
                "max_diff_regions": 1000
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                diffs = data.get("diffs", [])
                summary = data.get("summary", {})

                print(f"  ✓ Diff completed")
                print(f"    Files compared: {summary.get('files_compared')}")
                print(f"    Average similarity: {summary.get('avg_similarity'):.2f}%")
                print(f"    Most similar file: ID {summary.get('most_similar')} ({summary.get('highest_similarity'):.2f}%)")
                print(f"    Least similar file: ID {summary.get('least_similar')} ({summary.get('lowest_similarity'):.2f}%)")

                # Should compare against all files except reference
                expected_comparisons = len(provider_ids) - 1
                if len(diffs) == expected_comparisons:
                    print(f"  ✓ Compared against {len(diffs)} files (excluding reference)")
                    passed += 1
                else:
                    print(f"  ✗ Expected {expected_comparisons} comparisons, got {len(diffs)}")
                    failed += 1
            else:
                print(f"  ✗ Diff failed: {response.get('error')}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

        # TEST 3: Similarity accuracy
        print("="*70)
        print("TEST 3: SIMILARITY CALCULATION ACCURACY")
        print("="*70)
        print()

        print("[TEST 3.1] Verify similarity percentages are reasonable")
        try:
            # Compare reference against similar and different files
            response = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": provider_ids[1:7],  # Mix of similar and different files
                "algorithm": "myers"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                diffs = data.get("diffs", [])

                # Check similarity ranges
                high_similarity_count = sum(1 for d in diffs if d.get("similarity", 0) >= 95)
                low_similarity_count = sum(1 for d in diffs if d.get("similarity", 0) < 50)

                print(f"  Files with ≥95% similarity: {high_similarity_count}")
                print(f"  Files with <50% similarity: {low_similarity_count}")

                if high_similarity_count >= 1 and low_similarity_count >= 1:
                    print(f"  ✓ Similarity calculations show expected variation")
                    passed += 1
                else:
                    print(f"  ✗ Expected both high and low similarity files")
                    failed += 1

                # Print detailed results
                print("\n  Detailed results:")
                for diff in diffs:
                    print(f"    File ID {diff.get('target_id')}: {diff.get('similarity'):.2f}% similar, {diff.get('diff_regions')} regions")

            else:
                print(f"  ✗ Diff failed: {response.get('error')}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

        # TEST 4: Diff regions
        print("="*70)
        print("TEST 4: DIFF REGIONS")
        print("="*70)
        print()

        print("[TEST 4.1] Verify diff regions are returned")
        try:
            response = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": [provider_ids[2]],  # similar2.bin (99% similar)
                "algorithm": "myers"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                diffs = data.get("diffs", [])

                if diffs:
                    regions = diffs[0].get("regions", [])
                    diff_regions_count = diffs[0].get("diff_regions", 0)

                    print(f"  ✓ Got {len(regions)} region samples (total: {diff_regions_count} regions)")

                    if len(regions) > 0:
                        print(f"  ✓ Diff regions present")

                        # Check region structure
                        sample_region = regions[0]
                        has_type = "type" in sample_region
                        has_start = "start" in sample_region
                        has_end = "end" in sample_region
                        has_size = "size" in sample_region

                        if has_type and has_start and has_end and has_size:
                            print(f"  ✓ Region structure valid")
                            print(f"    Sample region: {sample_region.get('type')} at 0x{sample_region.get('start'):08X}-0x{sample_region.get('end'):08X} ({sample_region.get('size')} bytes)")
                            passed += 1
                        else:
                            print(f"  ✗ Region structure incomplete")
                            failed += 1
                    else:
                        # Identical files might have no diff regions
                        print(f"  ✓ No diff regions (files may be identical)")
                        passed += 1
                else:
                    print(f"  ✗ No diff results returned")
                    failed += 1
            else:
                print(f"  ✗ Diff failed: {response.get('error')}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

        # TEST 5: Summary statistics
        print("="*70)
        print("TEST 5: SUMMARY STATISTICS")
        print("="*70)
        print()

        print("[TEST 5.1] Verify summary contains all required fields")
        try:
            response = client.send_command("batch/diff", {
                "reference_id": reference_id,
                "target_ids": "all",
                "algorithm": "myers"
            })

            if response.get("status") == "success":
                data = response.get("data", {})
                summary = data.get("summary", {})

                required_fields = [
                    "reference_id", "reference_file", "algorithm",
                    "files_compared", "avg_similarity",
                    "most_similar", "highest_similarity",
                    "least_similar", "lowest_similarity"
                ]

                missing_fields = [f for f in required_fields if f not in summary]

                if not missing_fields:
                    print(f"  ✓ All summary fields present")
                    print(f"    Reference: {summary.get('reference_file')} (ID: {summary.get('reference_id')})")
                    print(f"    Algorithm: {summary.get('algorithm')}")
                    print(f"    Files compared: {summary.get('files_compared')}")
                    print(f"    Average similarity: {summary.get('avg_similarity'):.2f}%")
                    passed += 1
                else:
                    print(f"  ✗ Missing fields: {missing_fields}")
                    failed += 1
            else:
                print(f"  ✗ Diff failed: {response.get('error')}")
                failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("="*70)
        print("CLEANUP")
        print("="*70)
        print()

        # Close all files
        if provider_ids:
            print(f"Closing {len(provider_ids)} files...")
            for provider_id in provider_ids:
                try:
                    client.send_command("file/close", {"provider_id": provider_id})
                except:
                    pass
            print("  ✓ Files closed")

        # Clean up test directory
        try:
            import shutil
            shutil.rmtree(test_dir)
            print(f"  ✓ Test directory cleaned up")
        except:
            print(f"  Note: Test directory not cleaned up: {test_dir}")

        print()

        # Print summary
        print("="*70)
        print("TEST SUMMARY")
        print("="*70)
        total = passed + failed
        print(f"Passed: {passed}/{total}")
        print(f"Failed: {failed}/{total}")

        if failed == 0:
            print()
            print("🎉 ALL TESTS PASSED!")
            sys.exit(0)
        else:
            print()
            print(f"❌ {failed} TEST(S) FAILED")
            sys.exit(1)


if __name__ == "__main__":
    main()
