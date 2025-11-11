#!/usr/bin/env python3
import sys
import tempfile
import time
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

# Create test file
with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
    f.write(b'TEST' + b'\x00' * 100)
    test_file = f.name

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=10.0, read_timeout=10.0)
client = ImHexClient(config)

try:
    client.connect()
    print(f"✓ Connected to ImHex")
    
    # Open file
    r1 = client.send_command("file/open", {"path": test_file})
    print(f"✓ file/open response: {r1}")
    
    if r1.get("status") == "success":
        print(f"✓ file/open succeeded")
        
        # Wait for file to actually open
        time.sleep(0.5)
        
        # Check if file is now open
        r2 = client.send_command("list/providers", {})
        if r2.get("status") == "success":
            providers = r2.get("data", {}).get("providers", [])
            print(f"✓ Got {len(providers)} providers")
            if providers:
                print(f"  Provider ID: {providers[0]['id']}, Name: {providers[0]['name']}")
        else:
            print(f"✗ list/providers failed: {r2.get('error')}")
    else:
        print(f"✗ file/open failed: {r1.get('error')}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    import os
    if os.path.exists(test_file):
        os.unlink(test_file)
