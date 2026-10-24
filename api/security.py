"""Content Security Policy: what a page of ours may load and run.

The browser runs only our own scripts, the two outside ones the landing page needs
(Google Analytics, Cloudflare Turnstile), and inline scripts carrying this response's
nonce (`csp_nonce()` in templates). Anything injected into a page (a stored XSS
that got past the templates' escaping) has no nonce and does not run.

nginx adds the other security headers (deploy/nginx.conf); this one lives here
because the nonce changes with every response.
"""

import secrets

from flask import g, request

# Pictures and uploads go to and come from the image bucket (presigned S3 URLs).
S3 = "https://*.amazonaws.com"
ANALYTICS = (
    "https://www.googletagmanager.com https://*.google-analytics.com https://*.analytics.google.com"
)
TURNSTILE = "https://challenges.cloudflare.com"


def policy(nonce):
    return "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://www.googletagmanager.com {TURNSTILE}",
            # Styles set from scripts (element.style) are not limited by CSP; this
            # covers the style attributes Turnstile's widget adds.
            "style-src 'self' 'unsafe-inline'",
            f"img-src 'self' data: blob: {S3} {ANALYTICS}",
            # Socket.IO's WebSocket: 'self' covers wss: in current browsers, older
            # Safari needs it spelled out.
            f"connect-src 'self' wss://{request.host} {S3} {ANALYTICS} {TURNSTILE}",
            f"frame-src {TURNSTILE}",
            "font-src 'self'",
            "worker-src 'self'",
            "manifest-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


def csp_nonce():
    if "csp_nonce" not in g:
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def init_security(app):
    app.jinja_env.globals["csp_nonce"] = csp_nonce

    @app.after_request
    def add_csp(response):
        if response.mimetype == "text/html":
            response.headers["Content-Security-Policy"] = policy(csp_nonce())
        return response
