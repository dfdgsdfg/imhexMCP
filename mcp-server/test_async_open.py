#!/usr/bin/env python3
import sys
import time
import tempfile
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

# Create test file
with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
    f.write(b'TEST' + b'\x00' * 1000)
    test_file = f.name

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=5.0)
client = ImHexClient(config)

try:
    client.connect()
    print(f"✓ Connected")
    
    # Request file open (async)
    r1 = client.send_command("file/open", {"path": test_file})
    print(f"file/open response: {r1}")
    
    # Wait for file to open
    print("Waiting for file to open...")
    time.sleep(1)
    
    # Check if file opened
    r2 = client.send_command("list/providers", {})
    if r2.get("status") == "success":
        providers = r2.get("data", {}).get("providers", [])
        print(f"✓ Got {len(providers)} providers")
        if providers:
            print(f"  Provider: {providers[0]}")
    else:
        print(f"✗ list/providers failed: {r2}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    import os
    if os.path.exists(test_file):
        os.unlink(test_file)
