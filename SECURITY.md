# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in AI Data Agent, please report it responsibly.

### How to Report

**Please do NOT open a public GitHub Issue for security vulnerabilities.**

Instead, please send an email to: **security@ai-data-agent.dev** (placeholder — update with real contact)

Include the following information:

1. **Description** — Clear description of the vulnerability
2. **Impact** — What could an attacker do if they exploited this?
3. **Steps to Reproduce** — Detailed steps to trigger the vulnerability
4. **Affected Versions** — Which versions are affected?
5. **Mitigation** — Any workarounds you've identified

### Response Timeline

- **24 hours** — Acknowledgment of receipt
- **72 hours** — Initial assessment and severity rating
- **7 days** — Fix plan communicated (for critical/high severity)
- **30 days** — Fix released (for critical/high severity)

We will keep you informed throughout the process and credit you in the security advisory (unless you prefer to remain anonymous).

## Security Measures

AI Data Agent implements the following security measures:

- **SQL Injection Prevention** — All SQL queries use SQLAlchemy parameterized execution
- **Code Sandboxing** — Python execution uses RestrictedPython to limit dangerous operations
- **Data Masking** — Column-level permission system automatically masks sensitive fields
- **Row-Level Filtering** — Automatic `WHERE` clause injection based on user department/role
- **JWT Authentication** — Secure token-based authentication with configurable expiration
- **API Config Encryption** — Stored API authentication credentials are encrypted at rest
- **Approval Audit Trail** — All approval actions are logged with user ID and timestamp

## Known Limitations

- The Python execution sandbox relies on RestrictedPython; determined attackers with specialized knowledge may find bypasses. Use in trusted environments.
- API authentication credentials are encrypted but the encryption key must be properly secured in your deployment environment.
