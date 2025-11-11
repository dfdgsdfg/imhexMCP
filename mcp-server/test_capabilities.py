#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=5.0)
client = ImHexClient(config)

try:
    client.connect()
    print(f"✓ Connected")
    
    r = client.send_command("imhex/capabilities", {})
    if r.get("status") == "success":
        commands = r.get("data", {}).get("commands", [])
        print(f"✓ Got {len(commands)} commands")
        print(f"  Has batch/diff: {'batch/diff' in commands}")
    else:
        print(f"✗ Failed: {r}")
except Exception as e:
    print(f"✗ Error: {e}")
