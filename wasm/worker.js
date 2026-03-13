/*
 * Service worker that runs Django/Wagtail inside Pyodide (Python in WASM).
 *
 * All fetch requests from the page are intercepted here and routed through
 * Django's WSGI stack via WebTest's TestApp, so there is no real HTTP server.
 */

const PYODIDE_VERSION = "0.29.3";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full`;

importScripts(`${PYODIDE_CDN}/pyodide.js`);
importScripts(
  "https://cdn.jsdelivr.net/npm/xhr-shim@0.1.3/src/index.min.js"
);

// Pyodide needs XMLHttpRequest which is not natively available in service workers.
self.XMLHttpRequest = self.XMLHttpRequestShim;

let pyodide = null;
let loaded = false;

// In-memory cookie jar. Service workers cannot read cookies from intercepted
// requests, so we capture Set-Cookie response headers and replay them.
const cookies = {};

// ── Helpers ──────────────────────────────────────────────────────────────────

function broadcast(msg) {
  console.log("[wasm worker]", msg.message || JSON.stringify(msg));
  self.clients
    .matchAll({ type: "window", includeUncontrolled: true })
    .then((clients) => {
      clients.forEach((c) => c.postMessage(msg));
    });
}

function buildCookieHeader() {
  return Object.entries(cookies)
    .map(([k, v]) => `${k}=${v}`)
    .join("; ");
}

function captureSetCookies(headerString) {
  if (!headerString) return;
  // May contain multiple cookies separated by commas. Each cookie's attributes
  // are separated by semicolons -- we only care about the name=value part.
  const parts = headerString.split(/,(?=\s*\w+=)/);
  for (const part of parts) {
    const nameValue = part.split(";")[0].trim();
    const eqIdx = nameValue.indexOf("=");
    if (eqIdx > 0) {
      cookies[nameValue.slice(0, eqIdx).trim()] = nameValue.slice(eqIdx + 1);
    }
  }
}

function guessContentType(url, fallback) {
  const ext = url.split("?")[0].split("#")[0].split(".").pop().toLowerCase();
  const map = {
    woff: "font/woff",
    woff2: "font/woff2",
    ttf: "font/ttf",
    otf: "font/otf",
    eot: "application/vnd.ms-fontobject",
    svg: "image/svg+xml",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    gif: "image/gif",
    webp: "image/webp",
    avif: "image/avif",
    ico: "image/x-icon",
    pdf: "application/pdf",
    js: "application/javascript",
    mjs: "application/javascript",
    css: "text/css",
    json: "application/json",
  };
  return map[ext] || fallback;
}

// ── Setup ────────────────────────────────────────────────────────────────────

async function setupPython() {
  try {
    broadcast({ type: "status", message: "Loading Python runtime..." });

    pyodide = await loadPyodide();

    broadcast({ type: "status", message: "Installing packages..." });

    // Pre-load WASM-compiled packages first (Pillow, lxml).
    await pyodide.loadPackage(["micropip", "Pillow", "lxml", "sqlite3"]);
    const micropip = pyodide.pyimport("micropip");

    // Install Wagtail first -- it has strict django-tasks version constraints
    // and must resolve its dependency tree before we add other packages.
    broadcast({ type: "status", message: "Installing Wagtail..." });
    await micropip.install("wagtail>=7.2,<7.3");

    broadcast({ type: "status", message: "Installing extra packages..." });
    await micropip.install([
      "tzdata",
      "webtest",
      "beautifulsoup4",
      "djangorestframework",
      "django-modelcluster",
      "django-taggit",
      "dj-database-url",
      "python-dotenv",
      "wagtail-font-awesome-svg",
      "django-extensions",
    ]);

    // Install the bakerydemo wheel (built with `pip wheel . --no-deps`).
    // Use absolute URL because relative URLs inside Pyodide resolve against
    // its own base, not the service worker's location.
    broadcast({ type: "status", message: "Installing bakerydemo..." });
    const wheelUrl = `${self.location.origin}/wasm/wheel/bakerydemo-0.1.0-py3-none-any.whl`;
    await micropip.install(wheelUrl);

    // Set up persistent filesystem via IDBFS for the database directory.
    broadcast({
      type: "status",
      message: "Setting up persistent storage...",
    });
    pyodide.runPython(`
import os
from pyodide.code import run_js

# Mount an IDBFS-backed directory for the database
_db_dir = "/home/pyodide/wagtail_db"
os.makedirs(_db_dir, exist_ok=True)

run_js("""
  let FS = pyodide.FS;
  try {
    FS.mount(FS.filesystems.IDBFS, {}, '/home/pyodide/wagtail_db');
  } catch (e) {
    // Already mounted
  }
""")

# Sync FROM IndexedDB into the virtual filesystem (populate=true)
import pyodide_js
from pyodide.ffi import run_sync

