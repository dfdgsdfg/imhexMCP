#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=5.0, read_timeout=5.0)
client = ImHexClient(config)

try:
    client.connect()
    print(f"✓ Connected")
    
    r = client.send_command("file/open", {"path": "/tmp/test.bin"})
    print(f"Response: {r}")
except Exception as e:
    print(f"✗ Error: {e}")
