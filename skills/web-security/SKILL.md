---
name: web-security
description: Use when writing or reviewing web security - CSP, XSS, security headers, third-party scripts, and form abuse. Triggers on .css/.svelte/.ts/.tsx/.jsx/.html/.vue file edits, "csp", "xss", "security headers", "sri", "csrf", "web security".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Web Security

Pick a side. These are the rulings, not a tutorial.

## Content Security Policy

Always ship a production CSP, and use a **per-request nonce** for scripts — never `'unsafe-inline'`.

```text
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{RANDOM}' https://cdn.jsdelivr.net;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  img-src 'self' data: https:;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://*.example.com;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
```

Adjust the origins to the project. **Do not cargo-cult this block unchanged.**

## Headers

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## XSS

- Never inject unsanitized HTML.
- Avoid `innerHTML` / `{@html}` unless the value is sanitized first.
- Escape dynamic template values.
- Sanitize user HTML with a vetted local sanitizer, and only when there is no alternative.

## Third-party scripts

Load asynchronously. Use SRI when serving from a CDN. Audit quarterly. Self-host critical dependencies where practical.

## Forms

CSRF protection on every state-changing form. Rate-limit submission endpoints. Validate client **and** server side. Prefer honeypots or light anti-abuse controls over a heavy-handed CAPTCHA default.
