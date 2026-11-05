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
    row.innerHTML = `<span class="file-icon" aria-hidden="true">PDF</span><span class="job-info"><span class="job-name" title="${escapeHtml(job.name)}">${escapeHtml(job.name)}</span><span class="job-meta">${formatSize(job.size)} · ${job.report ? `PDF ${job.report.metadata.version || "version unknown"}` : "Local inspection"} · ${fingerprint}</span></span><span class="job-status ${statusClass}">${status}</span><button class="remove-job" type="button" data-remove="${job.id}" aria-label="Remove ${escapeHtml(job.name)}">×</button>`;
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
async function addFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  const rejected = files.filter((file) => !file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf");
  if (rejected.length) showToast(`${rejected.length} file${rejected.length > 1 ? "s were" : " was"} skipped. PDF inspection is supported today.`);
  files.filter((file) => !rejected.includes(file)).forEach((file) => {
    const id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${file.name}`;
    const job = { id, name: file.name, size: file.size };
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
function runPrompt(text) {
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
  } else {
    addMessage(`${selectedTool[0].toUpperCase() + selectedTool.slice(1)} is on the roadmap. I can inspect your PDFs today without uploading or modifying them.`);
  }
}
$("#command-form").addEventListener("submit", (event) => { event.preventDefault(); runPrompt($("#goal-input").value); });
$("#goal-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); runPrompt(event.target.value); } });
$("#browse-button").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (event) => addFiles(event.target.files));
queue.addEventListener("click", (event) => {
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
themeButton.addEventListener("click", () => {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("nimblepdf-theme", nextTheme);
  applyTheme(nextTheme);
});
renderQueue();
