#!/usr/bin/env python3
"""
Test file/open threading fix - verifies TaskManager::doLater() solution works
"""
import sys
import tempfile
import os
import time
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

print("="*60)
print("FILE/OPEN THREADING FIX TEST")
print("="*60)

# Create test files
print("\n1. Creating test files...")
test_files = []
for i in range(3):
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=f'_test{i}.bin') as f:
        f.write(b'TEST' * 256)  # 1KB
        test_files.append(f.name)
        print(f"   Created: {f.name}")

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=5.0)
client = ImHexClient(config)

try:
    print("\n2. Connecting to ImHex...")
    client.connect()
    print("   ✓ Connected")

    # Get initial provider count
    r = client.send_command("list/providers", {})
    initial_count = len(r.get("data", {}).get("providers", []))
    print(f"\n3. Initial providers: {initial_count}")

    # Test opening files
    print("\n4. Testing file/open endpoint (with threading fix)...")
    opened_files = []

    for i, filepath in enumerate(test_files):
        print(f"\n   Test {i+1}/3: Opening {os.path.basename(filepath)}...")

        try:
            r = client.send_command("file/open", {"path": filepath})

            if r.get("status") == "success":
                data = r.get("data", {})
                status = data.get("status")
                message = data.get("message", "")

                print(f"   ✓ Response: status={status}")
                print(f"   ✓ Message: {message}")

                if status == "async":
                    opened_files.append(filepath)
                else:
                    print(f"   ⚠ Unexpected status: {status}")
            else:
                print(f"   ✗ Failed: {r}")
                break

        except Exception as e:
            print(f"   ✗ Exception: {e}")
            break

    # Wait for files to open
    if opened_files:
        print(f"\n5. Waiting 2 seconds for {len(opened_files)} files to open on main thread...")
        time.sleep(2)

        # Check if files opened
        print("\n6. Checking if files opened...")
        r = client.send_command("list/providers", {})

        if r.get("status") == "success":
            providers = r.get("data", {}).get("providers", [])
            new_count = len(providers)
            added = new_count - initial_count

            print(f"   ✓ Current providers: {new_count} (added {added})")

            for p in providers[initial_count:]:
                print(f"     - Provider {p['id']}: {os.path.basename(p.get('path', 'unknown'))} ({p.get('size', 0)} bytes)")

            if added > 0:
                print(f"\n" + "="*60)
                print(f"✅ THREADING FIX SUCCESSFUL!")
                print("="*60)
                print(f"\nfile/open endpoint now works without crashing:")
                print(f"  - Uses TaskManager::doLater() to schedule on main thread")
                print(f"  - Returns async response immediately")
                print(f"  - {added} file(s) opened successfully")
            else:
                print(f"\n" + "="*60)
                print(f"⚠️ FILES DID NOT OPEN")
                print("="*60)
                print(f"\nThe endpoint didn't crash, but files may not have opened.")
                print(f"This could be due to:")
                print(f"  - File permissions")
                print(f"  - ImHex settings")
                print(f"  - Timing issues")
        else:
            print(f"   ✗ Failed to list providers: {r}")

    print("\n7. Checking ImHex is still running...")
    r = client.send_command("imhex/capabilities", {})
    if r.get("status") == "success":
        print("   ✓ ImHex still responding - no crash!")
    else:
        print("   ✗ ImHex not responding")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    print(f"\n8. Cleaning up test files...")
    for f in test_files:
        if os.path.exists(f):
            try:
                os.unlink(f)
            except:
                pass
    print("   ✓ Cleanup complete")
