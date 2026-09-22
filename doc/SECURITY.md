# 🔐 BuildBot Ultimate - Security Documentation

## Security Overview

BuildBot Ultimate implements multiple layers of security to protect against common vulnerabilities while maintaining usability. This document covers security for all 10 innovative features.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Layer 1: Input Validation                                             │
│   ─────────────────────────                                             │
│   • Repository URL allowlist                                            │
│   • Branch name pattern validation                                      │
│   • Input sanitization                                                  │
│   • Length limits                                                       │
│   • Shortcut validation (!h, !j, etc.)                                 │
│                                                                         │
│   Layer 2: Authentication                                               │
│   ────────────────────────                                              │
│   • Jenkins API tokens (not passwords)                                  │
│   • LLM API key management                                              │
│   • Credentials stored in .env (not in code)                           │
│   • .env excluded from Git                                             │
│                                                                         │
│   Layer 3: Authorization                                                │
│   ──────────────────────                                                │
│   • Repository allowlist                                                │
│   • Job name validation                                                 │
│   • Collaboration role-based access                                     │
│   • Scheduler permission controls                                       │
│   • No arbitrary code execution                                        │
│                                                                         │
│   Layer 4: Secure Communication                                         │
│   ─────────────────────────────                                         │
│   • HTTPS recommended for non-localhost                                │
│   • TLS for LLM API calls (with SSL bypass option)                     │
│   • Webhook URL validation                                             │
│   • No sensitive data in logs                                          │
│                                                                         │
│   Layer 5: Feature-Specific Security                                    │
│   ──────────────────────────────────                                    │
│   • Scheduler: Rate limiting, max schedules                            │
│   • Collaboration: @mention validation, XSS prevention                 │
│   • Rollback: Confirmation required, audit trail                       │
│   • Templates: Sanitized parameters                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Credential Management

### ✅ What We Do

| Practice | Implementation |
|----------|----------------|
| No hardcoded credentials | All secrets in `.env` file |
| API tokens over passwords | Jenkins API tokens only |
| Gitignore secrets | `.env` in `.gitignore` |
| Masked logging | Tokens never printed/logged |
| SSL bypass documented | `LLM_VERIFY_SSL=false` for expired certs |

### Configuration File Security

```env
# ❌ NEVER DO THIS (hardcoded in code)
api_token = "abc123"

# ✅ CORRECT (in .env file, loaded at runtime)
JENKINS_API_TOKEN=abc123
LLM_API_KEY=your-key-here
LLM_VERIFY_SSL=false  # Only for expired certs!
```

### .gitignore Rules

```
# Secrets - NEVER commit
.env
*.pem
*.key
*_TOKEN*
*_SECRET*
credentials.json
```

---

## 2. Input Validation

### Repository URL Validation

**Threat:** Attacker could inject malicious URLs or trigger builds on unauthorized repositories.

**Protection:**
```python
# Allowlist-based validation
ALLOWED_REPOS = ["github.com", "github.com/your-org"]

def _validate_repo_url(url: str) -> tuple[bool, str | None]:
    # Block suspicious characters
    if '..' in url or ';' in url or '|' in url:
        return False, "Invalid characters"
    
    # Check against allowlist
    for allowed in allowed_repos:
        if allowed.lower() in url.lower():
            return True, None
    
    return False, "Not in allowed list"
```

### Branch Name Validation

**Threat:** Command injection via malicious branch names.

**Protection:**
```python
# Dangerous characters that could enable injection
BLOCKED_CHARS = [';', '|', '`', '$', '(', ')', '{', '}', '<', '>', '&']

# Valid pattern: alphanumeric, /, -, _, .
VALID_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9/_.-]*[a-zA-Z0-9]$'

def _validate_branch_name(branch: str) -> bool:
    for char in BLOCKED_CHARS:
        if char in branch:
            return False
    return bool(re.match(VALID_PATTERN, branch))
```

### Shortcut Validation

**Threat:** Malicious shortcut injection.

**Protection:**
```python
# Only predefined shortcuts allowed
VALID_SHORTCUTS = {
    '!h': 'help',
    '!j': 'list jobs',
    '!s': 'show status',
    '!r': 'rebuild last build',
    '!a': 'show analytics',
    '!t': 'show templates',
    '!f': 'show favorites',
}

def _expand_shortcuts(text: str) -> str:
    if text.strip() in VALID_SHORTCUTS:
        return VALID_SHORTCUTS[text.strip()]
    return text  # Return unchanged if not a valid shortcut
```

---

## 3. Feature-Specific Security

### 📊 Analytics Engine Security

**Threats:**
- Data manipulation
- Information disclosure

**Protections:**
```python
# Analytics data is read-only from Jenkins
# No user input directly affects analytics calculations
# Cached data expires after configurable period

class AnalyticsEngine:
    def __init__(self):
        self._cache_ttl = 300  # 5 minutes
        self._max_history = 1000  # Limit stored builds
    
    def get_metrics(self, job_name: str) -> dict:
        # Sanitize job name before query
        job_name = self._sanitize_job_name(job_name)
        # Read-only Jenkins API calls
        return self._fetch_from_cache_or_jenkins(job_name)
