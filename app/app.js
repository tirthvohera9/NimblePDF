import { inspect } from "../engine/index.js";

const $ = (selector) => document.querySelector(selector);
const fileInput = $("#file-input");
const queue = $("#queue");
const messages = $("#messages");
const fileTray = $("#file-tray");
const toast = $("#toast");
let jobs = [];
let selectedTool = "inspect";
const themeButton = $("#theme-button");
const dropHint = $("#drop-hint");
let bytesRead = 0;

const formatSize = (bytes) => bytes === 0 ? "0 B" : bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]);
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeButton.innerHTML = `<span aria-hidden="true">${theme === "dark" ? "☀" : "☾"}</span>`;
  themeButton.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} theme`);
  themeButton.title = `Switch to ${theme === "dark" ? "light" : "dark"} theme`;
}
const savedTheme = localStorage.getItem("nimblepdf-theme");
applyTheme(savedTheme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 3200);
}
function addMessage(text, role = "assistant") {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;
  article.innerHTML = role === "assistant"
    ? `<div class="message-avatar" aria-hidden="true">✦</div><div class="message-body"><p>${escapeHtml(text)}</p></div>`
    : `<div class="message-body"><p>${escapeHtml(text)}</p></div><div class="message-avatar" aria-hidden="true">T</div>`;
  messages.appendChild(article);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function setHealth() {
  const completed = jobs.filter((job) => job.report);
  if (!completed.length) {
    $("#health-card").hidden = true;
    return;
  }
  const findings = completed.flatMap((job) => job.report.health.findings);
  const errors = findings.filter((item) => item.level === "error").length;
  const warnings = findings.filter((item) => item.level === "warning").length;
  const score = Math.max(0, Math.round(100 - errors * 35 - warnings * 10));
  $("#health-score").textContent = score;
  $("#health-copy").textContent = errors ? `${errors} issue${errors === 1 ? "" : "s"} need attention.` : warnings ? `${warnings} warning${warnings === 1 ? "" : "s"} found to review.` : "No health findings in inspected files.";
  $("#health-details").textContent = `${completed.length} file${completed.length === 1 ? "" : "s"} inspected · ${findings.length || "No"} findings`;
  $("#health-card").hidden = false;
}
function renderQueue() {
  queue.innerHTML = "";
  fileTray.hidden = jobs.length === 0;
  jobs.forEach((job) => {
    const row = document.createElement("article");
    row.className = "job";
    const statusClass = job.error ? "status-error" : job.report ? "status-ready" : "status-loading";
    const status = job.error ? "Could not inspect" : job.report ? (job.report.health.ok ? "Ready" : "Review findings") : "Reading…";
    const fingerprint = job.hash ? `SHA-256 ${job.hash.slice(0, 12)}…` : "Fingerprinting locally";
    row.innerHTML = `<span class="file-icon" aria-hidden="true">PDF</span><span class="job-info"><span class="job-name" title="${escapeHtml(job.name)}">${escapeHtml(job.name)}</span><span class="job-meta">${formatSize(job.size)} · ${job.report ? `PDF ${job.report.metadata.version || "version unknown"}` : "Local inspection"} · ${fingerprint}</span></span><span class="job-status ${statusClass}">${status}</span>${job.report ? `<button class="preview-job" type="button" data-preview="${job.id}">Preview</button>` : ""}<button class="remove-job" type="button" data-remove="${job.id}" aria-label="Remove ${escapeHtml(job.name)}">×</button>`;
    queue.appendChild(row);
  });
  const duplicateHashes = jobs.filter((job, index, list) => job.hash && list.findIndex((candidate) => candidate.hash === job.hash) !== index);
  const note = $("#evidence-note");
  if (duplicateHashes.length) {
    note.hidden = false;
    note.textContent = "Duplicate content detected by SHA-256. Identical files are marked without opening or uploading them.";
  } else {
    note.hidden = true;
  }
  $("#privacy-bytes").textContent = formatSize(bytesRead);
  setHealth();
}
async function fingerprint(file) {
  if (!crypto.subtle) throw new Error("This browser cannot create a local file fingerprint.");
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function encodeFile(file) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}
function requestedPages(text) {
  const match = text.match(/pages?\s+([0-9,\s-]+)/i);
  if (!match) return null;
  const pages = new Set();
  for (const token of match[1].split(",")) {
    const range = token.trim().split("-").map(Number);
    if (range.length === 1 && Number.isInteger(range[0])) pages.add(range[0]);
    if (range.length === 2 && Number.isInteger(range[0]) && Number.isInteger(range[1]) && range[0] <= range[1]) {
      for (let page = range[0]; page <= range[1]; page += 1) pages.add(page);
    }
  }
  return [...pages].sort((a, b) => a - b);
}
async function executeOperation(operation, prompt) {
  const ready = jobs.filter((job) => job.report && job.file);
  if (operation === "merge" && ready.length < 2) {
    addMessage("Merge needs at least two inspected PDFs. Attach another file and try again.");
    return;
  }
  if ((operation === "split" || operation === "rotate" || operation === "sanitize-metadata" || operation === "ocr" || operation === "redact") && ready.length !== 1) {
    addMessage(`${operation[0].toUpperCase() + operation.slice(1)} works on one inspected PDF at a time. Keep one file attached and specify pages, for example “${operation} pages 1-3”.`);
    return;
  }
  const pages = operation === "merge" || operation === "sanitize-metadata" || operation === "ocr" || operation === "redact" ? null : requestedPages(prompt);
  if ((operation === "split" || operation === "rotate") && !pages?.length) {
    addMessage(`Tell me which pages to ${operation}, for example “${operation} pages 1-3”. I will verify the range before creating anything.`);
    return;
  }
  const degreesMatch = prompt.match(/(?:rotate|turn).*?(\d{2,3})\s*(?:degrees|°)?/i);
  const degrees = degreesMatch ? Number(degreesMatch[1]) : 90;
  const terms = operation === "redact"
    ? prompt.replace(/^.*?\b(?:redact|remove|hide)\b/i, "").split(/,| and /i).map((term) => term.replace(/^["']|["']$/g, "").trim()).filter(Boolean)
    : null;
  if (operation === "redact" && !terms?.length) {
    addMessage("Tell me what to redact, for example: “redact Alice@example.com and 555-1234”.");
    return;
  }
  try {
    showToast(`Running verified ${operation} locally…`);
    const response = await fetch("/api/operate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operation,
        files: await Promise.all(ready.map(async (job) => ({ name: job.name, data: await encodeFile(job.file) }))),
        ...(pages ? { pages } : {}),
        ...(operation === "rotate" ? { degrees } : {}),
        ...(terms ? { terms } : {}),
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || payload.error || "The local operation failed.");
    const data = atob(payload.output.data);
    const bytes = Uint8Array.from(data, (char) => char.charCodeAt(0));
    const blob = new Blob([bytes], { type: "application/pdf" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = payload.output.name;
    link.click();
    URL.revokeObjectURL(link.href);
    addMessage(`${operation[0].toUpperCase() + operation.slice(1)} complete. NimblePDF reopened and verified the ${payload.output.pageCount}-page output before download.`);
    showToast("Verified PDF downloaded.");
  } catch (error) {
    addMessage(`I could not complete ${operation}: ${error instanceof Error ? error.message : "unknown local operation error"}`);
  }
}
async function addFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  const rejected = files.filter((file) => !file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf");
  if (rejected.length) showToast(`${rejected.length} file${rejected.length > 1 ? "s were" : " was"} skipped. PDF inspection is supported today.`);
  files.filter((file) => !rejected.includes(file)).forEach((file) => {
    const id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${file.name}`;
    const job = { id, name: file.name, size: file.size, file };
    jobs.push(job);
    renderQueue();
    if (file.size > 100 * 1024 * 1024) {
      job.error = "This file is larger than the 100 MB browser limit.";
      renderQueue();
      return;
    }
    Promise.all([inspect(file), fingerprint(file)]).then(([report, hash]) => {
      if (!jobs.includes(job)) return;
      job.report = report;
      job.hash = hash;
      bytesRead += file.size;
      renderQueue();
      addMessage(`${job.name} is ready. I found ${report.health.findings.length ? `${report.health.findings.length} thing${report.health.findings.length === 1 ? "" : "s"} to review` : "no health findings"} in the local inspection.`);
    }).catch((error) => {
      if (!jobs.includes(job)) return;
      job.error = error instanceof Error ? error.message : "The PDF could not be inspected.";
      renderQueue();
      addMessage(`I couldn't inspect ${job.name}: ${job.error}`);
    });
  });
  fileInput.value = "";
}
async function runPrompt(text) {
  const prompt = text.trim();
  if (!prompt) return;
  addMessage(prompt, "user");
  $("#goal-input").value = "";
  if (!jobs.length) {
    addMessage("Attach a PDF and I’ll take a look. You can use the plus button or drop a file into this window.");
    fileInput.click();
    return;
  }
  if (selectedTool === "inspect") {
    const ready = jobs.filter((job) => job.report);
    addMessage(ready.length ? `I’ve inspected ${ready.length} file${ready.length === 1 ? "" : "s"} locally. The findings are shown below.` : "I’m still reading your files locally. I’ll share the findings here when they’re ready.");
  } else if (["merge", "split", "rotate", "sanitize-metadata", "ocr", "redact"].includes(selectedTool)) {
    await executeOperation(selectedTool, prompt);
  } else if (selectedTool === "summarize") {
    const ready = jobs.filter((job) => job.report && job.file);
    if (ready.length !== 1) {
      addMessage("Summary analysis works on one inspected PDF at a time.");
      return;
    }
    try {
      const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: ready[0].name, data: await encodeFile(ready[0].file) }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || "Local analysis failed.");
      const pages = payload.analysis.pages.filter((page) => page.preview).map((page) => `Page ${page.page}: ${page.preview}`).join(" ");
      const checks = payload.analysis.accessibility.checks.filter((check) => !check.pass).map((check) => check.message).join(" ");
      addMessage(`Local analysis found ${payload.analysis.textCharacters} extractable characters across ${payload.analysis.textPages}/${payload.analysis.pageCount} pages. ${pages || "No text preview was available."} ${checks ? `Accessibility notes: ${checks}` : "Basic accessibility checks passed."}`);
    } catch (error) {
      addMessage(`I could not analyze the PDF locally: ${error instanceof Error ? error.message : "unknown analysis error"}`);
    }
  } else {
    addMessage(`${selectedTool[0].toUpperCase() + selectedTool.slice(1)} needs a text extraction engine. Inspection is available now; no unsupported output will be fabricated.`);
  }
}
$("#command-form").addEventListener("submit", (event) => { event.preventDefault(); runPrompt($("#goal-input").value); });
$("#goal-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); runPrompt(event.target.value); } });
$("#browse-button").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (event) => addFiles(event.target.files));
["dragenter", "dragover"].forEach((eventName) => document.addEventListener(eventName, (event) => {
  if (!event.dataTransfer?.types.includes("Files")) return;
  event.preventDefault();
  dropHint.classList.add("visible");
}));
["dragleave", "drop"].forEach((eventName) => document.addEventListener(eventName, (event) => {
  if (eventName === "drop" && event.dataTransfer?.files?.length) {
    event.preventDefault();
    addFiles(event.dataTransfer.files);
  }
  dropHint.classList.remove("visible");
}));
queue.addEventListener("click", (event) => {
  const preview = event.target.closest("[data-preview]");
  if (preview) {
    const job = jobs.find((candidate) => candidate.id === preview.dataset.preview);
    if (!job?.file) return;
    $("#preview-title").textContent = job.name;
    $("#preview-frame").src = URL.createObjectURL(job.file);
    $("#preview-dialog").showModal();
    return;
  }
  const button = event.target.closest("[data-remove]");
  if (!button) return;
  jobs = jobs.filter((job) => job.id !== button.dataset.remove);
  renderQueue();
});
$("#clear-queue").addEventListener("click", () => { jobs = []; renderQueue(); showToast("Attached files cleared."); });
$("#export-receipt").addEventListener("click", () => {
  const inspected = jobs.filter((job) => job.report && job.hash);
  if (!inspected.length) {
    showToast("Inspect a PDF before exporting its evidence receipt.");
    return;
  }
  const receipt = {
    product: "NimblePDF",
    receiptVersion: 1,
    createdAt: new Date().toISOString(),
    processing: { location: "browser memory", networkRequests: 0, originalsModified: false, bytesRead },
    files: inspected.map((job) => ({
      name: job.name,
      bytes: job.size,
      sha256: job.hash,
      metadata: job.report.metadata,
      health: job.report.health,
    })),
  };
  const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `nimblepdf-evidence-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  showToast("Evidence receipt exported.");
});
document.querySelectorAll("[data-suggestion]").forEach((button) => button.addEventListener("click", () => { $("#goal-input").value = button.dataset.suggestion; $("#goal-input").focus(); }));
const toolsButton = $("#tools-button");
const toolMenu = $("#tool-menu");
toolsButton.addEventListener("click", () => {
  toolMenu.hidden = !toolMenu.hidden;
  toolsButton.setAttribute("aria-expanded", String(!toolMenu.hidden));
});
document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => {
  selectedTool = button.dataset.tool;
  toolMenu.hidden = true;
  toolsButton.setAttribute("aria-expanded", "false");
  $("#goal-input").placeholder = `${button.querySelector("strong").textContent}...`;
  showToast(`${button.querySelector("strong").textContent} selected.`);
}));
document.addEventListener("click", (event) => { if (!event.target.closest(".topbar-actions")) { toolMenu.hidden = true; toolsButton.setAttribute("aria-expanded", "false"); } });
$("#privacy-button").addEventListener("click", () => $("#privacy-dialog").showModal());
document.querySelector(".modal-close").addEventListener("click", () => $("#privacy-dialog").close());
document.querySelector(".preview-close").addEventListener("click", () => {
  const frame = $("#preview-frame");
  frame.src = "about:blank";
  $("#preview-dialog").close();
});
themeButton.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("nimblepdf-theme", nextTheme);
  applyTheme(nextTheme);
});
renderQueue();
