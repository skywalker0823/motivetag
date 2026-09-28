from flask import request


def public_base_url():
    """https://motivetag.com in production: nginx talks plain HTTP to the app and says
    in X-Forwarded-Proto that the visitor used HTTPS."""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    return f"{scheme}://{request.host}"
