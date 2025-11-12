# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Considerations

### Network Interface
The MCP plugin adds a network interface to ImHex that listens on `localhost:31337`. This interface:
- **Only binds to localhost (127.0.0.1)** - Not accessible from other machines
- **No authentication by default** - Any local process can connect
- **JSON over TCP** - Plaintext communication

### Recommendations for Secure Usage

1. **Sandboxed Environment:**
   - Run ImHex in a VM or container when analyzing untrusted binaries
   - Use Docker or similar isolation for automated malware analysis

2. **Firewall Rules:**
   - Ensure localhost-only access (should be default)
   - Block port 31337 from external networks

3. **File Access:**
   - The network interface can open any file ImHex can access
   - Limit ImHex's file system permissions appropriately
   - Use read-only mounts when possible

4. **Untrusted Input:**
   - When analyzing malware or untrusted binaries, assume they may:
     - Contain exploits for file parsers
     - Attempt to escape sandboxes
     - Connect to command & control servers
   - Use appropriate isolation and monitoring

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please:

### DO:
1. **Email privately:** Create an issue with title "SECURITY: [brief description]" and mark it private
2. **Provide details:**
   - Type of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if you have one)

3. **Allow time:** Give us reasonable time to address before public disclosure
4. **Coordinate disclosure:** Work with us on timing and details of public disclosure

### DON'T:
- Don't publicly disclose the vulnerability before we've had a chance to fix it
- Don't exploit the vulnerability beyond proving it exists
- Don't access others' data or systems

## Vulnerability Response Timeline

1. **Acknowledgment:** Within 48 hours
2. **Assessment:** Within 1 week
3. **Fix development:** Depends on severity
   - Critical: Within 7 days
   - High: Within 14 days
   - Medium: Within 30 days
   - Low: Next release
4. **Public disclosure:** After fix is released and users have time to update

## Security Best Practices for Users

### Malware Analysis
When using ImHex MCP for malware analysis:

```bash
# Use a dedicated analysis VM/container
docker run -it --rm \
  -v /path/to/samples:/samples:ro \
  -v /path/to/results:/results \
  imhex-mcp

# Or run in a VM with network isolation
```

### Network Isolation
If you need network isolation:

```bash
# Run ImHex without network access (except localhost)
# macOS:
pfctl -e
# Add rules to block ImHex except localhost

# Linux:
iptables -A OUTPUT -m owner --uid-owner $(id -u imhex-user) \
  -d 127.0.0.1 -j ACCEPT
iptables -A OUTPUT -m owner --uid-owner $(id -u imhex-user) -j DROP
```

### File Permissions
Run ImHex with minimal permissions:

```bash
# Create dedicated user for analysis
sudo useradd -m -s /bin/bash imhex-analysis
sudo -u imhex-analysis /path/to/imhex
```

## Known Limitations

1. **No Authentication:** Network interface has no authentication
   - Mitigation: Only binds to localhost
   - Future: May add API key authentication

2. **No Encryption:** Communication is plaintext TCP
   - Mitigation: Only on localhost (not exposed to network)
   - Future: May add TLS support

3. **File System Access:** Can read any file ImHex user has access to
   - Mitigation: Run with minimal privileges
   - Use filesystem sandboxing (AppArmor, SELinux, etc.)

4. **Resource Limits:** No built-in limits on file size or processing time
   - Mitigation: Use OS-level resource limits (ulimit, cgroups)
   - Future: May add configurable limits

## Security Updates

Security fixes will be:
- Released as patches to the affected versions
- Announced via GitHub Security Advisories
- Documented in CHANGELOG.md with [SECURITY] tag

## Contact

For security concerns: Create a private issue on GitHub or contact repository maintainers.

For general security questions: Open a discussion on GitHub.
