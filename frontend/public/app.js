// Analyst frontend - Phase 1.
"use strict";

const $ = (id) => document.getElementById(id);
let state = {
  workspaceId: null,
  workspaceName: "Zone Review",
};

async function loadHealth() {
  const badge = $("provider-badge");
  try {
    const res = await fetch("/health");
    const body = await res.json();
    const { provider, model, key_configured: keyed } = body.data;
    if (!keyed) {
      badge.textContent = "no API key - set one in .env";
      badge.classList.add("stub");
    } else {
      badge.textContent = `${provider} · ${model}`;
    }
  } catch {
    badge.textContent = "backend unreachable";
    badge.classList.add("stub");
  }
}

function setStatus(id, msg) {
  const el = $(id);
  el.textContent = msg;
  el.hidden = false;
}

function clearStatus(id) {
  const el = $(id);
  el.textContent = "";
  el.hidden = true;
}

async function ensureWorkspaceId() {
  if (state.workspaceId) {
    return state.workspaceId;
  }
  const name = ($("workspace-name")?.value || "Untitled workspace").trim() || "Untitled workspace";
  const res = await fetch("/workspaces", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body?.detail?.message || `HTTP ${res.status}`);
  }
  const data = body.data || body;
  state.workspaceId = data.id;
  state.workspaceName = data.name || name;
  setStatus("workspace-id", `Workspace: ${state.workspaceName} (${state.workspaceId})`);
  return state.workspaceId;
}

async function uploadDataset() {
  const fileInput = $("dataset-file");
  const btn = $("upload-btn");
  const file = fileInput.files?.[0];
  if (!file) {
    setStatus("upload-error", "Choose a CSV file first.");
    return;
  }
  clearStatus("upload-error");
  clearStatus("upload-status");
  btn.disabled = true;
  setStatus("upload-status", "Uploading...");
  try {
    const workspaceId = await ensureWorkspaceId();
    const form = new FormData();
    form.append("file", file);
    form.append("title", file.name);
    form.append("workspace_id", workspaceId);
    const res = await fetch(`/workspaces/${workspaceId}/datasets`, {
      method: "POST",
      body: form,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body?.detail?.message || `HTTP ${res.status}`);
    }
    setStatus("upload-status", `Uploaded ${file.name}`);
  } catch (err) {
    setStatus("upload-error", err.message || "Upload failed.");
    clearStatus("upload-status");
  } finally {
    btn.disabled = false;
  }
}

async function askQuestion() {
  const question = $("question").value.trim();
  const insights = $("insights-toggle").checked;
  const btn = $("ask-btn");
  const status = $("ask-status");
  const errBox = $("ask-error");
  if (!question) {
    errBox.textContent = "Type a question first.";
    errBox.hidden = false;
    return;
  }
  errBox.hidden = true;
  $("result-card").hidden = true;
  btn.disabled = true;
  status.textContent = "Thinking...";
  status.hidden = false;
  try {
    const workspaceId = await ensureWorkspaceId();
    const res = await fetch(`/workspaces/${workspaceId}/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question, insights_toggle: insights }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body?.detail?.message || `HTTP ${res.status}`);
    }
    const run = body.data || body;
    if (run.status === "failed") {
      throw new Error(run.error_message || "The agent run failed.");
    }
    const output = run.answer || run.output_text || "";
    const table = output.includes("|") ? parseMarkdownTable(output) : null;
    renderResult(output || "Answer produced.", table);
  } catch (err) {
    errBox.textContent = err.message || "Question failed.";
    errBox.hidden = false;
  } finally {
    btn.disabled = false;
    status.hidden = true;
  }
}

async function listRuns() {
  const list = $("run-list");
  const workspaceId = state.workspaceId || "";
  if (!workspaceId) {
    list.innerHTML = `<li>Create a workspace first.</li>`;
    return;
  }
  try {
    const res = await fetch(`/workspaces/${workspaceId}/runs`);
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      list.innerHTML = `<li>Failed to load runs.</li>`;
      return;
    }
    const runs = [];
    const data = body.data || body;
    if (Array.isArray(data.runs)) {
      (data.runs || []).forEach((run) => {
        runs.push(`<li>${escapeHtml(run.question || "")} — ${escapeHtml(run.status || "")}</li>`);
      });
    }
    list.innerHTML = runs.join("") || "<li>No runs yet.</li>";
  } catch {
    list.innerHTML = `<li>Failed to load runs.</li>`;
  }
}

function renderResult(answer, table) {
  $("answer-text").textContent = answer;
  $("result-card").hidden = false;

  if (table) {
    const thead = $("result-head");
    const tbody = $("result-body");
    thead.innerHTML = `<tr>${table.columns.map((c) => `<th>${escape(c)}</th>`).join("")}</tr>`;
    tbody.innerHTML = table.rows
      .map((row) => `<tr>${table.columns.map((c) => `<td>${escape(String(row[c] ?? ""))}</td>`).join("")}</tr>`)
      .join("");
  }
}

function parseMarkdownTable(text) {
  const lines = text.split("\n").filter((line) => line.trim().startsWith("|"));
  if (lines.length < 2) return null;
  const header = lines[0].split("|").filter((_, idx, arr) => idx !== 0 && idx !== arr.length - 1).map((s) => s.trim());
  const rows = lines.slice(2).map((line) => {
    const cols = line.split("|").filter((_, idx, arr) => idx !== 0 && idx !== arr.length - 1).map((s) => s.trim());
    return Object.fromEntries(header.map((h, i) => [h, cols[i] ?? ""]));
  });
  return { columns: header, rows };
}

function escape(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[ch] || ch));
}

$("upload-btn").addEventListener("click", uploadDataset);
$("ask-btn").addEventListener("click", askQuestion);
$("refresh-runs-btn")?.addEventListener("click", listRuns);
loadHealth();
listRuns();
