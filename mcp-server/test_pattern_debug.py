#!/usr/bin/env python3
"""Quick test to debug pattern matching"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from server import ImHexClient, ServerConfig

# Create test directory
test_dir = tempfile.mkdtemp(prefix='imhex_pattern_debug_')
test_files = [
    ('test1.bin', b'TEST1' + b'\x00' * 100),
    ('test2.bin', b'TEST2' + b'\x00' * 200),
    ('test3.exe', b'MZ' + b'\x00' * 50),
    ('data.txt', b'This is text'),
]

for filename, content in test_files:
    filepath = os.path.join(test_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(content)

print(f"Created test directory: {test_dir}")
print(f"Test files: {[f[0] for f in test_files]}")
print()

# Connect to ImHex
config = ServerConfig(
    imhex_host='localhost',
    imhex_port=31337,
    connection_timeout=10.0,
    read_timeout=30.0
)
client = ImHexClient(config)
client.connect()

print("Test 1: Open all files with * pattern")
response = client.send_command("batch/open_directory", {
    "directory": test_dir,
    "pattern": "*"
})
print(f"Result: {response.get('data', {}).get('total_opened')} files opened")
print()

# Close all
file_list = client.send_command("file/list", {})
if file_list.get("status") == "success":
    files = file_list.get("data", {}).get("files", [])
    for file_info in files:
        client.send_command("file/close", {"provider_id": file_info["id"]})

print("Test 2: Open only .bin files with *.bin pattern")
response = client.send_command("batch/open_directory", {
    "directory": test_dir,
    "pattern": "*.bin"
})
data = response.get('data', {})
print(f"Result: {data.get('total_opened')} files opened")
print(f"Files found: {data.get('files_found')}")
if data.get('opened_files'):
    for f in data.get('opened_files', []):
        print(f"  - {f.get('name')}")
print()

# Cleanup
for filename, _ in test_files:
    filepath = os.path.join(test_dir, filename)
    if os.path.exists(filepath):
        os.unlink(filepath)
os.rmdir(test_dir)

print("Check /tmp/imhex_debug.log for debug output from ImHex")