async def _sync_from_idb():
    from js import Promise
    def _do_sync(resolve, reject):
        from pyodide.code import run_js as _rjs
        _rjs("""
          pyodide.FS.syncfs(true, (err) => {
            if (err) console.error('[wasm] IDBFS sync-from error:', err);
          });
        """)
        resolve(None)
    await Promise.new(_do_sync)

# Synchronous sync-from using Atomics (simpler approach)
from pyodide.code import run_js as _rjs2
_rjs2("""
  pyodide.FS.syncfs(true, (err) => {
    if (err) console.warn('[wasm] IDBFS load error:', err);
    else console.log('[wasm] IDBFS loaded from IndexedDB');
  });
""")
`);

    // Small delay to let IDBFS sync complete
    await new Promise((r) => setTimeout(r, 500));

    // Check if the database already exists (from a previous session)
    const dbExists = pyodide.runPython(`
import os
os.path.exists("/home/pyodide/wagtail_db/db.sqlite3")
`);

    // Run the Python bootstrap script.
    broadcast({
      type: "status",
      message: dbExists
        ? "Loading saved Wagtail data..."
        : "Initializing Wagtail (migrations, data)...",
    });
    const initUrl = `${self.location.origin}/wasm/init.py`;
    const initScript = await (await fetch(initUrl)).text();

    // Tell init.py where the DB is and whether to skip fixture loading
    pyodide.globals.set("_wasm_db_exists", dbExists);
    pyodide.runPython(initScript);

    loaded = true;
    broadcast({ type: "status", message: "ready" });
  } catch (err) {
    console.error("[wasm worker] Setup failed:", err);
    broadcast({
      type: "status",
      message: `Setup failed: ${err.message}`,
    });
    throw err;
  }
}

// ── Request handling ─────────────────────────────────────────────────────────

async function djangoRequest(request) {
  if (!loaded) {
    await setupPython();
  }

  const method = request.method.toLowerCase();
  const url = request.url;

  // Build request headers. Merge any browser-sent cookies with our manual jar
  // (the browser may have cookies if Set-Cookie flowed through on earlier
  // responses, but the jar is the authoritative source in the SW context).
  const reqHeaders = {};
  for (const [key, value] of request.headers.entries()) {
    reqHeaders[key] = value;
  }
  const browserCookies = reqHeaders["cookie"] || "";
  const jarCookies = buildCookieHeader();
  reqHeaders["Cookie"] = jarCookies || browserCookies;
  if (request.referrer) {
    reqHeaders["Referer"] = request.referrer;
  }

  // Read the request body for methods that carry one.
  let bodyBytes = null;
  let contentType = reqHeaders["content-type"] || "";
  if (["post", "put", "patch"].includes(method)) {
    bodyBytes = new Uint8Array(await request.arrayBuffer());
  }

  // Pass data into Python through globals to avoid string-interpolation issues.
  pyodide.globals.set("_req_url", url);
  pyodide.globals.set("_req_method", method);
  pyodide.globals.set("_req_headers", JSON.stringify(reqHeaders));
  pyodide.globals.set("_req_content_type", contentType);

  const hasBody = bodyBytes && bodyBytes.length > 0;
  if (hasBody) {
    pyodide.globals.set("_req_body_js", bodyBytes);
  }
  pyodide.globals.set("_req_has_body", hasBody);

  // Execute the request inside Python via a raw WebOb Request for full
  // control over headers and body bytes (avoids WebTest re-encoding
  // multipart uploads or mangling binary POST data).
  pyodide.runPython(`
import json as _json
from io import BytesIO
from webob import Request as _WebObRequest

_headers_dict = _json.loads(_req_headers)

# Build a raw WSGI environ via WebOb so the body passes through untouched.
_environ = {
    "REQUEST_METHOD": _req_method.upper(),
    "PATH_INFO": _req_url.split("?")[0].replace(_headers_dict.get("origin", ""), "") if "://" in _req_url else _req_url.split("?")[0],
    "QUERY_STRING": _req_url.split("?", 1)[1] if "?" in _req_url else "",
    "SERVER_NAME": _headers_dict.get("host", "localhost").split(":")[0],
    "SERVER_PORT": _headers_dict.get("host", "localhost:1337").split(":")[-1] if ":" in _headers_dict.get("host", "") else "80",
    "SERVER_PROTOCOL": "HTTP/1.1",
    "wsgi.version": (1, 0),
    "wsgi.url_scheme": "http",
    "wsgi.multithread": False,
    "wsgi.multiprocess": False,
    "wsgi.run_once": False,
    "wsgi.input": BytesIO(),
    "wsgi.errors": BytesIO(),
}

# Strip the origin from PATH_INFO if the full URL was passed.
if _environ["PATH_INFO"].startswith("http"):
    from urllib.parse import urlparse as _urlparse
    _parsed = _urlparse(_req_url)
    _environ["PATH_INFO"] = _parsed.path
    _environ["QUERY_STRING"] = _parsed.query