```

### ⏰ Scheduler Security

**Threats:**
- Denial of Service (too many schedules)
- Unauthorized schedule creation
- Schedule injection

**Protections:**
```python
class BuildScheduler:
    MAX_SCHEDULES = 50  # Per user limit
    MIN_INTERVAL_MINUTES = 5  # Prevent spam
    
    def create_schedule(self, schedule: dict) -> tuple[bool, str]:
        # Rate limiting
        if len(self.schedules) >= self.MAX_SCHEDULES:
            return False, "Maximum schedules reached"
        
        # Validate interval
        if schedule.get('interval_minutes', 0) < self.MIN_INTERVAL_MINUTES:
            return False, f"Minimum interval is {self.MIN_INTERVAL_MINUTES} minutes"
        
        # Validate job exists
        if not self._job_exists(schedule['job_name']):
            return False, "Job not found"
        
        # Sanitize cron expression
        if schedule.get('cron'):
            if not self._validate_cron(schedule['cron']):
                return False, "Invalid cron expression"
        
        return True, "Schedule created"
    
    def _validate_cron(self, cron: str) -> bool:
        # Only allow safe cron patterns
        # Block shell commands in cron
        dangerous = [';', '|', '`', '$', '(', ')']
        return not any(c in cron for c in dangerous)
```

### 👥 Collaboration Security

**Threats:**
- XSS via comments
- Unauthorized @mentions
- Impersonation

**Protections:**
```python
import html

