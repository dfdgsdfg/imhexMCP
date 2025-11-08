#!/usr/bin/env python3
"""
Test script for ImHex MCP Server
This script tests the connection to ImHex and basic functionality.
"""

import socket
import json
import sys


def test_imhex_connection(host="localhost", port=31337):
    """Test connection to ImHex TCP server."""
    print(f"Testing connection to ImHex at {host}:{port}...")

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        print("✓ Connected to ImHex successfully")

        # Test capabilities endpoint
        request = {
            "endpoint": "imhex/capabilities",
            "data": {}
        }

        print("\nSending capabilities request...")
        request_json = json.dumps(request) + "\n"
        sock.sendall(request_json.encode('utf-8'))

        # Receive response
        response_data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in response_data:
                break

        response_str = response_data.decode('utf-8').strip()
        response = json.loads(response_str)

        print("\nResponse:")
        print(json.dumps(response, indent=2))

        if response.get("status") == "success":
            print("\n✓ ImHex is responding correctly")
            print("\nImHex capabilities:")
            data = response.get("data", {})
            for key, value in data.items():
                print(f"  {key}: {value}")
            return True
        else:
            print("\n✗ ImHex returned an error")
            print(f"  Error: {response.get('data', {}).get('error', 'Unknown error')}")
            return False

    except socket.timeout:
        print("✗ Connection timed out")
        print("\nTroubleshooting:")
        print("  1. Make sure ImHex is running")
        print("  2. Enable Network Interface in ImHex Settings → General")
        print("  3. Check if ImHex is listening on port 31337")
        return False

    except ConnectionRefusedError:
        print("✗ Connection refused")
        print("\nTroubleshooting:")
        print("  1. Make sure ImHex is running")
        print("  2. Enable Network Interface in ImHex Settings → General")
        print("  3. Restart ImHex after enabling the network interface")
        return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    finally:
        try:
            sock.close()
        except:
            pass


def main():
    """Main test function."""
    print("ImHex MCP Server - Connection Test")
    print("=" * 50)

    success = test_imhex_connection()

    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
        print("\nYou can now use the MCP server with Claude.")
        return 0
    else:
        print("✗ Tests failed")
        print("\nPlease fix the issues above and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
