/* Vantage PDF Editor engine worker.
 *
 * Runs Python + PyMuPDF (WebAssembly, via Pyodide) in a background thread of
 * the visitor's browser and answers the page's "/api/..." requests with the
 * same code the desktop app uses. Nothing is sent over the network except the
 * one-time download of the engine files from this site.
 */
"use strict";

const BASE = new URL("../", self.location.href); // tool root (this file lives in static/)
const status = (text) => self.postMessage({ type: "status", text });

importScripts(new URL("pyodide/pyodide.js", BASE).href);

const ready = (async () => {
  status("Starting the PDF engine…");
  const pyodide = await loadPyodide({ indexURL: new URL("pyodide/", BASE).href });
  const manifest = await (await fetch(new URL("wheels/manifest.json", BASE))).json();
  status("Loading the PDF engine (first visit downloads about 30 MB)…");
  const quiet = { messageCallback: () => {}, errorCallback: (m) => console.warn(m) };
  await pyodide.loadPackage(manifest.packages, quiet);
  await pyodide.loadPackage(manifest.wheels.map((w) => new URL("wheels/" + w, BASE).href), quiet);
  pyodide.runPython("from pdfscout import webbridge; webbridge.install()");
  const bridge = pyodide.pyimport("pdfscout.webbridge");
  self.postMessage({ type: "ready", version: manifest.version });
  return bridge;
})();
ready.catch((e) => self.postMessage({ type: "fatal", error: String((e && e.message) || e) }));

self.onmessage = async (ev) => {
  const { id, method, url, headers, body } = ev.data;
  let reply;
  try {
    const bridge = await ready;
    const res = await bridge.handle(method, url, JSON.stringify(headers || []), body ? new Uint8Array(body) : null);
    const js = res.toJs({ dict_converter: Object.fromEntries });
    res.destroy();
    const bytes = js.body instanceof Uint8Array ? js.body.slice() : new Uint8Array(0);
    reply = { id, status: js.status, headers: js.headers, body: bytes.buffer };
    self.postMessage(reply, [bytes.buffer]);
  } catch (e) {
    const msg = JSON.stringify({ detail: "PDF engine error: " + String((e && e.message) || e).split("\n").slice(-3).join(" ") });
    self.postMessage({ id, status: 500, headers: [["content-type", "application/json"]], body: new TextEncoder().encode(msg).buffer });
  }
};
