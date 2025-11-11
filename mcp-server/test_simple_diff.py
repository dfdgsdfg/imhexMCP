#!/usr/bin/env python3
import sys
import tempfile
import os
sys.path.insert(0, '.')
from server import ImHexClient, ServerConfig

# Create two simple test files
with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f1:
    f1.write(b'TEST' + b'\\x00' * 100)
    file1 = f1.name

with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f2:
    f2.write(b'TEST' + b'\\xFF' * 100)
    file2 = f2.name

config = ServerConfig(imhex_host='localhost', imhex_port=31337, connection_timeout=10.0, read_timeout=30.0)
client = ImHexClient(config)

try:
    client.connect()
    print(f"✓ Connected to ImHex")
    
    # Open files
    r1 = client.send_command("file/open", {"path": file1})
    r2 = client.send_command("file/open", {"path": file2})
    
    if r1.get("status") == "success" and r2.get("status") == "success":
        print(f"✓ Opened both files")
        
        # Get provider IDs
        r3 = client.send_command("list/providers", {})
        if r3.get("status") == "success":
            providers = r3.get("data", {}).get("providers", [])
            print(f"✓ Got {len(providers)} providers")
            
            if len(providers) >= 2:
                ref_id = providers[0]["id"]
                target_id = providers[1]["id"]
                
                print(f"Running batch/diff with reference={ref_id}, target={target_id}...")
                
                r4 = client.send_command("batch/diff", {
                    "reference_id": ref_id,
                    "target_ids": [target_id],
                    "algorithm": "myers"
                })
                
                if r4.get("status") == "success":
                    data = r4.get("data", {})
                    diffs = data.get("diffs", [])
                    summary = data.get("summary", {})
                    
                    print(f"✓ Batch diff succeeded!")
                    print(f"  Files compared: {summary.get('files_compared')}")
                    print(f"  Average similarity: {summary.get('avg_similarity'):.2f}%")
                    if diffs:
                        print(f"  First result: {diffs[0].get('similarity'):.2f}% similar, {diffs[0].get('diff_regions')} regions")
                else:
                    print(f"✗ Batch diff failed: {r4.get('error')}")
            else:
                print(f"✗ Not enough providers: {len(providers)}")
        else:
            print(f"✗ Failed to list providers: {r3.get('error')}")
    else:
        print(f"✗ Failed to open files")
finally:
    os.unlink(file1)
    os.unlink(file2)
