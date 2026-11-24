/* Vantage PDF Editor client (desktop app and browser build). Plain JS, no build step. */
(() => {
  "use strict";

  // ------------------------------------------------------------------ icons
  const P = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const ICONS = {
    folder: P('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    file: P('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'),
    filePlus: P('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M12 11v6M9 14h6"/>'),
    download: P('<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>'),
    undo: P('<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>'),
    redo: P('<path d="m15 14 5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>'),
    plus: P('<path d="M12 5v14M5 12h14"/>'),
    minus: P('<path d="M5 12h14"/>'),
    search: P('<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>'),
    chevUp: P('<path d="m6 15 6-6 6 6"/>'),
    chevDown: P('<path d="m6 9 6 6 6-6"/>'),
    chevLeft: P('<path d="m15 6-6 6 6 6"/>'),
    grid: P('<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>'),
    x: P('<path d="M6 6l12 12M18 6 6 18"/>'),
    rotL: P('<path d="M4 4v6h6"/><path d="M4.5 10A8 8 0 1 1 6 16"/>'),
    rotR: P('<path d="M20 4v6h-6"/><path d="M19.5 10A8 8 0 1 0 18 16"/>'),
    trash: P('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>'),
    cursor: P('<path d="m5 3 14 7-6 2-2 6z"/>'),
    editText: P('<path d="M4 6V4h12v2M10 4v14M7 18h6"/><path d="m14 20 6-6 2 2-6 6h-2z"/>'),
    addText: P('<path d="M5 6V4h12v2M11 4v15M8 19h6"/><path d="M19 15v6M16 18h6"/>'),
    highlight: P('<path d="m9 11-5 5v4h4l5-5"/><path d="m14 6 4 4-5 5-4-4z"/><path d="M14 20h6"/>'),
    underline: P('<path d="M7 4v7a5 5 0 0 0 10 0V4M5 20h14"/>'),
    strike: P('<path d="M16 6.5C15 5 13.6 4 12 4c-2.5 0-4.5 1.6-4.5 3.6 0 1.6 1 2.6 3 3.4M5 12h14M8 17c1 1.8 2.4 3 4.2 3 2.7 0 4.8-1.6 4.8-3.8 0-.7-.2-1.3-.5-1.8"/>'),
    note: P('<path d="M4 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-7l-5 4v-4H5a1 1 0 0 1-1-1z"/>'),
    pen: P('<path d="M3 21c3 0 4-1 6-3l11-11-3-3L6 15c-2 2-3 3-3 6z"/><path d="m14 7 3 3"/>'),
    square: P('<rect x="4" y="5" width="16" height="14" rx="1"/>'),
    circle: P('<ellipse cx="12" cy="12" rx="8.5" ry="7"/>'),
    arrow: P('<path d="M5 19 19 5M10 5h9v9"/>'),
    image: P('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>'),
    sign: P('<path d="M3 17c2-3 3-9 5-9s-1 9 1 9 3-5 4-5 0 4 2 4 3-2 5-2"/><path d="M3 21h18"/>'),
    redact: P('<rect x="3" y="8" width="18" height="8" rx="1" fill="currentColor" stroke="none"/><path d="M3 4h10M3 20h14"/>'),
    crop: P('<path d="M6 2v14a2 2 0 0 0 2 2h14"/><path d="M2 6h14a2 2 0 0 1 2 2v14"/>'),
    form: P('<rect x="3" y="5" width="18" height="5" rx="1"/><rect x="3" y="14" width="5" height="5" rx="1"/><path d="m4.5 16.5 1 1 2-2M11 16.5h10"/>'),
    pages: P('<rect x="3" y="3" width="8" height="10" rx="1"/><rect x="13" y="3" width="8" height="10" rx="1"/><rect x="3" y="15" width="8" height="6" rx="1"/><rect x="13" y="15" width="8" height="6" rx="1"/>'),
    merge: P('<path d="M8 3v5a4 4 0 0 0 4 4 4 4 0 0 1 4 4v5M16 3v5a4 4 0 0 1-4 4"/><path d="m5 18 3 3 3-3" transform="translate(8 0)"/>'),
    split: P('<path d="M12 3v6M12 9 6 15v6M12 9l6 6v6"/>'),
    stamp: P('<path d="M9 13V9a3 3 0 1 1 6 0v4"/><path d="M5 13h14v4H5zM5 21h14"/>'),
    hash: P('<path d="M9 4 7 20M17 4l-2 16M4 9h16M3 15h16"/>'),
    lock: P('<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>'),
    zip: P('<path d="M4 14 9 9l4 4 7-7"/><path d="M14 6h6v6"/>'),
    broom: P('<path d="m14 4 6 6M17 7 9 15"/><path d="M4 20c0-4 2-7 5-7l2 2c0 3-3 5-7 5z"/>'),
    info: P('<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>'),
    bookmark: P('<path d="M6 3h12v18l-6-5-6 5z"/>'),
    export: P('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 14h6M12 11l3 3-3 3"/>'),
    scan: P('<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3M7 12h10"/>'),
    compare: P('<rect x="3" y="4" width="7" height="16" rx="1"/><rect x="14" y="4" width="7" height="16" rx="1"/><path d="M10 9h4M10 15h4"/>'),
    comments: P('<path d="M4 5h16v10H9l-5 4z"/><path d="M8 9h8M8 12h5"/>'),
    flatten: P('<path d="M3 8l9-5 9 5-9 5z"/><path d="m3 13 9 5 9-5"/>'),
  };
  const icon = (name) => `<i data-icon="${name}">${ICONS[name] || ""}</i>`;
  const hydrateIcons = (root = document) => root.querySelectorAll("i[data-icon]:empty").forEach((el) => (el.innerHTML = ICONS[el.dataset.icon] || ""));

  // ------------------------------------------------------------------ state
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const PT = 96 / 72; // CSS px per PDF point at 100%

  const S = {
    doc: null,          // snapshot from the server
    caps: { presets: {}, ocr: false },
    zoom: 1,
    tool: "select",
    currentPage: 0,
    selected: new Set(),
    pending: [],        // redaction marks: {page, rect}
    textCache: new Map(),
    search: { q: "", matches: [], idx: -1 },
    panel: null,
    renderedVersion: -1,
    annotations: [],
    picked: null,
    imageForPlacement: null,
  };

  const TOOLS = [
    { id: "select", name: "Select", icon: "cursor", hint: "Click a comment to select it. Press Delete to remove it." },
    { id: "edittext", name: "Edit text", icon: "editText", hint: "Click any line of text to change it.", opts: ["fontsize", "color", "family", "style"] },
    { id: "addtext", name: "Add text", icon: "addText", hint: "Click or drag a box on the page, then type.", opts: ["fontsize", "color", "family", "style"] },
    "sep",
    { id: "highlight", name: "Highlight", icon: "highlight", hint: "Drag across text to highlight it.", opts: ["color"], color: "#ffeb3b" },
    { id: "underline", name: "Underline", icon: "underline", hint: "Drag across text to underline it.", opts: ["color"], color: "#1d4ed8" },
    { id: "strikeout", name: "Strikethrough", icon: "strike", hint: "Drag across text to strike it out.", opts: ["color"], color: "#e5191a" },
    { id: "note", name: "Sticky note", icon: "note", hint: "Click where the note should go.", opts: ["color"], color: "#ffcc00" },
    { id: "freetext", name: "Text comment", icon: "comments", hint: "Drag a box for a text comment (annotation).", opts: ["fontsize", "color"], color: "#000000" },
    "sep",
    { id: "ink", name: "Draw", icon: "pen", hint: "Draw freehand on the page.", opts: ["color", "width"], color: "#1d4ed8" },
    { id: "rect", name: "Rectangle", icon: "square", hint: "Drag to draw a rectangle.", opts: ["color", "width"], color: "#e5191a" },
    { id: "ellipse", name: "Ellipse", icon: "circle", hint: "Drag to draw an ellipse.", opts: ["color", "width"], color: "#e5191a" },
    { id: "arrow", name: "Arrow", icon: "arrow", hint: "Drag from the tail to the head of the arrow.", opts: ["color", "width"], color: "#e5191a" },
    "sep",
    { id: "image", name: "Add image", icon: "image", hint: "Choose an image, then drag where it should go." },
    { id: "signature", name: "Fill & sign", icon: "sign", hint: "Create a signature, then drag where it should go." },
    { id: "field", name: "Form field", icon: "form", hint: "Drag to add a form field.", opts: ["field"] },
    "sep",
    { id: "redact", name: "Redact", icon: "redact", hint: "Drag over anything to mark it for redaction, then click Apply in the Redact panel." },
    { id: "crop", name: "Crop", icon: "crop", hint: "Drag the area to keep on this page." },
  ];
  const toolById = (id) => TOOLS.find((t) => t !== "sep" && t.id === id);
  const toolColors = {};

  // ------------------------------------------------------------------ utils
  function toast(msg, kind = "") {
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    el.textContent = msg;
    $("#toasts").appendChild(el);
    setTimeout(() => el.remove(), kind === "error" ? 6000 : 3200);
  }
  let busyCount = 0;
  function busy(on, text = "Working…") {
    busyCount += on ? 1 : -1;
    $("#busyText").textContent = text;
    clearTimeout(busy.t);
    if (busyCount > 0) busy.t = setTimeout(() => ($("#busy").hidden = busyCount <= 0), 250);
    else $("#busy").hidden = true;
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  async function api(path, { method = "GET", json, form, raw = false, quiet = false, busyText } = {}) {
    const opts = { method, headers: {} };
    if (json !== undefined) { opts.body = JSON.stringify(json); opts.headers["Content-Type"] = "application/json"; }
    if (form) opts.body = form;
    if (!quiet) busy(true, busyText);
    try {
      const res = await fetch(path, opts);
      if (!res.ok) {
        let detail = res.statusText;
        try { const j = await res.json(); detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch (_) {}
        const err = new Error(detail); err.status = res.status; throw err;
      }
      if (raw) return res;
      return res.headers.get("content-type")?.includes("json") ? res.json() : res.text();
    } finally {
      if (!quiet) busy(false);
    }
  }
  const docPath = (p = "") => `/api/documents/${S.doc.id}${p}`;

  async function op(name, body = {}, msg) {
    try {
      const snap = await api(docPath(`/ops/${name}`), { method: "POST", json: body });
      setDoc(snap);
      if (msg) toast(typeof msg === "function" ? msg(snap.result) : msg);
      return snap.result;
    } catch (e) { handleError(e); throw e; }
  }

  function handleError(e) {
    if (e.status === 404 && S.doc) toast("This document expired on the server. Please open it again.", "error");
    else toast(e.message || String(e), "error");
  }

  async function downloadResponse(res, fallback) {
    const blob = await res.blob();
    const cd = res.headers.get("content-disposition") || "";
    const m = cd.match(/filename="([^"]+)"/);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = m ? m[1] : fallback;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  // Desktop app (pywebview): native dialogs instead of browser downloads/uploads.
  const desktop = () => (window.pywebview && window.pywebview.api) || null;
  const docStem = () => (S.doc ? S.doc.filename.replace(/\.[^.]+$/, "") : "document");

  async function download(path, body, fallback = "download") {
    const isFullSave = path.endsWith("/download") && !(body && (body.user_password || body.owner_password));
    const savedVersion = S.doc && S.doc.version;
    const dk = desktop();
    if (dk) {
      try {
        busy(true, "Saving…");
        const r = await dk.save_download(path, body || {}, fallback);
        if (!r) return;
        if (r.error) return toast(r.error, "error");
        toast(`Saved ${r.name}`);
        if (isFullSave) markSaved(savedVersion);
      } catch (e) { handleError(e); } finally { busy(false); }
      return;
    }
    try {
      const res = await api(path, { method: "POST", json: body || {}, raw: true, busyText: "Preparing download…" });
      await downloadResponse(res, fallback);
      if (isFullSave) markSaved(savedVersion);
    } catch (e) { handleError(e); }
  }
  function markSaved(version) {
    S.savedVersion = version;
    updateTitle();
  }
  const isDirty = () => !!S.doc && S.savedVersion !== S.doc.version;
  function updateTitle() {
    if (!S.doc) return;
    document.title = `${isDirty() ? "• " : ""}${S.doc.filename} – ${BRAND().product}`;
    const dk = desktop();
    if (dk) dk.set_state(S.doc.filename, isDirty()).catch(() => {});
  }
  window.addEventListener("beforeunload", (e) => { if (!desktop() && isDirty()) { e.preventDefault(); e.returnValue = ""; } });

  function installDoc(snap) {
    if (S.doc) api(docPath(), { method: "DELETE", quiet: true }).catch(() => {});
    resetDocState();
    S.savedVersion = snap.version;
    setDoc(snap);
    fitWidth();
  }

  async function nativeOpen(path) {
    const dk = desktop();
    if (!path) path = await dk.choose_open();
    if (!path) return;
    let password = null;
    for (let attempt = 0; attempt < 4; attempt++) {
      busy(true, "Opening…");
      let r;
      try { r = await dk.open_path(path, password); } finally { busy(false); }
      if (r.snapshot) { installDoc(r.snapshot); return; }
      if (r.needs_password) {
        if (password) toast("Incorrect password", "error");
        password = await askPassword(r.name || path);
        if (password == null) return;
        continue;
      }
      toast(r.error || "Could not open the file", "error");
      return;
    }
  }

  function pickFile(accept, multiple = false) {
    return new Promise((resolve) => {
      const input = $("#fileAny");
      input.value = ""; input.accept = accept || ""; input.multiple = multiple;
      input.onchange = () => resolve(multiple ? Array.from(input.files) : input.files[0]);
      input.click();
    });
  }

  function modal(html, onMount) {
    const back = $("#modal");
    const box = $(".modal", back);
    box.innerHTML = html;
    hydrateIcons(box);
    back.hidden = false;
    return new Promise((resolve) => {
      const close = (v) => { back.hidden = true; box.innerHTML = ""; document.removeEventListener("keydown", onKey, true); resolve(v); };
      const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(null); } };
      document.addEventListener("keydown", onKey, true);
      back.onclick = (e) => { if (e.target === back) close(null); };
      $$("[data-close]", box).forEach((b) => (b.onclick = () => close(null)));
      onMount && onMount(box, close);
    });
  }

  async function askPassword(name) {
    return modal(`<h3>Password required</h3><p class="muted">${esc(name)} is protected. Enter its password to open it.</p>
      <form><div class="field"><input type="password" name="pw" autofocus autocomplete="off"></div>
      <div class="actions"><button class="btn primary" type="submit">Open</button><button class="btn" type="button" data-close>Cancel</button></div></form>`,
      (box, close) => { const f = $("form", box); $("input", f).focus(); f.onsubmit = (e) => { e.preventDefault(); close(f.pw.value); }; });
  }

  // ------------------------------------------------------------------ opening
  async function openFile(file) {
    if (!file) return;
    let password = null;
    for (let attempt = 0; attempt < 4; attempt++) {
      const fd = new FormData();
      fd.append("file", file);
      if (password) fd.append("password", password);
      try {
        const snap = await api("/api/documents", { method: "POST", form: fd, busyText: `Opening ${file.name}…` });
        installDoc(snap);
        return;
      } catch (e) {
        if (/password/i.test(e.message)) {
          if (password) toast("Incorrect password", "error");
          password = await askPassword(file.name);
          if (password == null) return;
          continue;
        }
        handleError(e);
        return;
      }
    }
  }

  async function newBlank() {
    try {
      const snap = await api("/api/documents/blank", { method: "POST", json: { size: "a4", pages: 1 } });
      installDoc(snap);
    } catch (e) { handleError(e); }
  }

  async function fromImages() {
    const files = await pickFile("image/*", true);
    if (!files || !files.length) return;
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    try {
      const snap = await api("/api/documents/from-images", { method: "POST", form: fd, busyText: "Creating PDF…" });
      installDoc(snap);
    } catch (e) { handleError(e); }
  }

  function resetDocState() {
    S.currentPage = 0; S.selected.clear(); S.pending = []; S.textCache.clear();
    S.search = { q: "", matches: [], idx: -1 }; S.renderedVersion = -1; S.picked = null;
    $("#searchInput").value = ""; $("#searchCount").textContent = "";
  }

  // ------------------------------------------------------------------ document state
  function setDoc(snap) {
    const versionChanged = !S.doc || S.doc.version !== snap.version || S.doc.id !== snap.id;
    S.doc = snap;
    document.body.classList.add("has-doc");
    updateTitle();
    $('[data-action="undo"]').disabled = !snap.can_undo;
    $('[data-action="undo"]').title = snap.can_undo ? `Undo ${snap.undo_label} (Ctrl+Z)` : "Nothing to undo";
    $('[data-action="redo"]').disabled = !snap.can_redo;
    $('[data-action="redo"]').title = snap.can_redo ? `Redo ${snap.redo_label} (Ctrl+Shift+Z)` : "Nothing to redo";
    $("#pageTotal").textContent = `/ ${snap.page_count}`;
    S.currentPage = clamp(S.currentPage, 0, snap.page_count - 1);
    [...S.selected].forEach((p) => p >= snap.page_count && S.selected.delete(p));
    S.pending = S.pending.filter((m) => m.page < snap.page_count);
    if (versionChanged) {
      S.textCache.clear();
      S.picked = null;
      renderPages();
      renderThumbs();
      refreshAnnotations();
      if (S.search.q) runSearch(S.search.q, true);
    }
    updatePageInput();
    if (S.panel) renderPanel(S.panel, true);
  }

  // ------------------------------------------------------------------ rendering
  let pageObserver;
  function renderScale() {
    const s = S.zoom * PT * (window.devicePixelRatio || 1);
    return clamp(Math.ceil(s * 4) / 4, 0.5, 5);
  }

  function renderPages() {
    const box = $("#pages");
    const viewer = $("#viewer");
    const anchor = S.doc ? S.currentPage : 0;
    const prevTop = viewer.scrollTop;
    box.innerHTML = "";
    if (pageObserver) pageObserver.disconnect();
    pageObserver = new IntersectionObserver(onPageVisible, { root: viewer, rootMargin: "600px 0px" });
    S.doc.pages.forEach((p, i) => {
      const el = document.createElement("div");
      el.className = "page";
      el.dataset.page = i;
      el.style.width = `${p.width * S.zoom * PT}px`;
      el.style.height = `${p.height * S.zoom * PT}px`;
      el.innerHTML = `<span class="label">${i + 1}</span><img alt="Page ${i + 1}" draggable="false"><div class="overlay"><svg class="draw"></svg></div>`;
      box.appendChild(el);
      pageObserver.observe(el);
      attachOverlay(el, i);
    });
    S.renderedVersion = S.doc.version;
    viewer.scrollTop = prevTop;
    if (!prevTop && anchor) scrollToPage(anchor, false);
    drawMarks();
  }

  function onPageVisible(entries) {
    for (const en of entries) {
      if (!en.isIntersecting) continue;
      const el = en.target;
      const i = +el.dataset.page;
      const img = $("img", el);
      const src = `${docPath(`/pages/${i}/image`)}?scale=${renderScale()}&v=${S.doc.version}`;
      if (img.dataset.src !== src) { img.dataset.src = src; img.src = src; }
      if (S.tool === "edittext") loadTextLines(i);
    }
  }

  function zoomTo(z, keepCenter = true) {
    const viewer = $("#viewer");
    const ratio = clamp(z, 0.25, 4) / S.zoom;
    const cx = viewer.scrollLeft + viewer.clientWidth / 2;
    const cy = viewer.scrollTop + viewer.clientHeight / 2;
    S.zoom = clamp(z, 0.25, 4);
    $("#zoomLabel").textContent = `${Math.round(S.zoom * 100)}%`;
    if (!S.doc) return;
    S.doc.pages.forEach((p, i) => {
      const el = $(`.page[data-page="${i}"]`);
      if (!el) return;
      el.style.width = `${p.width * S.zoom * PT}px`;
      el.style.height = `${p.height * S.zoom * PT}px`;
      const img = $("img", el);
      if (img.dataset.src) { img.dataset.src = ""; }
    });
    // re-trigger image loads at new resolution
    pageObserver && $$(".page").forEach((el) => { pageObserver.unobserve(el); pageObserver.observe(el); });
    if (keepCenter) { viewer.scrollLeft = cx * ratio - viewer.clientWidth / 2; viewer.scrollTop = cy * ratio - viewer.clientHeight / 2; }
    drawMarks();
  }
  function fitWidth() {
    if (!S.doc) return;
    const maxW = Math.max(...S.doc.pages.map((p) => p.width));
    const avail = $("#viewer").clientWidth - 56;
    zoomTo(clamp(avail / (maxW * PT), 0.25, 1.5), false);
  }

  function scrollToPage(i, smooth = true) {
    const el = $(`.page[data-page="${i}"]`);
    if (!el) return;
    $("#viewer").scrollTo({ top: el.offsetTop - 16, behavior: smooth ? "smooth" : "auto" });
    setCurrentPage(i);
  }
  function setCurrentPage(i) {
    if (!S.doc) return;
    S.currentPage = clamp(i, 0, S.doc.page_count - 1);
    updatePageInput();
    $$(".thumb").forEach((t) => t.classList.toggle("current", +t.dataset.page === S.currentPage));
  }
  function updatePageInput() { if (S.doc && document.activeElement !== $("#pageInput")) $("#pageInput").value = S.currentPage + 1; }

  $("#viewer").addEventListener("scroll", () => {
    if (!S.doc) return;
    const viewer = $("#viewer");
    const mid = viewer.scrollTop + viewer.clientHeight * 0.35;
    let best = 0;
    for (const el of $$(".page")) { if (el.offsetTop <= mid) best = +el.dataset.page; else break; }
    if (best !== S.currentPage) setCurrentPage(best);
  }, { passive: true });

  // ------------------------------------------------------------------ thumbnails & page organisation
  function renderThumbs() {
    const list = $("#thumbList");
    list.innerHTML = "";
    const io = new IntersectionObserver((ents) => ents.forEach((en) => {
      if (en.isIntersecting) { const img = $("img", en.target); if (!img.src) img.src = img.dataset.src; io.unobserve(en.target); }
    }), { root: list, rootMargin: "300px" });
    S.doc.pages.forEach((p, i) => {
      const t = document.createElement("div");
      t.className = "thumb";
      t.dataset.page = i;
      t.draggable = true;
      const scale = Math.min(128 / p.width, 170 / p.height);
      t.innerHTML = `<div class="frame"><img alt="" style="width:${p.width * scale}px;height:${p.height * scale}px" data-src="${docPath(`/pages/${i}/image`)}?scale=${Math.max(0.25, scale * 2).toFixed(2)}&v=${S.doc.version}"></div><div>${i + 1}</div>`;
      t.classList.toggle("current", i === S.currentPage);
      t.classList.toggle("selected", S.selected.has(i));
      t.addEventListener("click", (e) => {
        if (e.ctrlKey || e.metaKey) { S.selected.has(i) ? S.selected.delete(i) : S.selected.add(i); }
        else if (e.shiftKey && S.selected.size) {
          const last = [...S.selected].pop();
          for (let k = Math.min(last, i); k <= Math.max(last, i); k++) S.selected.add(k);
        } else { S.selected = new Set([i]); }
        $$(".thumb").forEach((x) => x.classList.toggle("selected", S.selected.has(+x.dataset.page)));
        scrollToPage(i);
      });
      t.addEventListener("dragstart", (e) => { e.dataTransfer.setData("text/x-page", String(i)); e.dataTransfer.effectAllowed = "move"; });
      t.addEventListener("dragover", (e) => {
        if (!e.dataTransfer.types.includes("text/x-page")) return;
        e.preventDefault();
        const r = t.getBoundingClientRect();
        const after = e.clientY > r.top + r.height / 2;
        $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after"));
        t.classList.add(after ? "drop-after" : "drop-before");
      });
      t.addEventListener("dragleave", () => t.classList.remove("drop-before", "drop-after"));
      t.addEventListener("drop", (e) => {
        e.preventDefault();
        const from = +e.dataTransfer.getData("text/x-page");
        const after = t.classList.contains("drop-after");
        $$(".thumb").forEach((x) => x.classList.remove("drop-before", "drop-after"));
        let to = i + (after ? 1 : 0);
        if (from < to) to -= 1;
        if (from !== to) { S.selected = new Set([to]); S.currentPage = to; op("move_page", { from, to }).catch(() => {}); }
      });
      list.appendChild(t);
      io.observe(t);
    });
  }
  const selectedPages = () => (S.selected.size ? [...S.selected].sort((a, b) => a - b) : [S.currentPage]);

  // ------------------------------------------------------------------ marks (redactions, search hits, annotations)
  function rectStyle(r) {
    const k = S.zoom * PT;
    return `left:${r[0] * k}px;top:${r[1] * k}px;width:${(r[2] - r[0]) * k}px;height:${(r[3] - r[1]) * k}px`;
  }
  function drawMarks() {
    if (!S.doc) return;
    $$(".mark.redact, .mark.search, .mark.annot").forEach((m) => m.remove());
    S.pending.forEach((m, idx) => {
      const ov = $(`.page[data-page="${m.page}"] .overlay`);
      if (!ov) return;
      const d = document.createElement("div");
      d.className = "mark redact";
      d.style.cssText = rectStyle(m.rect);
      d.title = "Marked for redaction – click to unmark";
      d.innerHTML = '<span class="x">×</span>';
      d.addEventListener("pointerdown", (e) => e.stopPropagation());
      d.addEventListener("click", (e) => { e.stopPropagation(); S.pending.splice(idx, 1); drawMarks(); if (S.panel === "redact") renderPanel("redact", true); });
      ov.appendChild(d);
    });
    S.search.matches.forEach((m, idx) => {
      const ov = $(`.page[data-page="${m.page}"] .overlay`);
      if (!ov) return;
      m.rects.forEach((r) => {
        const d = document.createElement("div");
        d.className = "mark search" + (idx === S.search.idx ? " current" : "");
        d.style.cssText = rectStyle(r);
        ov.appendChild(d);
      });
    });
    if (S.tool === "select") {
      S.annotations.forEach((a) => {
        if (a.type === "Widget" || a.type === "Link" || a.type === "Popup") return;
        const ov = $(`.page[data-page="${a.page}"] .overlay`);
        if (!ov) return;
        const d = document.createElement("div");
        d.className = "mark annot" + (S.picked && S.picked.xref === a.xref ? " picked" : "");
        d.style.cssText = rectStyle(a.rect);
        d.title = `${a.type}${a.content ? ": " + a.content : ""}`;
        d.addEventListener("pointerdown", (e) => { e.stopPropagation(); S.picked = a; drawMarks(); });
        d.addEventListener("dblclick", () => { openPanel("comments"); });
        ov.appendChild(d);
      });
    }
  }
  async function refreshAnnotations() {
    try { S.annotations = (await api(docPath("/annotations"), { quiet: true })).annotations; drawMarks(); }
    catch (_) { S.annotations = []; }
  }

  // ------------------------------------------------------------------ edit-text overlay
  async function loadTextLines(i) {
    if (S.textCache.has(i)) return drawTextLines(i);
    S.textCache.set(i, null);
    try {
      const { lines } = await api(docPath(`/pages/${i}/text`), { quiet: true });
      S.textCache.set(i, lines);
      drawTextLines(i);
    } catch (e) { S.textCache.delete(i); }
  }
  function drawTextLines(i) {
    const ov = $(`.page[data-page="${i}"] .overlay`);
    const lines = S.textCache.get(i);
    if (!ov || !lines || S.tool !== "edittext") return;
    $$(".mark.textline", ov).forEach((m) => m.remove());
    lines.forEach((ln) => {
      const d = document.createElement("div");
      d.className = "mark textline";
      d.style.cssText = rectStyle(ln.bbox);
      d.title = ln.text;
      d.addEventListener("pointerdown", (e) => { e.stopPropagation(); e.preventDefault(); openLineEditor(i, ln, d); });
      ov.appendChild(d);
    });
  }
  function clearTextLines() { $$(".mark.textline").forEach((m) => m.remove()); }

  function openLineEditor(page, ln, markEl) {
    closeEditors();
    const ov = markEl.parentElement;
    const k = S.zoom * PT;
    const ta = document.createElement("textarea");
    ta.className = "inline-editor";
    ta.value = ln.text;
    ta.spellcheck = false;
    const vertical = Math.abs(ln.dir[0]) < 0.5;
    const fs = ln.size * k;
    Object.assign(ta.style, {
      left: `${ln.bbox[0] * k - 2}px`, top: `${ln.bbox[1] * k - 2}px`,
      width: `${Math.max((ln.bbox[2] - ln.bbox[0]) * k + 40, 80)}px`,
      height: `${vertical ? fs * 1.4 : (ln.bbox[3] - ln.bbox[1]) * k + 4}px`,
      fontSize: `${fs}px`, color: ln.color || "#000",
      fontFamily: ln.family === "serif" ? "Times New Roman, serif" : ln.family === "mono" ? "Courier New, monospace" : "Helvetica, Arial, sans-serif",
      fontWeight: ln.bold ? "700" : "400", fontStyle: ln.italic ? "italic" : "normal",
    });
    ov.appendChild(ta);
    ta.focus(); ta.select();
    // reflect the current option-bar values into the line style when user changes them
    $("#optFontSize").value = Math.round(ln.size * 10) / 10;
    $("#optColor").value = ln.color || "#000000";
    $("#optFamily").value = ln.family;
    $("#optBold").classList.toggle("on", !!ln.bold);
    $("#optItalic").classList.toggle("on", !!ln.italic);
    const startStyle = styleOpts();
    const grow = () => { ta.style.width = "0px"; ta.style.width = `${Math.max(ta.scrollWidth + 8, 80)}px`; };
    ta.addEventListener("input", grow); grow();
    let done = false;
    const commit = async (save) => {
      if (done) return; done = true;
      const text = ta.value.replace(/\n/g, " ");
      const st = styleOpts();
      const styleChanged = JSON.stringify(st) !== JSON.stringify(startStyle);
      ta.remove();
      if (!save || (text === ln.text && !styleChanged)) return;
      const body = { page, bbox: ln.bbox, text };
      if (styleChanged) Object.assign(body, { fontsize: st.fontsize, color: st.color, family: st.family, bold: st.bold, italic: st.italic });
      await op("edit_text", body).catch(() => {});
    };
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); commit(true); }
      if (e.key === "Escape") { e.preventDefault(); commit(false); }
      e.stopPropagation();
    });
    ta.addEventListener("blur", () => setTimeout(() => { if (!ta.isConnected) return; if (!$("#optionsBar").contains(document.activeElement)) commit(true); else ta.focus(); }, 120));
    ta._commit = commit;
  }
  function closeEditors() { $$(".inline-editor, .popover").forEach((el) => (el._commit ? el._commit(true) : el.remove())); }

  function styleOpts() {
    return {
      fontsize: parseFloat($("#optFontSize").value) || 12,
      color: $("#optColor").value,
      family: $("#optFamily").value,
      bold: $("#optBold").classList.contains("on"),
      italic: $("#optItalic").classList.contains("on"),
    };
  }

  // ------------------------------------------------------------------ tools
  function renderToolstrip() {
    const strip = $("#toolstrip");
    strip.innerHTML = TOOLS.map((t) => (t === "sep" ? '<div class="sep"></div>' : `<button class="tool" data-tool="${t.id}" title="${t.name}" aria-label="${t.name}">${icon(t.icon)}</button>`)).join("");
    strip.addEventListener("click", (e) => { const b = e.target.closest(".tool"); if (b) setTool(b.dataset.tool); });
  }

  async function setTool(id) {
    closeEditors();
    const prev = S.tool;
    if (prev !== "select" || id !== "select") toolColors[prev] = $("#optColor").value;
    const t = toolById(id) || toolById("select");
    if (id === "image") {
      const f = await pickFile("image/*");
      if (!f) return;
      S.imageForPlacement = { blob: f, name: f.name };
    }
    if (id === "signature") {
      const sig = await signatureDialog();
      if (!sig) return;
      S.imageForPlacement = { blob: sig, name: "signature.png", signature: true };
    }
    S.tool = t.id;
    document.body.dataset.tool = t.id;
    $$(".tool").forEach((b) => b.classList.toggle("active", b.dataset.tool === t.id));
    $("#toolName").textContent = t.name;
    $("#toolHint").textContent = t.hint || "";
    $$("#toolOpts [data-opt]").forEach((el) => (el.hidden = !(t.opts || []).includes(el.dataset.opt)));
    if (t.opts && t.opts.includes("color")) $("#optColor").value = toolColors[t.id] || t.color || "#000000";
    if (t.id === "edittext") $$(".page").forEach((el) => { const r = el.getBoundingClientRect(); if (r.bottom > 0 && r.top < innerHeight + 600) loadTextLines(+el.dataset.page); });
    else clearTextLines();
    if (t.id === "redact" && S.panel !== "redact") openPanel("redact");
    drawMarks();
  }

  function eventPoint(e, ov) {
    const r = ov.getBoundingClientRect();
    const k = S.zoom * PT;
    return [clamp((e.clientX - r.left) / k, 0, r.width / k), clamp((e.clientY - r.top) / k, 0, r.height / k)];
  }
  const normRect = (a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];

  function attachOverlay(pageEl, page) {
    const ov = $(".overlay", pageEl);
    const svg = $("svg.draw", ov);
    ov.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 || e.target.closest(".inline-editor, .popover")) return;
      setCurrentPage(page);
      const tool = S.tool;
      if (tool === "select") { if (S.picked) { S.picked = null; drawMarks(); } return; }
      if (tool === "edittext") return;
      closeEditors();
      e.preventDefault();
      ov.setPointerCapture(e.pointerId);
      const start = eventPoint(e, ov);
      const k = S.zoom * PT;
      let rubber = null, line = null, path = null;
      const pts = [start];
      if (tool === "ink") {
        path = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        path.setAttribute("fill", "none"); path.setAttribute("stroke", $("#optColor").value);
        path.setAttribute("stroke-width", parseFloat($("#optWidth").value) * k); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round");
        svg.appendChild(path);
      } else if (tool === "arrow") {
        line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("stroke", $("#optColor").value); line.setAttribute("stroke-width", parseFloat($("#optWidth").value) * k);
        svg.appendChild(line);
      } else if (tool !== "note") {
        rubber = document.createElement("div");
        rubber.className = "mark rubber" + (tool === "redact" ? " redact-draw" : "");
        ov.appendChild(rubber);
      }
      const move = (ev) => {
        const p = eventPoint(ev, ov);
        if (path) { pts.push(p); path.setAttribute("points", pts.map((q) => `${q[0] * k},${q[1] * k}`).join(" ")); }
        else if (line) { line.setAttribute("x1", start[0] * k); line.setAttribute("y1", start[1] * k); line.setAttribute("x2", p[0] * k); line.setAttribute("y2", p[1] * k); pts[1] = p; }
        else if (rubber) { rubber.style.cssText = rectStyle(normRect(start, p)); }
      };
      const up = (ev) => {
        ov.removeEventListener("pointermove", move);
        ov.removeEventListener("pointerup", up);
        ov.removeEventListener("pointercancel", up);
        const end = eventPoint(ev, ov);
        rubber && rubber.remove();
        if (line) line.remove();
        const rect = normRect(start, end);
        const tiny = rect[2] - rect[0] < 3 && rect[3] - rect[1] < 3;
        finishGesture(tool, page, { start, end, rect, tiny, pts, path, ov, ev }).catch(() => {});
      };
      ov.addEventListener("pointermove", move);
      ov.addEventListener("pointerup", up);
      ov.addEventListener("pointercancel", up);
    });
  }

  async function finishGesture(tool, page, g) {
    const color = $("#optColor").value;
    const width = parseFloat($("#optWidth").value);
    switch (tool) {
      case "highlight": case "underline": case "strikeout":
        if (g.tiny) return;
        return op("annotate", { page, kind: tool, rect: g.rect, color });
      case "rect": case "ellipse":
        if (g.tiny) return;
        return op("annotate", { page, kind: tool, rect: g.rect, color, width });
      case "arrow":
        if (g.tiny) return;
        return op("annotate", { page, kind: "arrow", start: g.start, end: g.end, color, width });
      case "ink": {
        g.path && setTimeout(() => g.path.remove(), 400);
        if (g.pts.length < 2) return;
        const simplified = g.pts.filter((p, i, a) => i === 0 || i === a.length - 1 || Math.hypot(p[0] - a[i - 1][0], p[1] - a[i - 1][1]) > 0.8);
        return op("annotate", { page, kind: "ink", strokes: [simplified], color, width });
      }
      case "note":
        return notePopover(page, g.start, g.ov, async (text) => op("annotate", { page, kind: "note", point: g.start, text, color }));
      case "freetext": {
        const r = g.tiny ? [g.start[0], g.start[1], g.start[0] + 180, g.start[1] + 40] : g.rect;
        return textBoxEditor(page, r, g.ov, true, (text) => op("annotate", { page, kind: "freetext", rect: r, text, color, fontsize: styleOpts().fontsize }));
      }
      case "addtext": {
        const st = styleOpts();
        const r = g.tiny ? [g.start[0], g.start[1] - st.fontsize * 0.2, g.start[0] + 220, g.start[1] + st.fontsize * 1.4] : g.rect;
        return textBoxEditor(page, r, g.ov, !g.tiny, (text) => op("add_text", { page, rect: r, text, ...st }));
      }
      case "image": case "signature": {
        const img = S.imageForPlacement;
        if (!img) return;
        let r = g.rect;
        if (g.tiny) { const w = img.signature ? 160 : 200; const h = img.signature ? 60 : 150; r = [g.start[0], g.start[1], g.start[0] + w, g.start[1] + h]; }
        const fd = new FormData();
        fd.append("file", img.blob, img.name); fd.append("page", page); fd.append("rect", JSON.stringify(r));
        try { setDoc(await api(docPath("/image"), { method: "POST", form: fd })); } catch (e) { handleError(e); }
        return;
      }
      case "field": {
        if (g.tiny) return;
        const kind = $("#optField").value;
        const name = await promptDialog("New form field", "Field name", `${kind}_${Date.now().toString(36).slice(-4)}`, kind === "combobox" ? "Options (comma separated)" : null);
        if (!name) return;
        return op("add_field", { page, kind, rect: g.rect, name: name.value, options: name.extra ? name.extra.split(",").map((s) => s.trim()).filter(Boolean) : undefined }, "Form field added");
      }
      case "redact":
        if (g.tiny) return;
        S.pending.push({ page, rect: g.rect });
        drawMarks();
        if (S.panel === "redact") renderPanel("redact", true);
        return;
      case "crop": {
        if (g.tiny) return;
        const pages = S.selected.size > 1 ? selectedPages() : [page];
        const ok = await confirmDialog("Crop pages", `Crop ${pages.length > 1 ? `${pages.length} selected pages` : `page ${page + 1}`} to the selected area?`, "Crop");
        if (ok) await op("crop", { pages, rect: g.rect }, "Cropped");
        setTool("select");
      }
    }
  }

  function textBoxEditor(page, rect, ov, isBox, onCommit) {
    const k = S.zoom * PT;
    const st = styleOpts();
    const ta = document.createElement("textarea");
    ta.className = "inline-editor box";
    ta.placeholder = "Type here";
    Object.assign(ta.style, {
      left: `${rect[0] * k}px`, top: `${rect[1] * k}px`, width: `${(rect[2] - rect[0]) * k}px`, minHeight: `${(rect[3] - rect[1]) * k}px`,
      fontSize: `${st.fontsize * k}px`, color: st.color, whiteSpace: "pre-wrap", overflow: "visible",
      fontFamily: st.family === "serif" ? "Times New Roman, serif" : st.family === "mono" ? "Courier New, monospace" : "Helvetica, Arial, sans-serif",
      fontWeight: st.bold ? "700" : "400", fontStyle: st.italic ? "italic" : "normal",
    });
    ov.appendChild(ta);
    setTimeout(() => ta.focus(), 0);
    const autosize = () => { ta.style.height = "auto"; ta.style.height = `${ta.scrollHeight + 2}px`; };
    ta.addEventListener("input", autosize);
    let done = false;
    const commit = (save) => {
      if (done) return; done = true;
      const text = ta.value;
      ta.remove();
      if (save && text.trim()) onCommit(text);
    };
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { e.preventDefault(); commit(false); }
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); commit(true); }
      e.stopPropagation();
    });
    ta.addEventListener("blur", () => setTimeout(() => { if (ta.isConnected && !$("#optionsBar").contains(document.activeElement)) commit(true); }, 120));
    ta._commit = commit;
  }

  function notePopover(page, pt, ov, onSave) {
    const k = S.zoom * PT;
    const pop = document.createElement("div");
    pop.className = "popover";
    pop.style.left = `${pt[0] * k}px`; pop.style.top = `${pt[1] * k + 20}px`;
    pop.innerHTML = `<textarea placeholder="Add a comment"></textarea><div class="row"><button class="btn" data-x>Cancel</button><button class="btn primary" data-ok>Post</button></div>`;
    ov.appendChild(pop);
    pop.addEventListener("pointerdown", (e) => e.stopPropagation());
    const ta = $("textarea", pop);
    setTimeout(() => ta.focus(), 0);
    const close = () => pop.remove();
    $("[data-x]", pop).onclick = close;
    $("[data-ok]", pop).onclick = () => { const v = ta.value.trim(); close(); if (v) onSave(v); };
    ta.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Escape") close(); if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("[data-ok]", pop).click(); });
  }

  function confirmDialog(title, text, okLabel = "OK", danger = false) {
    return modal(`<h3>${esc(title)}</h3><p>${esc(text)}</p><div class="actions"><button class="btn ${danger ? "danger" : "primary"}" data-ok>${esc(okLabel)}</button><button class="btn" data-close>Cancel</button></div>`,
      (box, close) => { $("[data-ok]", box).onclick = () => close(true); $("[data-ok]", box).focus(); }).then((v) => !!v);
  }
  function promptDialog(title, label, value = "", extraLabel = null) {
    return modal(`<h3>${esc(title)}</h3><form><label class="field"><span>${esc(label)}</span><input type="text" name="v" value="${esc(value)}"></label>
      ${extraLabel ? `<label class="field"><span>${esc(extraLabel)}</span><input type="text" name="x"></label>` : ""}
      <div class="actions"><button class="btn primary" type="submit">OK</button><button class="btn" type="button" data-close>Cancel</button></div></form>`,
      (box, close) => { const f = $("form", box); f.v.focus(); f.v.select(); f.onsubmit = (e) => { e.preventDefault(); if (f.v.value.trim()) close({ value: f.v.value.trim(), extra: f.x ? f.x.value : "" }); }; });
  }

  // ------------------------------------------------------------------ signature
  function signatureDialog() {
    let saved = null;
    try { saved = localStorage.getItem("pdfscout.signature"); } catch (_) {}
    return modal(`<h3>Create signature</h3>
      ${saved ? `<div class="note">Use your saved signature or draw a new one.<div class="actions"><button class="btn primary" data-saved>Use saved signature</button></div></div>` : ""}
      <p class="muted">Draw your signature below.</p>
      <canvas class="sig-pad" width="1000" height="360"></canvas>
      <div class="actions"><label class="check"><input type="checkbox" checked data-remember> Remember on this device</label></div>
      <div class="actions"><button class="btn primary" data-ok>Use signature</button><button class="btn" data-clear>Clear</button><button class="btn" data-close>Cancel</button></div>`,
    (box, close) => {
      const cv = $("canvas", box), ctx = cv.getContext("2d");
      ctx.lineWidth = 5; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#0b1f66";
      let drawing = false, dirty = false, last = null;
      const pos = (e) => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) * cv.width / r.width, (e.clientY - r.top) * cv.height / r.height]; };
      cv.onpointerdown = (e) => { drawing = true; last = pos(e); cv.setPointerCapture(e.pointerId); };
      cv.onpointermove = (e) => { if (!drawing) return; const p = pos(e); ctx.beginPath(); ctx.moveTo(...last); ctx.lineTo(...p); ctx.stroke(); last = p; dirty = true; };
      cv.onpointerup = () => (drawing = false);
      $("[data-clear]", box).onclick = () => { ctx.clearRect(0, 0, cv.width, cv.height); dirty = false; };
      const toBlob = (url) => fetch(url).then((r) => r.blob());
      if (saved) $("[data-saved]", box).onclick = async () => close(await toBlob(saved));
      $("[data-ok]", box).onclick = async () => {
        if (!dirty) { toast("Draw your signature first"); return; }
        const url = trimCanvas(cv);
        if ($("[data-remember]", box).checked) { try { localStorage.setItem("pdfscout.signature", url); } catch (_) {} }
        close(await toBlob(url));
      };
    });
  }
  function trimCanvas(cv) {
    const ctx = cv.getContext("2d");
    const { data, width, height } = ctx.getImageData(0, 0, cv.width, cv.height);
    let x0 = width, y0 = height, x1 = 0, y1 = 0;
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) if (data[(y * width + x) * 4 + 3] > 0) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    const pad = 8; x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad); x1 = Math.min(width, x1 + pad); y1 = Math.min(height, y1 + pad);
    const out = document.createElement("canvas"); out.width = x1 - x0; out.height = y1 - y0;
    out.getContext("2d").drawImage(cv, x0, y0, out.width, out.height, 0, 0, out.width, out.height);
    return out.toDataURL("image/png");
  }

  // ------------------------------------------------------------------ search
  let searchTimer;
  async function runSearch(q, keepIdx = false) {
    S.search.q = q;
    if (!q) { S.search.matches = []; S.search.idx = -1; $("#searchCount").textContent = ""; drawMarks(); return; }
    try {
      const { matches } = await api(docPath(`/search?q=${encodeURIComponent(q)}`), { quiet: true });
      if (S.search.q !== q) return;
      S.search.matches = matches;
      S.search.idx = matches.length ? (keepIdx ? clamp(S.search.idx, 0, matches.length - 1) : 0) : -1;
      $("#searchCount").textContent = matches.length ? `${S.search.idx + 1}/${matches.length}` : "0";
      drawMarks();
      if (!keepIdx && matches.length) focusMatch();
    } catch (e) { handleError(e); }
  }
  function focusMatch() {
    const m = S.search.matches[S.search.idx];
    if (!m) return;
    $("#searchCount").textContent = `${S.search.idx + 1}/${S.search.matches.length}`;
    drawMarks();
    const el = $(`.page[data-page="${m.page}"]`);
    const viewer = $("#viewer");
    viewer.scrollTo({ top: el.offsetTop + m.rects[0][1] * S.zoom * PT - viewer.clientHeight / 3, behavior: "smooth" });
    setCurrentPage(m.page);
  }
  function stepSearch(d) {
    const n = S.search.matches.length;
    if (!n) return;
    S.search.idx = (S.search.idx + d + n) % n;
    focusMatch();
  }

  // ------------------------------------------------------------------ panels
  const PANELS = [
    ["Edit & review", [
      ["redact", "Redact", "Permanently remove sensitive content", "redact", "red"],
      ["comments", "Comments", "Review and delete comments", "comments", "amber"],
      ["forms", "Prepare form", "Fill, create and flatten form fields", "form", "purple"],
    ]],
    ["Organize", [
      ["organize", "Organize pages", "Rotate, delete, reorder, extract", "pages", "blue"],
      ["merge", "Combine files", "Insert another PDF or image", "merge", "blue"],
      ["split", "Split PDF", "Split into multiple files", "split", "blue"],
    ]],
    ["Stamp", [
      ["watermark", "Watermark", "Add a text watermark", "stamp", "green"],
      ["headerfooter", "Header, footer & Bates", "Page numbers and Bates numbering", "hash", "green"],
      ["bookmarks", "Bookmarks", "Edit the outline", "bookmark", "green"],
    ]],
    ["Protect & optimize", [
      ["protect", "Protect", "Password and permissions", "lock", "purple"],
      ["sanitize", "Remove hidden info", "Metadata, scripts, attachments", "broom", "purple"],
      ["optimize", "Compress", "Reduce file size", "zip", "amber"],
      ["flatten", "Flatten", "Burn comments and fields into pages", "flatten", "amber"],
    ]],
    ["Convert", [
      ["export", "Export", "Images, text, HTML", "export", "red"],
      ["ocr", "Recognize text (OCR)", "Make scanned PDFs searchable", "scan", "red"],
      ["compare", "Compare files", "Find text differences", "compare", "red"],
      ["properties", "Properties", "Title, author, keywords", "info", "red"],
    ]],
  ];
  const panelTitle = (id) => { for (const [, items] of PANELS) for (const it of items) if (it[0] === id) return it[1]; return "All tools"; };

  function openPanel(id) {
    document.body.classList.remove("panel-closed");
    S.panel = id;
    renderPanel(id);
  }

  function renderPanel(id, refresh = false) {
    const body = $("#panelBody");
    $("#panelTitle").textContent = id ? panelTitle(id) : "All tools";
    $("#panelBack").style.visibility = id ? "visible" : "hidden";
    if (!id) {
      body.innerHTML = PANELS.map(([sec, items]) => `<div class="tool-section">${sec}</div><div class="tool-grid">${items.map(([pid, name, desc, ic, col]) =>
        `<button class="tool-card" data-panel="${pid}"><span class="ic ${col}">${icon(ic)}</span><span><b>${name}</b><small>${desc}</small></span></button>`).join("")}</div>`).join("");
      $$("[data-panel]", body).forEach((b) => (b.onclick = () => openPanel(b.dataset.panel)));
      return;
    }
    const scroll = body.scrollTop;
    const fn = PANEL_RENDER[id];
    if (fn) fn(body, refresh);
    hydrateIcons(body);
    if (refresh) body.scrollTop = scroll;
  }

  const val = (form, name) => form.elements[name] && (form.elements[name].type === "checkbox" ? form.elements[name].checked : form.elements[name].value);
  const pagesField = (label = "Pages", placeholder = "All pages (e.g. 1-3, 5)") => `<label class="field"><span>${label}</span><input type="text" name="pages" placeholder="${placeholder}"></label>`;

  const PANEL_RENDER = {
    redact(body, refresh) {
      const prev = refresh ? $("form", body) : null;
      const keep = prev ? { terms: prev.terms.value, regex: prev.regex.value, presets: $$(".chip.on", body).map((c) => c.dataset.preset), overlay: prev.overlay.value, fill: prev.fill.value } : null;
      const presets = Object.entries(S.caps.presets || {});
      body.innerHTML = `
        <p class="note">Redaction <b>permanently deletes</b> the text, images and graphics under each mark – it is not just a black box on top. Review the marks before applying.</p>
        <div class="actions" style="margin:0 0 14px"><button class="btn block" data-mark>${icon("redact")}<span>Mark area by dragging</span></button></div>
        <form>
          <div class="tool-section">Find text &amp; redact</div>
          <label class="field"><span>Words or phrases (one per line)</span><textarea name="terms" placeholder="Jane Doe&#10;Account 12345"></textarea></label>
          <div class="field"><span>Patterns</span><div class="chips">${presets.map(([k, v]) => `<button type="button" class="chip" data-preset="${k}">${esc(v)}</button>`).join("")}</div></div>
          <label class="field"><span>Regular expression (optional)</span><input type="text" name="regex" placeholder="e.g. INV-\\d{6}"></label>
          <label class="check"><input type="checkbox" name="case"> Match case</label>
          <label class="check"><input type="checkbox" name="word"> Whole words only</label>
          <div class="actions"><button class="btn" type="submit">${icon("search")}<span>Find &amp; mark</span></button></div>
          <hr class="sep">
          <div class="tool-section">Appearance</div>
          <div class="row2">
            <label class="field"><span>Fill</span><select name="fill"><option value="#000000">Black box</option><option value="#ffffff">White (invisible)</option><option value="">No fill</option></select></label>
            <label class="field"><span>Overlay text</span><input type="text" name="overlay" placeholder="e.g. REDACTED"></label>
          </div>
          <label class="check"><input type="checkbox" name="sanitize" checked> Also remove hidden information (metadata, scripts…)</label>
        </form>
        <hr class="sep">
        <div style="display:flex;justify-content:space-between;align-items:center"><b>Marked for redaction</b><span class="badge">${S.pending.length}</span></div>
        <div class="list">${S.pending.slice(0, 200).map((m, i) => `<div class="list-item" data-i="${i}"><div class="grow">Page ${m.page + 1}${m.text ? ` – “${esc(m.text)}”` : " – area"}</div><button class="icon-btn sm" data-del="${i}" title="Unmark">${icon("x")}</button></div>`).join("")}</div>
        <div class="actions">
          <button class="btn danger" data-apply ${S.pending.length ? "" : "disabled"}>Apply ${S.pending.length || ""} redaction${S.pending.length === 1 ? "" : "s"}</button>
          <button class="btn" data-clear ${S.pending.length ? "" : "disabled"}>Clear marks</button>
        </div>`;
      const f = $("form", body);
      if (keep) { f.terms.value = keep.terms; f.regex.value = keep.regex; f.overlay.value = keep.overlay; f.fill.value = keep.fill; keep.presets.forEach((p) => $(`[data-preset="${p}"]`, body)?.classList.add("on")); }
      $$(".chip", body).forEach((c) => (c.onclick = () => c.classList.toggle("on")));
      $("[data-mark]", body).onclick = () => setTool("redact");
      f.onsubmit = async (e) => {
        e.preventDefault();
        const req = {
          terms: f.terms.value.split("\n").map((s) => s.trim()).filter(Boolean),
          regexes: f.regex.value.trim() ? [f.regex.value.trim()] : [],
          presets: $$(".chip.on", body).map((c) => c.dataset.preset),
          case_sensitive: f.case.checked, whole_word: f.word.checked,
        };
        try {
          const { matches } = await api(docPath("/redact/preview"), { method: "POST", json: req, busyText: "Searching…" });
          let added = 0;
          for (const m of matches) for (const r of m.rects) {
            if (!S.pending.some((p) => p.page === m.page && p.rect.every((v, i) => Math.abs(v - r[i]) < 0.5))) { S.pending.push({ page: m.page, rect: r, text: m.text }); added++; }
          }
          toast(matches.length ? `Marked ${matches.length} match${matches.length === 1 ? "" : "es"}` : "No matches found");
          drawMarks(); renderPanel("redact", true);
          if (matches.length) scrollToPage(matches[0].page);
        } catch (err) { handleError(err); }
      };
      $$("[data-del]", body).forEach((b) => (b.onclick = (e) => { e.stopPropagation(); S.pending.splice(+b.dataset.del, 1); drawMarks(); renderPanel("redact", true); }));
      $$(".list-item[data-i]", body).forEach((it) => (it.onclick = () => scrollToPage(S.pending[+it.dataset.i].page)));
      $("[data-clear]", body).onclick = () => { S.pending = []; drawMarks(); renderPanel("redact", true); };
      $("[data-apply]", body).onclick = async () => {
        const n = S.pending.length;
        if (!(await confirmDialog("Apply redactions", `Permanently remove the content in ${n} marked area${n === 1 ? "" : "s"}? You can undo until you close the document, but the downloaded file will not contain the removed content.`, "Apply", true))) return;
        try {
          await op("redact_areas", { areas: S.pending.map(({ page, rect }) => ({ page, rect })), fill: f.fill.value || null, overlay_text: f.overlay.value || null });
          if (f.sanitize.checked) await op("sanitize", { metadata: true, javascript: true, attachments: true, hidden_text: true, thumbnails: true });
          S.pending = []; drawMarks(); renderPanel("redact", true);
          toast(`Applied ${n} redaction${n === 1 ? "" : "s"}`);
        } catch (_) {}
      };
    },

    async comments(body) {
      await refreshAnnotations();
      const items = S.annotations.filter((a) => !["Widget", "Link", "Popup"].includes(a.type));
      body.innerHTML = items.length ? `<div class="list">${items.map((a, i) => `<div class="list-item" data-i="${i}">
          <span style="width:10px;height:10px;border-radius:2px;margin-top:4px;flex:none;background:${a.color || "#999"}"></span>
          <div class="grow"><div>${esc(a.content || a.type)}</div><div class="meta">${esc(a.type)} · page ${a.page + 1}${a.author ? " · " + esc(a.author) : ""}</div></div>
          <button class="icon-btn sm" data-del="${i}" title="Delete">${icon("trash")}</button></div>`).join("")}</div>`
        : `<p class="muted">No comments yet. Use the highlight, note, drawing and shape tools on the left to add some.</p>`;
      $$(".list-item", body).forEach((it) => (it.onclick = () => { const a = items[+it.dataset.i]; scrollToPage(a.page); setTool("select"); S.picked = a; drawMarks(); }));
      $$("[data-del]", body).forEach((b) => (b.onclick = (e) => { e.stopPropagation(); const a = items[+b.dataset.del]; op("delete_annotation", { page: a.page, xref: a.xref }, "Comment deleted").catch(() => {}); }));
    },

    async forms(body) {
      let fields = [];
      try { fields = (await api(docPath("/fields"), { quiet: true })).fields; } catch (e) { handleError(e); }
      body.innerHTML = `
        <div class="actions" style="margin:0 0 12px"><button class="btn block" data-add>${icon("form")}<span>Add a form field</span></button></div>
        ${fields.length ? `<form>${fields.map((f, i) => {
          const name = esc(f.name || `xref:${f.xref}`);
          let input;
          if (f.type === "checkbox" || f.type === "radiobutton") input = `<label class="check"><input type="checkbox" data-k="${i}" ${f.value && f.value !== "Off" ? "checked" : ""} ${f.readonly ? "disabled" : ""}> ${name}</label>`;
          else if (f.options.length) input = `<label class="field"><span>${name}</span><select data-k="${i}" ${f.readonly ? "disabled" : ""}>${["", ...f.options].map((o) => `<option ${o === f.value ? "selected" : ""}>${esc(o)}</option>`).join("")}</select></label>`;
          else if (f.type === "signature") input = `<div class="field"><span>${name}</span><small class="muted">Signature field – use Fill &amp; sign</small></div>`;
          else input = `<label class="field"><span>${name}</span><input type="text" data-k="${i}" value="${esc(f.value)}" ${f.readonly ? "disabled" : ""}></label>`;
          return `<div data-page="${f.page}">${input}</div>`;
        }).join("")}
        <div class="actions"><button class="btn primary" type="submit">Save form values</button></div></form>`
        : `<p class="muted">This document has no form fields. Add fields with the button above, then fill them here.</p>`}
        <hr class="sep"><button class="btn" data-flatten>${icon("flatten")}<span>Flatten form fields</span></button>
        <p class="muted" style="font-size:12px">Flattening turns fields into regular page content so values can no longer be changed.</p>`;
      $("[data-add]", body).onclick = () => setTool("field");
      const form = $("form", body);
      if (form) form.onsubmit = (e) => {
        e.preventDefault();
        const values = {};
        $$("[data-k]", form).forEach((el) => { const f = fields[+el.dataset.k]; values[f.name || `xref:${f.xref}`] = el.type === "checkbox" ? el.checked : el.value; });
        op("fill_form", { values }, "Form saved").catch(() => {});
      };
      $("[data-flatten]", body).onclick = async () => { if (await confirmDialog("Flatten form", "Turn all form fields into static content?", "Flatten")) op("flatten", { annots: false, widgets: true }, "Form flattened").catch(() => {}); };
    },

    organize(body) {
      const sel = selectedPages();
      body.innerHTML = `
        <p class="note">Select pages in the thumbnail bar (Ctrl/Shift-click for several). Drag thumbnails to reorder.</p>
        <p><b>Selected:</b> ${sel.length > 12 ? `${sel.length} pages` : sel.map((p) => p + 1).join(", ")}</p>
        <div class="row2">
          <button class="btn" data-a="rotL">${icon("rotL")}<span>Rotate left</span></button>
          <button class="btn" data-a="rotR">${icon("rotR")}<span>Rotate right</span></button>
          <button class="btn" data-a="dup">${icon("pages")}<span>Duplicate</span></button>
          <button class="btn" data-a="del">${icon("trash")}<span>Delete</span></button>
          <button class="btn" data-a="extract">${icon("export")}<span>Extract</span></button>
          <button class="btn" data-a="blank">${icon("filePlus")}<span>Blank page</span></button>
        </div>
        <hr class="sep">
        <div class="tool-section">Reorder</div>
        <label class="field"><span>New page order</span><input type="text" name="order" placeholder="e.g. 3,1,2,4-10"></label>
        <div class="actions"><button class="btn" data-a="order">Apply order</button><button class="btn" data-a="reverse">Reverse all</button></div>`;
      const act = async (a) => {
        const pages = selectedPages();
        const n = S.doc.page_count;
        try {
          if (a === "rotL" || a === "rotR") await op("rotate", { pages, angle: a === "rotL" ? -90 : 90 });
          if (a === "del") { if (await confirmDialog("Delete pages", `Delete ${pages.length} page${pages.length === 1 ? "" : "s"}?`, "Delete", true)) { S.selected.clear(); await op("delete_pages", { pages }); } }
          if (a === "dup") { const order = []; for (let i = 0; i < n; i++) { order.push(i); if (pages.includes(i)) order.push(i); } await op("reorder", { order }, "Duplicated"); }
          if (a === "extract") await download(docPath("/export/extract"), { pages }, `${docStem()}-extract.pdf`);
          if (a === "blank") await op("insert_blank", { at: Math.max(...pages) + 1 });
          if (a === "reverse") await op("reorder", { order: [...Array(n).keys()].reverse() });
          if (a === "order") {
            const spec = $("[name=order]", body).value;
            const order = [];
            for (const part of spec.split(",").map((s) => s.trim()).filter(Boolean)) {
              const m = part.match(/^(\d+)(?:-(\d+))?$/);
              if (!m) throw new Error(`Invalid entry: ${part}`);
              const a1 = +m[1], b1 = m[2] ? +m[2] : a1;
              for (let k = a1; a1 <= b1 ? k <= b1 : k >= b1; k += a1 <= b1 ? 1 : -1) order.push(k - 1);
            }
            await op("reorder", { order }, "Pages reordered");
          }
        } catch (e) { if (!e.status) toast(e.message, "error"); }
      };
      $$("[data-a]", body).forEach((b) => (b.onclick = () => act(b.dataset.a)));
    },

    merge(body) {
      body.innerHTML = `
        <p class="note">Insert pages from another PDF (or an image, XPS, EPUB…) into this document.</p>
        <form>
          <label class="field"><span>Insert position</span><select name="where"><option value="end">At the end</option><option value="start">At the beginning</option><option value="after">After current page (${S.currentPage + 1})</option></select></label>
          <label class="field"><span>Pages to take from the other file</span><input type="text" name="pages" placeholder="All pages"></label>
          <div class="actions"><button class="btn primary" type="submit">${icon("folder")}<span>Choose file…</span></button></div>
        </form>`;
      const f = $("form", body);
      f.onsubmit = async (e) => {
        e.preventDefault();
        const files = await pickFile(".pdf,application/pdf,image/*,.xps,.epub", true);
        if (!files || !files.length) return;
        let at = f.where.value === "start" ? 0 : f.where.value === "after" ? S.currentPage + 1 : S.doc.page_count;
        for (const file of files) {
          let password = null;
          for (let attempt = 0; attempt < 3; attempt++) {
            const fd = new FormData();
            fd.append("file", file); fd.append("at", at);
            if (f.pages.value.trim()) fd.append("pages", f.pages.value.trim());
            if (password) fd.append("password", password);
            try {
              const snap = await api(docPath("/insert"), { method: "POST", form: fd, busyText: `Inserting ${file.name}…` });
              at += snap.result.added;
              setDoc(snap);
              toast(`Inserted ${snap.result.added} page${snap.result.added === 1 ? "" : "s"} from ${file.name}`);
              break;
            } catch (err) {
              if (/password/i.test(err.message)) { password = await askPassword(file.name); if (password == null) break; continue; }
              handleError(err); break;
            }
          }
        }
      };
    },

    split(body) {
      body.innerHTML = `
        <form>
          <label class="check"><input type="radio" name="mode" value="every" checked> Every <input type="number" name="every" value="1" min="1" style="width:60px;margin:0 4px"> page(s)</label>
          <label class="check"><input type="radio" name="mode" value="ranges"> By ranges</label>
          <label class="field"><span>Ranges (separate files with ;)</span><input type="text" name="ranges" placeholder="1-3; 4-6; 7-"></label>
          <div class="actions"><button class="btn primary" type="submit">${icon("split")}<span>Split &amp; download ZIP</span></button></div>
        </form>
        <hr class="sep">
        <div class="tool-section">Extract</div>
        <form data-extract>${pagesField("Pages to extract", "e.g. 2, 5-7")}<div class="actions"><button class="btn" type="submit">Extract to new PDF</button></div></form>`;
      const f = $("form", body);
      f.ranges.oninput = () => (f.mode.value = "ranges");
      f.onsubmit = (e) => { e.preventDefault(); download(docPath("/export/split"), f.mode.value === "every" ? { every: +f.every.value || 1 } : { ranges: f.ranges.value }, `${docStem()}-split.zip`); };
      const x = $("[data-extract]", body);
      x.onsubmit = (e) => { e.preventDefault(); if (!x.pages.value.trim()) return toast("Enter the pages to extract", "error"); download(docPath("/export/extract"), { pages: x.pages.value }, `${docStem()}-extract.pdf`); };
    },

    watermark(body) {
      body.innerHTML = `<form>
        <label class="field"><span>Text</span><input type="text" name="text" value="CONFIDENTIAL"></label>
        <div class="row2">
          <label class="field"><span>Font size</span><input type="number" name="fontsize" value="60" min="6" max="300"></label>
          <label class="field"><span>Color</span><input type="color" name="color" value="#d61f3a" style="height:36px;width:100%"></label>
          <label class="field"><span>Opacity (%)</span><input type="number" name="opacity" value="25" min="5" max="100"></label>
          <label class="field"><span>Angle</span><input type="number" name="angle" value="45" min="-180" max="180"></label>
        </div>
        <label class="field"><span>Font</span><select name="family"><option value="sans">Sans</option><option value="serif">Serif</option><option value="mono">Mono</option></select></label>
        ${pagesField()}
        <label class="check"><input type="checkbox" name="behind"> Place behind page content</label>
        <div class="actions"><button class="btn primary" type="submit">Add watermark</button></div></form>`;
      const f = $("form", body);
      f.onsubmit = (e) => {
        e.preventDefault();
        op("watermark", { text: f.text.value, fontsize: +f.fontsize.value, color: f.color.value, opacity: +f.opacity.value / 100, angle: +f.angle.value, family: f.family.value, behind: f.behind.checked, pages: f.pages.value || null }, "Watermark added").catch(() => {});
      };
    },

    headerfooter(body) {
      body.innerHTML = `<form>
        <p class="note">Tokens: <code>{page}</code> <code>{total}</code> <code>{bates}</code> <code>{date}</code> <code>{filename}</code></p>
        <div class="tool-section">Header</div>
        <div class="row3"><input type="text" name="header_left" placeholder="Left" class="fld"><input type="text" name="header_center" placeholder="Center" class="fld"><input type="text" name="header_right" placeholder="Right" class="fld"></div>
        <div class="tool-section">Footer</div>
        <div class="row3"><input type="text" name="footer_left" placeholder="Left" class="fld"><input type="text" name="footer_center" placeholder="Center" value="Page {page} of {total}" class="fld"><input type="text" name="footer_right" placeholder="Right" class="fld"></div>
        <div class="row2" style="margin-top:12px">
          <label class="field"><span>Font size</span><input type="number" name="fontsize" value="10" min="4" max="72"></label>
          <label class="field"><span>Margin (pt)</span><input type="number" name="margin" value="28" min="0" max="200"></label>
          <label class="field"><span>Color</span><input type="color" name="color" value="#000000" style="height:36px;width:100%"></label>
          <label class="field"><span>First page number</span><input type="number" name="start_number" value="1"></label>
        </div>
        <div class="tool-section">Bates numbering</div>
        <div class="row2">
          <label class="field"><span>Prefix</span><input type="text" name="bates_prefix" placeholder="ABC"></label>
          <label class="field"><span>Suffix</span><input type="text" name="bates_suffix"></label>
          <label class="field"><span>Start at</span><input type="number" name="bates_start" value="1" min="0"></label>
          <label class="field"><span>Digits</span><input type="number" name="bates_digits" value="6" min="1" max="12"></label>
        </div>
        ${pagesField()}
        <div class="actions"><button class="btn primary" type="submit">Apply</button><button class="btn" type="button" data-bates>Bates preset</button></div></form>`;
      $$(".fld", body).forEach((el) => Object.assign(el.style, { padding: "7px 8px", border: "1px solid var(--border)", borderRadius: "6px", background: "var(--surface-2)", minWidth: 0 }));
      const f = $("form", body);
      $("[data-bates]", body).onclick = () => { f.footer_center.value = ""; f.footer_right.value = "{bates}"; if (!f.bates_prefix.value) f.bates_prefix.value = "DOC"; };
      f.onsubmit = (e) => {
        e.preventDefault();
        const b = { filename: S.doc.filename, pages: f.pages.value || null };
        ["header_left", "header_center", "header_right", "footer_left", "footer_center", "footer_right", "bates_prefix", "bates_suffix", "color"].forEach((k) => (b[k] = f[k].value));
        ["fontsize", "margin", "start_number", "bates_start", "bates_digits"].forEach((k) => (b[k] = +f[k].value));
        op("header_footer", b, "Header & footer added").catch(() => {});
      };
    },

    bookmarks(body) {
      const toc = (S.doc.toc || []).map((t) => [...t]);
      const draw = () => {
        body.innerHTML = `
          <div class="list">${toc.map((t, i) => `<div class="list-item" data-i="${i}" style="padding-left:${8 + (t[0] - 1) * 16}px">
            <div class="grow">${esc(t[1])}<div class="meta">page ${t[2]}</div></div>
            <button class="icon-btn sm" data-in="${i}" title="Indent">›</button><button class="icon-btn sm" data-out="${i}" title="Outdent">‹</button>
            <button class="icon-btn sm" data-del="${i}" title="Delete">${icon("x")}</button></div>`).join("") || '<p class="muted">No bookmarks.</p>'}</div>
          <div class="actions"><button class="btn" data-add>${icon("plus")}<span>Add for page ${S.currentPage + 1}</span></button><button class="btn primary" data-save>Save bookmarks</button></div>`;
        $$(".list-item", body).forEach((it) => (it.onclick = () => scrollToPage(toc[+it.dataset.i][2] - 1)));
        $$("[data-del]", body).forEach((b) => (b.onclick = (e) => { e.stopPropagation(); toc.splice(+b.dataset.del, 1); draw(); }));
        $$("[data-in]", body).forEach((b) => (b.onclick = (e) => { e.stopPropagation(); const i = +b.dataset.in; if (i > 0 && toc[i][0] <= toc[i - 1][0]) toc[i][0]++; draw(); }));
        $$("[data-out]", body).forEach((b) => (b.onclick = (e) => { e.stopPropagation(); const i = +b.dataset.out; if (toc[i][0] > 1) toc[i][0]--; draw(); }));
        $("[data-add]", body).onclick = async () => {
          const r = await promptDialog("Add bookmark", "Title", `Page ${S.currentPage + 1}`);
          if (!r) return;
          toc.push([1, r.value, S.currentPage + 1]); draw();
        };
        $("[data-save]", body).onclick = () => op("bookmarks", { toc }, "Bookmarks saved").catch(() => {});
        hydrateIcons(body);
      };
      draw();
    },

    protect(body) {
      body.innerHTML = `<form>
        <p class="note">Encrypts the downloaded file with AES-256.</p>
        <label class="field"><span>Password to open</span><input type="password" name="user" autocomplete="new-password"></label>
        <label class="field"><span>Permissions password (owner)</span><input type="password" name="owner" autocomplete="new-password" placeholder="Defaults to the open password"></label>
        <div class="tool-section">Allow</div>
        <label class="check"><input type="checkbox" name="print" checked> Printing</label>
        <label class="check"><input type="checkbox" name="copy" checked> Copying text and images</label>
        <label class="check"><input type="checkbox" name="modify"> Editing and page assembly</label>
        <label class="check"><input type="checkbox" name="annotate" checked> Comments and form filling</label>
        <div class="actions"><button class="btn primary" type="submit">${icon("lock")}<span>Download protected PDF</span></button></div>
      </form>`;
      const f = $("form", body);
      f.onsubmit = (e) => {
        e.preventDefault();
        if (!f.user.value && !f.owner.value) return toast("Enter at least one password", "error");
        const permissions = ["print", "copy", "modify", "annotate"].filter((k) => f[k].checked);
        download(docPath("/download"), { user_password: f.user.value, owner_password: f.owner.value, permissions }, `${docStem()}-protected.pdf`);
      };
    },

    sanitize(body) {
      body.innerHTML = `<form>
        <p class="note">Remove information that is not visible on the page but stays in the file.</p>
        <label class="check"><input type="checkbox" name="metadata" checked> Document metadata (author, title, XMP)</label>
        <label class="check"><input type="checkbox" name="javascript" checked> JavaScript and actions</label>
        <label class="check"><input type="checkbox" name="attachments" checked> Attached and embedded files</label>
        <label class="check"><input type="checkbox" name="hidden_text" checked> Hidden text</label>
        <label class="check"><input type="checkbox" name="thumbnails" checked> Embedded thumbnails</label>
        <label class="check"><input type="checkbox" name="links"> Links</label>
        <label class="check"><input type="checkbox" name="reset_forms"> Reset form fields</label>
        <div class="actions"><button class="btn primary" type="submit">Remove hidden information</button></div></form>`;
      const f = $("form", body);
      f.onsubmit = (e) => {
        e.preventDefault();
        const b = {};
        ["metadata", "javascript", "attachments", "hidden_text", "thumbnails", "links", "reset_forms"].forEach((k) => (b[k] = f[k].checked));
        op("sanitize", b, "Hidden information removed").catch(() => {});
      };
    },

    optimize(body) {
      body.innerHTML = `<form>
        <p class="note">Current size: <b>${(S.doc.size / 1024 / 1024).toFixed(2)} MB</b></p>
        <label class="field"><span>Downsample images to</span><select name="dpi"><option value="72">72 dpi (smallest)</option><option value="150" selected>150 dpi (screen)</option><option value="220">220 dpi (print)</option><option value="0">Keep images</option></select></label>
        <label class="field"><span>JPEG quality</span><input type="number" name="quality" value="75" min="10" max="100"></label>
        <label class="check"><input type="checkbox" name="fonts" checked> Subset embedded fonts</label>
        <div class="actions"><button class="btn primary" type="submit">Compress</button><button class="btn" type="button" data-dl>Download compressed</button></div></form>`;
      const f = $("form", body);
      f.onsubmit = (e) => {
        e.preventDefault();
        const before = S.doc.size;
        op("optimize", { image_dpi: +f.dpi.value || null, image_quality: +f.quality.value, subset_fonts: f.fonts.checked },
          () => `Size: ${(before / 1048576).toFixed(2)} MB → ${(S.doc.size / 1048576).toFixed(2)} MB`).catch(() => {});
      };
      $("[data-dl]", body).onclick = () => download(docPath("/download"), { compress: true }, `${docStem()}-compressed.pdf`);
    },

    flatten(body) {
      body.innerHTML = `<p class="note">Flattening burns comments, markups and form fields into the page so they can no longer be edited or removed.</p>
        <label class="check"><input type="checkbox" id="flA" checked> Comments and markups</label>
        <label class="check"><input type="checkbox" id="flW" checked> Form fields</label>
        <div class="actions"><button class="btn primary" data-go>Flatten</button></div>`;
      $("[data-go]", body).onclick = () => op("flatten", { annots: $("#flA").checked, widgets: $("#flW").checked }, "Flattened").catch(() => {});
    },

    export(body) {
      body.innerHTML = `
        <div class="tool-section">Images</div>
        <form data-img><div class="row2"><label class="field"><span>Format</span><select name="format"><option value="png">PNG</option><option value="jpg">JPEG</option></select></label>
          <label class="field"><span>Resolution</span><select name="dpi"><option>72</option><option selected>150</option><option>300</option></select></label></div>
          ${pagesField()}<div class="actions"><button class="btn" type="submit">Export images (ZIP)</button></div></form>
        <hr class="sep"><div class="tool-section">Text</div>
        <div class="actions"><button class="btn" data-txt>Plain text (.txt)</button><button class="btn" data-html>HTML</button></div>
        <hr class="sep"><div class="tool-section">PDF</div>
        <div class="actions"><button class="btn" data-pdf>Download PDF</button><button class="btn" data-new>New PDF from images…</button></div>`;
      const fi = $("[data-img]", body);
      fi.onsubmit = (e) => { e.preventDefault(); download(docPath("/export/images"), { format: fi.format.value, dpi: +fi.dpi.value, pages: fi.pages.value || null }, `${docStem()}-images.zip`); };
      $("[data-txt]", body).onclick = () => download(docPath("/export/text"), {}, `${docStem()}.txt`);
      $("[data-html]", body).onclick = () => download(docPath("/export/html"), {}, `${docStem()}.html`);
      $("[data-pdf]", body).onclick = () => download(docPath("/download"), {}, `${docStem()}.pdf`);
      $("[data-new]", body).onclick = fromImages;
    },

    ocr(body) {
      body.innerHTML = S.caps.ocr ? `<form>
          <p class="note">Adds an invisible, searchable text layer to scanned pages. Pages that already contain text are skipped.</p>
          <label class="field"><span>Language (Tesseract code)</span><input type="text" name="lang" value="eng" placeholder="eng, deu, fra, eng+lav…"></label>
          ${pagesField()}
          <label class="check"><input type="checkbox" name="all"> Also process pages that already have text</label>
          <div class="actions"><button class="btn primary" type="submit">Recognize text</button></div></form>`
        : `<p class="note warn">OCR needs <b>Tesseract</b> installed on this computer.<br><br>Debian/Ubuntu: <code>sudo apt install tesseract-ocr</code><br>macOS: <code>brew install tesseract</code><br><br>Restart the app afterwards.</p>`;
      const f = $("form", body);
      if (f) f.onsubmit = (e) => {
        e.preventDefault();
        op("ocr", { language: f.lang.value || "eng", pages: f.pages.value || null, skip_text_pages: !f.all.checked }, (n) => `Recognized text on ${n} page${n === 1 ? "" : "s"}`).catch(() => {});
      };
    },

    compare(body) {
      body.innerHTML = `<p class="note">Compare the text of this document with another PDF.</p>
        <div class="actions"><button class="btn primary" data-pick>${icon("folder")}<span>Choose file to compare…</span></button></div><div data-out></div>`;
      $("[data-pick]", body).onclick = async () => {
        const file = await pickFile(".pdf,application/pdf");
        if (!file) return;
        const fd = new FormData(); fd.append("file", file);
        try {
          const r = await api(docPath("/compare"), { method: "POST", form: fd, busyText: "Comparing…" });
          const out = $("[data-out]", body);
          if (r.identical) { out.innerHTML = `<p><b>No text differences found.</b></p>`; return; }
          out.innerHTML = `<p><b>${r.pages.length}</b> page(s) differ. This: ${r.page_count[0]} pages, other: ${r.page_count[1]} pages.</p>` +
            r.pages.map((p) => `<div class="tool-section">Page ${p.page + 1}</div>` + p.changes.map((c) =>
              c.old.map((l) => `<span class="diff-old">${esc(l)}</span>`).join("") + c.new.map((l) => `<span class="diff-new">${esc(l)}</span>`).join("")).join('<div style="height:6px"></div>')).join("");
        } catch (e) { handleError(e); }
      };
    },

    properties(body) {
      const md = S.doc.metadata || {};
      body.innerHTML = `<form>
        ${["title", "author", "subject", "keywords", "creator", "producer"].map((k) => `<label class="field"><span>${k[0].toUpperCase() + k.slice(1)}</span><input type="text" name="${k}" value="${esc(md[k] || "")}"></label>`).join("")}
        <p class="muted">${S.doc.page_count} pages · ${(S.doc.size / 1024).toFixed(0)} KB · ${S.doc.is_form ? "has form fields" : "no form fields"}</p>
        <div class="actions"><button class="btn primary" type="submit">Save properties</button></div></form>`;
      const f = $("form", body);
      f.onsubmit = (e) => { e.preventDefault(); const b = {}; ["title", "author", "subject", "keywords", "creator", "producer"].forEach((k) => (b[k] = f[k].value)); op("metadata", b, "Properties saved").catch(() => {}); };
    },
  };

  // ------------------------------------------------------------------ actions & keyboard
  const BRAND = () => Object.assign({
    product: "Vantage PDF Editor", publisher: "DTR Networks, Inc.",
    website: "https://dtrvantage.com/tools/pdf-editor/", toolkit_url: "https://dtrvantage.com/tools/",
    vantage_url: "https://dtrvantage.com/", source_url: "https://github.com/dainisf/PDFScout", license: "GNU AGPL-3.0-or-later",
  }, (S.caps && S.caps.brand) || {});

  function aboutDialog() {
    const b = BRAND();
    const where = desktop() ? "Windows app" : (window.PDFSCOUT_WEB ? "Runs in your browser" : "Local server");
    return modal(`<div class="about">
      <img src="static/icon.png" alt="">
      <h3>${esc(b.product)}</h3>
      <div class="ver">Version ${esc(S.caps.version || "")} · ${esc(where)}</div>
      <p>Edit, redact, sign and organize PDFs. Your files are processed on this computer and never uploaded.</p>
      <div class="links">
        <a href="${esc(b.toolkit_url)}" target="_blank" rel="noopener">Vantage Toolkit</a>
        <a href="${esc(b.website)}" target="_blank" rel="noopener">Product page</a>
        <a href="${esc(b.vantage_url)}" target="_blank" rel="noopener">Vantage by DTR Networks</a>
        <a href="${esc(b.source_url)}" target="_blank" rel="noopener">Source code</a>
      </div>
      <div class="legal">© ${new Date().getFullYear()} ${esc(b.publisher)}. Free software under the ${esc(b.license)} license.<br>
        Built with MuPDF/PyMuPDF (© Artifex Software, AGPL). Provided without warranty.</div>
      <div class="actions" style="justify-content:center;margin-top:16px"><button class="btn primary" data-close>Close</button></div>
    </div>`);
  }

  const ACTIONS = {
    about: aboutDialog,
    open: async () => {
      if (isDirty() && !(await confirmDialog("Open another file", "Your changes to the current document haven't been saved. Open another file anyway?", "Open"))) return;
      desktop() ? nativeOpen() : $("#fileOpen").click();
    },
    new: newBlank,
    "from-images": fromImages,
    save: () => S.doc && download(docPath("/download"), {}, `${docStem()}.pdf`),
    undo: async () => { if (!S.doc?.can_undo) return; try { setDoc(await api(docPath("/undo"), { method: "POST", quiet: true })); } catch (e) { handleError(e); } },
    redo: async () => { if (!S.doc?.can_redo) return; try { setDoc(await api(docPath("/redo"), { method: "POST", quiet: true })); } catch (e) { handleError(e); } },
    "zoom-in": () => zoomTo(Math.round((S.zoom + (S.zoom >= 1 ? 0.25 : 0.1)) * 100) / 100),
    "zoom-out": () => zoomTo(Math.round((S.zoom - (S.zoom > 1 ? 0.25 : 0.1)) * 100) / 100),
    "zoom-fit": fitWidth,
    "toggle-panel": () => { const closed = document.body.classList.toggle("panel-closed"); if (!closed && !S.panel) renderPanel(null); },
    "search-next": () => stepSearch(1),
    "search-prev": () => stepSearch(-1),
    "pages-rotate-left": () => op("rotate", { pages: selectedPages(), angle: -90 }).catch(() => {}),
    "pages-rotate-right": () => op("rotate", { pages: selectedPages(), angle: 90 }).catch(() => {}),
    "pages-delete": async () => { const p = selectedPages(); if (await confirmDialog("Delete pages", `Delete page${p.length > 1 ? "s" : ""} ${p.map((x) => x + 1).join(", ")}?`, "Delete", true)) { S.selected.clear(); op("delete_pages", { pages: p }).catch(() => {}); } },
    "pages-insert-blank": () => op("insert_blank", { at: S.currentPage + 1 }).catch(() => {}),
  };
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-action]");
    if (!b || b.disabled) return;
    if (b.tagName === "A") e.preventDefault();
    ACTIONS[b.dataset.action]?.();
  });

  $("#panelBack").onclick = () => { S.panel = null; renderPanel(null); };
  $("#fileOpen").onchange = (e) => { openFile(e.target.files[0]); e.target.value = ""; };
  $("#pageInput").addEventListener("change", (e) => { const n = parseInt(e.target.value, 10); if (n) scrollToPage(n - 1); });
  $("#pageInput").addEventListener("keydown", (e) => { if (e.key === "Enter") e.target.blur(); });
  $("#searchInput").addEventListener("input", (e) => { clearTimeout(searchTimer); searchTimer = setTimeout(() => runSearch(e.target.value.trim()), 300); });
  $("#searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); e.shiftKey ? stepSearch(-1) : (S.search.matches.length ? stepSearch(1) : runSearch(e.target.value.trim())); } if (e.key === "Escape") { e.target.value = ""; runSearch(""); } });
  $("#optBold").onclick = () => $("#optBold").classList.toggle("on");
  $("#optItalic").onclick = () => $("#optItalic").classList.toggle("on");
  // keep inline editors' preview in sync with option changes
  ["#optFontSize", "#optColor", "#optFamily"].forEach((s) => $(s).addEventListener("input", () => {
    const ed = $(".inline-editor"); if (!ed) return; const st = styleOpts(); const k = S.zoom * PT;
    Object.assign(ed.style, { fontSize: `${st.fontsize * k}px`, color: st.color, fontFamily: st.family === "serif" ? "Times New Roman, serif" : st.family === "mono" ? "Courier New, monospace" : "Helvetica, Arial, sans-serif" });
  }));

  document.addEventListener("keydown", (e) => {
    const mod = e.ctrlKey || e.metaKey;
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
    if (mod && e.key.toLowerCase() === "o") { e.preventDefault(); ACTIONS.open(); return; }
    if (!S.doc) return;
    if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); ACTIONS.save(); return; }
    if (mod && e.key.toLowerCase() === "f") { e.preventDefault(); $("#searchInput").focus(); $("#searchInput").select(); return; }
    if (typing) return;
    if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? ACTIONS.redo() : ACTIONS.undo(); return; }
    if (mod && e.key.toLowerCase() === "y") { e.preventDefault(); ACTIONS.redo(); return; }
    if (mod && (e.key === "=" || e.key === "+")) { e.preventDefault(); ACTIONS["zoom-in"](); return; }
    if (mod && e.key === "-") { e.preventDefault(); ACTIONS["zoom-out"](); return; }
    if (e.key === "Escape") { closeEditors(); if (S.tool !== "select") setTool("select"); else if (S.picked) { S.picked = null; drawMarks(); } return; }
    if ((e.key === "Delete" || e.key === "Backspace") && S.picked) {
      e.preventDefault(); const a = S.picked; S.picked = null;
      op("delete_annotation", { page: a.page, xref: a.xref }, "Comment deleted").catch(() => {});
      return;
    }
    if (e.key === "PageDown" || (e.key === "ArrowRight" && !mod)) { scrollToPage(S.currentPage + 1); }
    if (e.key === "PageUp" || (e.key === "ArrowLeft" && !mod)) { scrollToPage(S.currentPage - 1); }
  });

  // drag & drop open
  let dragDepth = 0;
  window.addEventListener("dragenter", (e) => { if (e.dataTransfer.types.includes("Files")) { dragDepth++; document.body.classList.add("dragging"); } });
  window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; document.body.classList.remove("dragging"); } });
  window.addEventListener("dragover", (e) => { if (e.dataTransfer.types.includes("Files")) e.preventDefault(); });
  window.addEventListener("drop", (e) => {
    if (!e.dataTransfer.files.length) return;
    e.preventDefault(); dragDepth = 0; document.body.classList.remove("dragging");
    openFile(e.dataTransfer.files[0]);
  });
  window.addEventListener("resize", () => { clearTimeout(window._rz); window._rz = setTimeout(() => S.doc && drawMarks(), 150); });

  // ------------------------------------------------------------------ boot
  async function boot() {
    hydrateIcons();
    renderToolstrip();
    document.body.classList.add("panel-closed");
    renderPanel(null);
    setTool("select");
    try { S.caps = await api("/api/capabilities", { quiet: true }); } catch (_) {}
    const onDesktop = async () => {
      document.body.classList.add("desktop");
      $('[data-action="save"] span').textContent = "Save";
      $('[data-action="save"]').title = "Save a copy (Ctrl+S)";
      $(".drop .muted").textContent = "Everything stays on this computer.";
      try { const f = await desktop().initial_file(); if (f) nativeOpen(f); } catch (_) {}
    };
    if (desktop()) onDesktop(); else window.addEventListener("pywebviewready", onDesktop, { once: true });
  }
  boot();
})();
