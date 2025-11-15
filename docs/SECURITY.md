# ImHex MCP Security Guide

## Overview

The ImHex MCP server includes comprehensive security features to protect against common vulnerabilities and attacks. This guide covers all security mechanisms, configuration options, and best practices.

## Table of Contents

1. [Security Features](#security-features)
2. [Threat Model](#threat-model)
3. [Security Configuration](#security-configuration)
4. [Input Validation](#input-validation)
5. [Rate Limiting](#rate-limiting)
6. [IP Filtering](#ip-filtering)
7. [Attack Prevention](#attack-prevention)
8. [Security Best Practices](#security-best-practices)
9. [Security Auditing](#security-auditing)
10. [Incident Response](#incident-response)

---

## Security Features

### Core Security Mechanisms

The ImHex MCP server implements multiple layers of defense:

1. **Input Validation & Sanitization**
   - String length limits
   - Type validation
   - Control character removal
   - Path traversal protection
   - Hex string validation
   - Payload size limits

2. **Injection Attack Prevention**
   - SQL injection detection
   - Command injection detection
   - Pattern-based threat detection
   - Security event logging

3. **Rate Limiting**
   - Token bucket algorithm
   - Global rate limits
   - Per-client rate limits
   - Configurable burst capacity
   - Automatic client cleanup

4. **IP Filtering**
   - IP whitelisting
   - IP blacklisting
   - Network range support (CIDR)
   - Whitelist-only mode

5. **Security Logging**
   - Attack attempt logging
   - Access denial logging
   - Validation failure logging
   - Debug-level security checks

---

## Threat Model

### Threats Addressed

| Threat | Mitigation | Status |
|--------|------------|--------|
| **Denial of Service (DoS)** | Rate limiting, payload size limits | ✅ Implemented |
| **Path Traversal** | Path validation, blocked patterns | ✅ Implemented |
| **SQL Injection** | Pattern detection, validation | ✅ Implemented |
| **Command Injection** | Shell metacharacter detection | ✅ Implemented |
| **Memory Exhaustion** | Payload size limits, string length limits | ✅ Implemented |
| **Unauthorized Access** | IP filtering, authentication ready | ✅ Implemented |
| **Malformed Input** | Type validation, sanitization | ✅ Implemented |
| **Brute Force** | Rate limiting per client | ✅ Implemented |

### Threats Not Addressed

- **Network-Level DDoS**: Use external DDoS protection
- **TLS/SSL**: Implement TLS termination at proxy level
- **Authentication**: Not implemented (add via middleware)
- **Authorization**: Not implemented (add via middleware)

---

## Security Configuration

### Full Configuration Example

```yaml
security:
  # Rate Limiting
  rate_limit:
    enabled: true
    requests_per_second: 100.0
    burst_size: 200
    per_client: true

  # Input Validation
  validation:
    enabled: true
    max_payload_size: 10485760  # 10 MB
    max_string_length: 10000
    max_path_length: 4096
    sanitize_strings: true
    check_sql_injection: true
    check_command_injection: true

    allowed_path_patterns:
      - ".*"  # Allow all paths (customize for production)

    blocked_path_patterns:
      - '\\.\\.\/'  # Path traversal
      - '~'  # Home directory
      - '/etc/'  # System files
      - '/proc/'  # Process info
      - '/sys/'  # System info

    sql_injection_patterns:
      - '(\bUNION\b.*\bSELECT\b)'
      - '(\bSELECT\b.*\bFROM\b)'
      - '(\bINSERT\b.*\bINTO\b)'
      - '(\bUPDATE\b.*\bSET\b)'
      - '(\bDELETE\b.*\bFROM\b)'
      - '(\bDROP\b.*\bTABLE\b)'
      - '(--|\#|\/\*|\*\/)'  # SQL comments

    command_injection_patterns:
      - '[\;\|\&\$\`]'  # Shell metacharacters
      - '\$\('  # Command substitution
      - '\`'  # Backticks

  # IP Filtering
  ip_filter:
    enabled: false  # Enable for production
    whitelist_mode: false
    whitelist:
      - "127.0.0.1"
      - "192.168.1.0/24"
    blacklist:
      - "10.0.0.0/8"  # Example: block private network
```

### Python Configuration

```python
from lib.security import (
    SecurityConfig,
    SecurityManager,
    RateLimitConfig,
    ValidationConfig,
    IPFilterConfig,
)

# Create security configuration
security_config = SecurityConfig(
    rate_limit=RateLimitConfig(
        enabled=True,
        requests_per_second=100.0,
        burst_size=200,
        per_client=True
    ),
    validation=ValidationConfig(
        enabled=True,
        max_payload_size=10 * 1024 * 1024,
        check_sql_injection=True,
        check_command_injection=True
    ),
    ip_filter=IPFilterConfig(
        enabled=True,
        whitelist={"127.0.0.1", "192.168.1.0/24"},
        whitelist_mode=False
    )
)

# Create security manager
security_manager = SecurityManager(security_config)

# Use in request handling
async def handle_request(endpoint, data, client_ip):
    try:
        # Perform security checks
        validated_data = await security_manager.check_request(
            endpoint=endpoint,
            data=data,
            client_id=client_ip,
            client_ip=client_ip
        )

        # Process validated data
        return process_request(endpoint, validated_data)

    except SecurityViolation as e:
        logger.error(f"Security violation: {e}")
        return {"status": "error", "message": "Security check failed"}
```

---

## Input Validation

### String Validation

All string inputs are validated for:
- **Length**: Must not exceed `max_string_length` (default: 10,000 characters)
- **Type**: Must be valid string type
- **Control Characters**: Removed if `sanitize_strings` enabled
- **Injection Patterns**: Checked for SQL and command injection

```python
# Example: Validate user input
from lib.security import InputValidator, ValidationConfig

validator = InputValidator(ValidationConfig())

try:
    safe_input = validator.validate_string(user_input, "user_field")
    # Use safe_input
except InvalidInput as e:
    logger.error(f"Validation failed: {e}")
```

### Integer Validation

```python
# Validate with range constraints
validated_id = validator.validate_integer(
    value=provider_id,
    field_name="provider_id",
    min_value=0,
    max_value=1000
)
```

### Path Validation

Path validation includes:
- Length limits
- Blocked pattern checking (e.g., `../`, `/etc/`)
- Allowed pattern matching
- Path resolution and traversal detection

```python
# Validate file path
try:
    safe_path = validator.validate_path(user_path)
    # safe_path is a Path object
except InvalidInput:
    # Reject malicious path
    pass
```

### Hexadecimal Validation

```python
# Validate hex strings
hex_value = validator.validate_hex_string(user_hex, "pattern")
```

---

## Rate Limiting

### Token Bucket Algorithm

The rate limiter uses the token bucket algorithm:
- **Tokens**: Represent allowed requests
- **Refill Rate**: Tokens added per second (`requests_per_second`)
- **Capacity**: Maximum burst size (`burst_size`)

### Global vs Per-Client Limits

```python
# Global: All clients share the limit
# Per-Client: Each client (IP) has separate limit (10% of global)

rate_config = RateLimitConfig(
    requests_per_second=100.0,  # Global: 100 req/s
    burst_size=200,              # Can burst to 200 requests
    per_client=True              # Also limit per client (10 req/s each)
)
```

### Rate Limit Behavior

When rate limit is exceeded:
1. `RateLimitExceeded` exception is raised
2. Request is rejected
3. Event is logged
4. Client must wait before retrying

### Automatic Cleanup

Old client buckets are automatically cleaned up after 5 minutes of inactivity to prevent memory leaks.

---

## IP Filtering

### Whitelist Mode

In whitelist mode, **only** IP addresses in the whitelist are allowed:

```python
ip_config = IPFilterConfig(
    enabled=True,
    whitelist={"192.168.1.0/24", "10.0.0.5"},
    whitelist_mode=True  # Only whitelist IPs allowed
)
```

### Blacklist Mode

In blacklist mode, all IPs are allowed except those in the blacklist:

```python
ip_config = IPFilterConfig(
    enabled=True,
    blacklist={"203.0.113.0/24"},  # Block specific IPs
    whitelist_mode=False
)
```

### Mixed Mode

Combine whitelist and blacklist:
- Blacklist is checked first
- Then whitelist is checked (if not empty, acts as additional allowed IPs)

### Network Ranges (CIDR)

Both IPv4 and IPv6 networks are supported:

```python
whitelist = {
    "192.168.1.0/24",        # IPv4 network
    "2001:db8::/32",         # IPv6 network
    "127.0.0.1",             # Single IPv4
    "::1"                    # Single IPv6 (localhost)
}
```

---

## Attack Prevention

### SQL Injection

Detected patterns include:
- `UNION SELECT`
- `SELECT ... FROM`
- `INSERT INTO`
- `UPDATE ... SET`
- `DELETE FROM`
- `DROP TABLE`
- SQL comments (`--`, `#`, `/*`, `*/`)
- Boolean conditions (`OR`, `AND` with `=`)

**Example Detection:**
```
Input: "admin' OR '1'='1"
Result: InvalidInput exception raised
Log: "SQL injection attempt detected"
```

### Command Injection

Detected patterns include:
- Shell metacharacters (`;`, `|`, `&`, `$`, `` ` ``)
- Command substitution (`$(...)`)
- Backticks
- Device redirection (`> /dev/...`)

**Example Detection:**
```
Input: "test; rm -rf /"
Result: InvalidInput exception raised
Log: "Command injection attempt detected"
```

### Path Traversal

Blocked patterns:
- `../` (directory traversal)
- `~` (home directory expansion)
- `/etc/` (system files)
- `/proc/` (process information)
- `/sys/` (system information)

**Example Detection:**
```
Input: "../../etc/passwd"
Result: InvalidInput exception raised
```

### Payload Size Attacks

All payloads are checked against `max_payload_size` (default: 10 MB):

```python
# Automatic size checking
validator.validate_payload_size(large_data)
# Raises PayloadTooLarge if too big
```

---

## Security Best Practices

### Production Deployment

1. **Enable All Security Features**
   ```python
   security_config = SecurityConfig(
       rate_limit=RateLimitConfig(enabled=True, ...),
       validation=ValidationConfig(enabled=True, ...),
       ip_filter=IPFilterConfig(enabled=True, ...)
   )
   ```

2. **Configure IP Filtering**
   - Use whitelist mode for maximum security
   - Limit to known client IPs/networks
   - Regularly review and update lists

3. **Adjust Rate Limits**
   - Set based on expected traffic patterns
   - Monitor rate limit violations
   - Adjust `requests_per_second` as needed

4. **Customize Path Patterns**
   - Restrict `allowed_path_patterns` to needed directories
   - Add application-specific blocked patterns
   - Use absolute paths when possible

5. **Enable Security Logging**
   ```python
   import logging
   logging.getLogger('lib.security').setLevel(logging.WARNING)
   ```

6. **Monitor Security Events**
   - Set up alerts for `SecurityViolation` exceptions
   - Track rate limit violations
   - Monitor IP filter rejections

### Defense in Depth

Don't rely on a single security mechanism:
- Use rate limiting **AND** IP filtering
- Enable all validation checks
- Add application-level authentication
- Use TLS for network encryption
- Run behind a reverse proxy (nginx, HAProxy)
- Implement request signing/verification

### Regular Updates

- Review security logs weekly
- Update blocked patterns based on attacks
- Adjust rate limits based on traffic
- Update IP whitelist/blacklist as needed
- Keep dependencies up to date

---

## Security Auditing

### Logging Levels

- **ERROR**: Critical security failures
- **WARNING**: Attack attempts, access denials
- **INFO**: Security configuration changes
- **DEBUG**: All security checks (verbose)

### Audit Log Example

```
2025-11-14 12:34:56 WARNING SQL injection attempt detected in user_input: (\bUNION\b.*\bSELECT\b)
2025-11-14 12:35:01 WARNING IP 203.0.113.5 is blacklisted
2025-11-14 12:35:15 WARNING Rate limit exceeded for client 192.168.1.100
2025-11-14 12:35:20 DEBUG Security check passed for endpoint=file/read, client_id=192.168.1.50, ip=192.168.1.50
```

### Monitoring Metrics

Track these security metrics:
- `security_violations_total` - Total security violations
- `rate_limit_exceeded_total` - Rate limit violations
- `ip_filter_rejections_total` - IP filter rejections
- `input_validation_failures_total` - Validation failures
- `sql_injection_attempts_total` - SQL injection attempts
- `command_injection_attempts_total` - Command injection attempts

---

## Incident Response

### When Attack is Detected

1. **Log the Incident**
   - Capture full request details
   - Record client IP and identifier
   - Log attack pattern matched

2. **Block the Attacker**
   - Add IP to blacklist
   - Implement temporary ban
   - Escalate to infrastructure team

3. **Review and Adjust**
   - Analyze attack pattern
   - Update detection rules if needed
   - Review similar requests in logs

4. **Notify Stakeholders**
   - Security team notification
   - Incident report creation
   - Update security documentation

### Common Attack Scenarios

#### Scenario 1: Rate Limit Abuse
```
Symptom: Multiple RateLimitExceeded from same IP
Action: Add IP to blacklist, investigate source
```

#### Scenario 2: SQL Injection Attempts
```
Symptom: Multiple SQL injection warnings
Action: Review endpoint implementation, block IP, update patterns
```

#### Scenario 3: Path Traversal Attempts
```
Symptom: InvalidInput for path validation
Action: Review path handling, block client, check for data access
```

---

## Security Checklist

### Pre-Production

- [ ] Enable all security features
- [ ] Configure IP filtering (whitelist mode recommended)
- [ ] Set appropriate rate limits
- [ ] Customize path validation patterns
- [ ] Enable security logging
- [ ] Set up monitoring and alerts
- [ ] Test all security mechanisms
- [ ] Review security configuration
- [ ] Document security procedures
- [ ] Train team on security features

### Ongoing

- [ ] Review security logs weekly
- [ ] Update IP whitelist/blacklist
- [ ] Monitor rate limit violations
- [ ] Check for new attack patterns
- [ ] Update detection rules
- [ ] Review access patterns
- [ ] Test security mechanisms quarterly
- [ ] Update documentation

---

## Additional Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework

---

**Last Updated**: 2025-11-14
**Version**: 1.0
**Author**: ImHex MCP Security Team
