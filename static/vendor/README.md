# Vendored browser libraries

Served from our own origin so the site does not depend on third-party CDNs.

| File | Package | Source |
|---|---|---|
| `socket.io-4.8.4.esm.min.js` | socket.io-client 4.8.4 (MIT) | `node_modules/socket.io-client/dist/socket.io.esm.min.js`, source-map comment removed |

To upgrade: `npm pack socket.io-client@<version>`, copy the same file, rename it
with the new version and update the import in `static/js/lib/socket.js`.