class CollaborationHub:
    def add_comment(self, build_id: str, author: str, text: str) -> dict:
        # XSS prevention - escape HTML
        safe_text = html.escape(text)
        
        # Validate author exists
        if not self._user_exists(author):
            raise ValueError("Invalid author")
        
        # Extract and validate mentions
        mentions = self._extract_mentions(safe_text)
        valid_mentions = [m for m in mentions if self._user_exists(m)]
        
        # Length limits
        if len(safe_text) > 1000:
            safe_text = safe_text[:1000]
        
        return {
            'text': safe_text,
            'mentions': valid_mentions,
            'author': author,
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_mentions(self, text: str) -> list[str]:
        # Only alphanumeric usernames allowed
        pattern = r'@([a-zA-Z0-9_]+)'
        return re.findall(pattern, text)
```

### 🔄 Rollback Security

**Threats:**
- Unauthorized rollbacks
- Rolling back to malicious builds
- Audit trail tampering

**Protections:**
```python
class RollbackManager:
    def suggest_rollback(self, failed_build: int) -> dict:
        # Only suggest from verified successful builds
        candidates = self._get_successful_builds_before(failed_build)
        
        # Validate each candidate
        safe_candidates = []
        for build in candidates:
            if self._verify_build_integrity(build):
                safe_candidates.append(build)
        
        return {
            'candidates': safe_candidates[:5],  # Limit suggestions
            'requires_confirmation': True,
            'audit_id': self._create_audit_entry()
        }
    
    def execute_rollback(self, target_build: int, confirmed: bool) -> tuple[bool, str]:
        if not confirmed:
            return False, "Rollback requires explicit confirmation"
        
        # Log the rollback action
        self._audit_log({
            'action': 'rollback',
            'target': target_build,
            'timestamp': datetime.now().isoformat(),
            'user': self._current_user()
        })
        
        # Rollback is just rebuilding a previous good build
        # No destructive operations
        return self._trigger_rebuild(target_build)
```

### 📋 Templates Security

**Threats:**
- Parameter injection
- Template manipulation

**Protections:**
```python
class TemplateManager:
    MAX_TEMPLATES = 20
    
    def save_template(self, template: dict) -> tuple[bool, str]:
        # Limit number of templates
        if len(self.templates) >= self.MAX_TEMPLATES:
            return False, "Maximum templates reached"
        
        # Sanitize all fields
        safe_template = {
            'name': self._sanitize_name(template.get('name', '')),
            'job_name': self._sanitize_job_name(template.get('job_name', '')),
            'repo_url': self._sanitize_url(template.get('repo_url', '')),
            'branch': self._sanitize_branch(template.get('branch', '')),
            'parameters': self._sanitize_parameters(template.get('parameters', {}))
        }
        
        # Validate job exists
        if not self._job_exists(safe_template['job_name']):
            return False, "Job not found"
        
        return True, "Template saved"
    
    def _sanitize_parameters(self, params: dict) -> dict:
        # Only allow string values, no nested objects
        return {
            str(k)[:50]: str(v)[:200] 
            for k, v in params.items() 
            if isinstance(k, str) and isinstance(v, (str, int, bool))
        }
```

---

## 4. SSL/TLS Security

### LLM API SSL Bypass

**Why:** The Exterro LLM server has an expired SSL certificate.

**Configuration:**
```env
# Only use when certificate is expired/invalid
LLM_VERIFY_SSL=false
```

**Implementation:**
```python
import httpx

def _get_http_client() -> httpx.Client:
    verify_ssl = settings.llm_verify_ssl
    
    if not verify_ssl:
        logger.warning("⚠️ SSL verification disabled for LLM API")
    
    return httpx.Client(
        verify=verify_ssl,
        timeout=30.0
    )
```

**Risks:**
- Man-in-the-middle attacks possible
- Use only in controlled/internal networks
- Document the decision

**Mitigation:**
- Only bypass SSL for specific endpoints
- Monitor for certificate renewal
- Use VPN when possible

---

## 5. Jenkins Security

### API Token Usage

```
┌─────────────────────────────────────────────────────────────────────────┐
│                JENKINS SECURITY CHECKLIST                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ☐ Enable CSRF protection                                              │
│   ☐ Use API tokens (not passwords)                                      │
│   ☐ Restrict job permissions                                            │
│   ☐ Enable audit logging                                                │
│   ☐ Use HTTPS for non-localhost                                         │
│   ☐ Limit network access (localhost only for dev)                       │
│   ☐ Keep Jenkins updated                                                │
│   ☐ Configure job-level permissions for BuildBot                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Logging Security

### What We Log

```
✅ Build requests (without full URLs)
✅ Build status changes
✅ Schedule executions
✅ Collaboration actions (anonymized)
✅ Security warnings
✅ Error messages
```

### What We DON'T Log

```
❌ API tokens
❌ Passwords
❌ Full repository URLs (only domain)
❌ Email addresses
❌ Webhook URLs
❌ User comments (full text)
❌ LLM responses (may contain sensitive data)
```

### Example Log Output

```
INFO: Build requested for github.com/***
INFO: Schedule 'nightly-build' triggered
INFO: Build #143 completed: SUCCESS
INFO: @mention notification sent to 2 users
WARN: SECURITY - Repository not in allowlist: evil.com
WARN: SECURITY - SSL verification disabled for LLM
```

---

## 7. Rate Limiting

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RATE LIMITS                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Feature                  Limit                  Reason                │
│   ───────                  ─────                  ──────                │
│                                                                         │
│   Builds per minute        10                     Prevent Jenkins DoS   │
│   LLM requests/minute      30                     API cost control      │
│   Schedules per user       50                     Resource management   │
│   Comments per build       100                    Storage limits        │
│   Templates per user       20                     Storage limits        │
│   Favorites per user       50                     UI performance        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Security Checklist for Deployment

### Before Going Live

- [ ] Change all default passwords
- [ ] Generate unique API tokens
- [ ] Configure `ALLOWED_REPOS` restrictively
- [ ] Enable HTTPS for Jenkins (if not localhost)
- [ ] Review and restrict Jenkins permissions
- [ ] Set up firewall rules
- [ ] Enable Jenkins audit logging
- [ ] Test with malicious inputs
- [ ] Verify SSL settings are intentional
- [ ] Review scheduler permissions
- [ ] Test collaboration @mention validation
- [ ] Verify rollback confirmation flow

### Regular Maintenance

- [ ] Rotate API tokens quarterly
- [ ] Review access logs monthly
- [ ] Update dependencies weekly
- [ ] Security scan monthly
- [ ] Backup configurations
- [ ] Review scheduled jobs
- [ ] Audit collaboration access
- [ ] Check for certificate renewals

---

## 9. Threat Model Summary

| Feature | Threat | Mitigation | Severity |
|---------|--------|------------|----------|
| Input | Command injection | Validation, allowlist | High |
| LLM | Prompt injection | Structured output only | Medium |
| Scheduler | DoS via many schedules | Rate limits | Medium |
| Collaboration | XSS in comments | HTML escaping | High |
| Rollback | Unauthorized rollback | Confirmation required | High |
| Templates | Parameter injection | Sanitization | Medium |
| Analytics | Data manipulation | Read-only access | Low |
| Shortcuts | Injection | Predefined only | Low |

---

## 10. Security Configuration Reference

### .env Security Settings

```env
# SECURITY: Only allow these repositories
ALLOWED_REPOS=github.com/your-org

# SECURITY: Limit artifact storage location
ARTIFACTS_SHARED_PATH=D:\shared\builds

# SECURITY: Reasonable poll interval (prevent DoS)
POLL_INTERVAL=5

# SECURITY: Max build wait time (1 hour)
MAX_BUILD_WAIT_TIME=3600

# SECURITY: SSL verification (disable only if necessary)
LLM_VERIFY_SSL=false

# SECURITY: Rate limits
MAX_SCHEDULES_PER_USER=50
MAX_TEMPLATES_PER_USER=20
MIN_SCHEDULE_INTERVAL_MINUTES=5
```

---

## 11. Incident Response

If you discover a security issue:

1. **DO NOT** create a public issue
2. Document the vulnerability with:
   - Steps to reproduce
   - Affected components
   - Potential impact
3. Report to your security team immediately
4. Disable affected features if critical
5. Wait for fix before disclosure

---

*BuildBot Ultimate Security Documentation v2.0*
*Exterro DevOps AI Challenge - September 2026*