# Map HTTP headers to WSGI environ keys.
for _hk, _hv in _headers_dict.items():
    _key = _hk.upper().replace("-", "_")
    if _key == "CONTENT_TYPE":
        _environ["CONTENT_TYPE"] = _hv
    elif _key == "CONTENT_LENGTH":
        _environ["CONTENT_LENGTH"] = _hv
    else:
        _environ["HTTP_" + _key] = _hv

if _req_has_body:
    _body_bytes = bytes(_req_body_js)
    _environ["wsgi.input"] = BytesIO(_body_bytes)
    _environ["CONTENT_LENGTH"] = str(len(_body_bytes))

_webreq = _WebObRequest(_environ)
_response = app.do_request(_webreq, expect_errors=True)

try:
    _resp_body = _response.text
    _resp_is_binary = False
except UnicodeDecodeError:
    _resp_body = _response.body
    _resp_is_binary = True

# Collect headers. Use headerlist to preserve ALL Set-Cookie entries.
_resp_hdr_dict = {}
_resp_set_cookies = []
for _hname, _hval in _response.headerlist:
    if _hname.lower() == "set-cookie":
        _resp_set_cookies.append(_hval)
    else:
        _resp_hdr_dict[_hname] = _hval

_resp_headers_json = _json.dumps(_resp_hdr_dict)
_resp_set_cookies_json = _json.dumps(_resp_set_cookies)
_resp_status = _response.status_int
`);

  const status = pyodide.globals.get("_resp_status");
  const isBinary = pyodide.globals.get("_resp_is_binary");
  const headersJson = pyodide.globals.get("_resp_headers_json");
  const respHeaders = JSON.parse(headersJson);

  // Capture ALL Set-Cookie headers (there may be multiple -- session, CSRF, messages).
  const setCookiesJson = pyodide.globals.get("_resp_set_cookies_json");
  const setCookies = JSON.parse(setCookiesJson);
  for (const sc of setCookies) {
    captureSetCookies(sc);
  }

  // Handle redirects.
  if (status === 301 || status === 302) {
    let location = respHeaders["Location"];
    if (location && !location.startsWith("http")) {
      const base = new URL(url);
      location = new URL(location, base).href;
    }
    return Response.redirect(location, status);
  }

  // Fix content types that Django/static handlers may get wrong.
  if (
    respHeaders["Content-Type"] === "application/octet-stream" ||
    !respHeaders["Content-Type"]
  ) {
    respHeaders["Content-Type"] = guessContentType(
      url,
      respHeaders["Content-Type"] || "application/octet-stream"
    );
  }

  let body;
  if (isBinary) {
    const pyBody = pyodide.globals.get("_resp_body");
    body = new Uint8Array(pyBody.toJs());
    pyBody.destroy();
  } else {
    body = pyodide.globals.get("_resp_body");
  }

  // Build a proper Headers object so we can include multiple Set-Cookie
  // entries (a plain object would deduplicate them).
  const outHeaders = new Headers();
  for (const [k, v] of Object.entries(respHeaders)) {
    if (k.toLowerCase() !== "set-cookie") {
      outHeaders.set(k, v);
    }
  }
  // Append each Set-Cookie individually so the browser stores session,
  // CSRF, and messages cookies. This also makes document.cookie work,
  // which Wagtail's JS relies on for X-CSRFToken AJAX headers.
  for (const sc of setCookies) {
    outHeaders.append("Set-Cookie", sc);
  }

  // Sync database to IndexedDB after write operations.
  if (["post", "put", "patch", "delete"].includes(method)) {
    syncDatabaseToIDB();
  }

  return new Response(body, {
    status: status,
    headers: outHeaders,
  });
}

let syncTimeout = null;
function syncDatabaseToIDB() {
  // Debounce: sync 500ms after the last write operation.
  clearTimeout(syncTimeout);
  syncTimeout = setTimeout(() => {
    try {
      pyodide.runPython(`
from pyodide.code import run_js as _rjs_sync
_rjs_sync("""
  pyodide.FS.syncfs(false, (err) => {
    if (err) console.warn('[wasm] IDBFS save error:', err);
  });
""")
`);
    } catch (e) {
      console.warn("[wasm worker] DB sync error:", e);
    }
  }, 500);
}

// ── Service worker lifecycle ─────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(setupPython());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Only intercept same-origin requests. Let CDN / external requests pass.
  if (url.origin !== self.location.origin) {
    return;
  }

  // Don't intercept WASM playground static assets.
  const path = url.pathname;
  if (path.startsWith("/wasm/")) {
    return;
  }

  event.respondWith(
    djangoRequest(event.request).catch((err) => {
      console.error("[wasm worker] Error handling request:", url.pathname, err);
      return new Response(
        `<html><body><h1>Error</h1><pre>${err.message}\n${err.stack}</pre></body></html>`,
        {
          status: 500,
          headers: { "Content-Type": "text/html" },
        }
      );
    })
  );
});
