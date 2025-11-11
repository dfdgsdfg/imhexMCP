#!/usr/bin/env python3
import socket
import json

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 31337))
    
    # Test builtin endpoint
    request = {"endpoint": "imhex/capabilities", "data": {}}
    request_json = json.dumps(request) + "\n"
    sock.sendall(request_json.encode('utf-8'))
    
    response_data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response_data += chunk
        if b"\n" in response_data:
            break
    
    response = json.loads(response_data.decode('utf-8'))
    print("Response:", json.dumps(response, indent=2))
    
    if response.get("status") == "success":
        commands = response.get("data", {}).get("commands", [])
        print(f"\n✓ Network interface is working!")
        print(f"  Available endpoints: {len(commands)}")
        print(f"  Has batch/diff: {'batch/diff' in commands}")
        if "batch/diff" in commands:
            print("  Has batch/open_directory: " + str("batch/open_directory" in commands))
    
    sock.close()
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
