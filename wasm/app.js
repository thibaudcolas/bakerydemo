/*
 * Main-thread script that registers the service worker and manages the
 * loading screen while Pyodide + Django/Wagtail spin up.
 */

const statusEl = document.getElementById("status");
const progressBar = document.getElementById("progress-bar");

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
  console.log("[wasm app]", msg);
}

function setProgress(pct) {
  if (progressBar) progressBar.style.width = `${pct}%`;
}

const STATUS_PROGRESS = {
  "Loading Python runtime...": 10,
  "Installing packages...": 25,
  "Installing Wagtail...": 40,
  "Installing extra packages...": 55,
  "Installing bakerydemo...": 70,
  "Setting up persistent storage...": 78,
  "Initializing Wagtail (migrations, data)...": 85,
  "Loading saved Wagtail data...": 85,
  ready: 100,
};

async function main() {
  if (!("serviceWorker" in navigator)) {
    setStatus(
      "Service workers are not supported in this browser. " +
        "Please use a modern browser (Chrome, Edge, Firefox) over HTTPS or localhost."
    );
    return;
  }

  // If ?reset is in the URL, unregister service workers and clear stored data.
  if (window.location.search.includes("reset")) {
    setStatus("Resetting...");
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const reg of registrations) {
      await reg.unregister();
    }
    // Clear IndexedDB databases used by IDBFS and Pyodide
    const dbs = await indexedDB.databases();
    for (const db of dbs) {
      if (db.name) indexedDB.deleteDatabase(db.name);
    }
    // Clear caches
    const cacheNames = await caches.keys();
    for (const name of cacheNames) {
      await caches.delete(name);
    }
    setStatus("Reset complete. Reloading...");
    window.location.href = window.location.pathname;
    return;
  }

  // Listen for messages from the service worker.
  let ready = false;
  navigator.serviceWorker.addEventListener("message", (event) => {
    const { type, message } = event.data || {};
    if (type !== "status") return;

    setStatus(message);
    const pct = STATUS_PROGRESS[message];
    if (pct !== undefined) setProgress(pct);

    if (message === "ready" && !ready) {
      ready = true;
      setStatus("Wagtail is ready! Loading site...");
      setTimeout(() => {
        window.location.href = "/";
      }, 500);
    }
  });

  try {
    setStatus("Registering service worker...");
    const registration = await navigator.serviceWorker.register(
      "/wasm/worker.js",
      { scope: "/" }
    );
    setStatus("Service worker registered. Setting up Python...");
    setProgress(5);

    // If the worker is already active and controlling this page, it means
    // Wagtail was previously loaded (e.g. the page was refreshed). However,
    // the in-memory state (DB, WSGI app) is gone if the worker restarted.
    // The worker's fetch handler re-runs setupPython if needed.
    if (navigator.serviceWorker.controller) {
      setStatus("Wagtail is ready! Loading site...");
      setProgress(100);
      window.location.href = "/";
      return;
    }
  } catch (err) {
    setStatus(`Failed to register service worker: ${err.message}`);
    console.error("SW registration failed:", err);
  }
}

main();
