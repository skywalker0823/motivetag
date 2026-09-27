"""Versioned static URLs, so browsers and Cloudflare can cache assets for a year.

Every asset URL carries a hash of the file (`/css/base.css?v=1a2b3c4d5e`); a new
release changes the hash and therefore the URL, so a cached old file is never used.
Browser modules import each other by plain relative paths, which an import map
rewrites to their versioned URLs; `modulepreload` links let the browser fetch a
page's whole module tree at once instead of discovering it import by import.
"""

import hashlib
import json
import os
import re

from flask import request

IMMUTABLE = "public, max-age=31536000, immutable"
IMPORT = re.compile(r"""(?:import|export)\s[^"']*?from\s*["']([^"']+)["']""")


class Assets:
    def __init__(self, static_folder, reload):
        self.root = os.path.abspath(static_folder)
        self.reload = reload  # development: notice edited files without a restart
        self._hashes = {}

    def version(self, path):
        full = os.path.join(self.root, path.lstrip("/"))
        try:
            stamp = os.path.getmtime(full) if self.reload else None
        except OSError:
            return None
        cached = self._hashes.get(path)
        if cached and cached[0] == stamp:
            return cached[1]
        try:
            with open(full, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()[:10]
        except OSError:
            return None
        self._hashes[path] = (stamp, digest)
        return digest

    def url(self, path):
        digest = self.version(path)
        return f"{path}?v={digest}" if digest else path

    def modules(self):
        for folder in ("js", "vendor"):
            for dirpath, _, files in os.walk(os.path.join(self.root, folder)):
                for name in files:
                    if name.endswith(".js"):
                        rel = os.path.relpath(os.path.join(dirpath, name), self.root)
                        yield "/" + rel.replace(os.sep, "/")

    def import_map(self):
        return json.dumps({"imports": {path: self.url(path) for path in sorted(self.modules())}})

    def module_tree(self, entry):
        """`entry` and every module it imports, directly or not."""
        seen, todo = [], [entry]
        while todo:
            path = todo.pop()
            if path in seen:
                continue
            seen.append(path)
            try:
                with open(os.path.join(self.root, path.lstrip("/")), encoding="utf-8") as f:
                    source = f.read()
            except OSError:
                continue
            for spec in IMPORT.findall(source):
                if spec.startswith("/"):
                    todo.append(spec)
                elif spec.startswith("."):
                    base = os.path.dirname(path)
                    todo.append(os.path.normpath(os.path.join(base, spec)).replace(os.sep, "/"))
        return seen

    def preload(self, entry):
        return [self.url(path) for path in self.module_tree(entry)]


def init_assets(app):
    assets = Assets(app.static_folder, reload=app.config.get("TEMPLATES_AUTO_RELOAD", False))
    app.jinja_env.globals.update(
        asset=assets.url, import_map=assets.import_map, preload=assets.preload
    )

    @app.after_request
    def cache_versioned_assets(response):
        if request.args.get("v") and response.status_code == 200 and request.endpoint == "static":
            response.headers["Cache-Control"] = IMMUTABLE
        return response

    return assets
