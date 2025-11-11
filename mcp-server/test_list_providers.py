#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

config = ServerConfig(imhex_host='localhost', imhex_port=31337)
client = ImHexClient(config)

try:
    client.connect()
    r = client.send_command("list/providers", {})
    print(r)
except Exception as e:
    print(f"Error: {e}")
