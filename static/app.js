/* TraceTalk — frontend logic per spec §4 */

const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const panelNarration = document.getElementById("panel-narration");
const panelVisual = document.getElementById("panel-visual");

let activeXHR = null;

// ── Chat helpers ────────────────────────────────────────────────────
function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function addInvestigating() {
  const div = document.createElement("div");
  div.className = "msg investigating";
  div.textContent = "investigating...";
  div.id = "investigating";
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function removeInvestigating() {
  const el = document.getElementById("investigating");
  if (el) el.remove();
}

// ── Side panel renderers (spec §3) ──────────────────────────────────

function renderNarration(text) {
  panelNarration.textContent = text;
}

function renderMetricQuery(data) {
  const result = data.result;
  const points = result.points || [];
  const metric = result.metric || data.input?.metric || "";
  const service = result.service || data.input?.service || "all";

  panelVisual.innerHTML = "";
  const title = document.createElement("div");
  title.style.cssText = "margin-bottom:12px;color:var(--text-dim);font-size:12px;";
  title.textContent = `${service} · ${metric}`;
  panelVisual.appendChild(title);

  if (points.length === 0) {
    panelVisual.innerHTML += '<div class="placeholder">No data points</div>';
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.className = "chart-canvas";
  panelVisual.appendChild(canvas);

  requestAnimationFrame(() => drawChart(canvas, points, metric));
}

function drawChart(canvas, points, metric) {
  const rect = canvas.parentElement.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = 220 * dpr;
  canvas.style.width = rect.width + "px";
  canvas.style.height = "220px";

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  const W = rect.width;
  const H = 220;
  const pad = { top: 20, right: 20, bottom: 35, left: 55 };

  const values = points.map((p) => p.value);
  const minV = Math.min(...values) * 0.9;
  const maxV = Math.max(...values) * 1.1 || 1;

  const xStep = (W - pad.left - pad.right) / Math.max(points.length - 1, 1);

  // Background
  ctx.fillStyle = "#1a1d27";
  ctx.fillRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = "#2a2d3a";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i / 4) * (H - pad.top - pad.bottom);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(W - pad.right, y);
    ctx.stroke();

    const val = maxV - (i / 4) * (maxV - minV);
    ctx.fillStyle = "#8b8fa3";
    ctx.font = "11px monospace";
    ctx.textAlign = "right";
    ctx.fillText(Math.round(val), pad.left - 8, y + 4);
  }

  // X-axis labels
  ctx.fillStyle = "#8b8fa3";
  ctx.textAlign = "center";
  const labelEvery = Math.max(1, Math.floor(points.length / 6));
  for (let i = 0; i < points.length; i += labelEvery) {
    const x = pad.left + i * xStep;
    const ts = points[i].timestamp;
    const label = ts.substring(11, 16); // HH:MM
    ctx.fillText(label, x, H - 8);
  }

  // Line
  ctx.beginPath();
  ctx.strokeStyle = "#6366f1";
  ctx.lineWidth = 2;
  for (let i = 0; i < points.length; i++) {
    const x = pad.left + i * xStep;
    const y = pad.top + ((maxV - points[i].value) / (maxV - minV)) * (H - pad.top - pad.bottom);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Fill under line
  ctx.lineTo(pad.left + (points.length - 1) * xStep, H - pad.bottom);
  ctx.lineTo(pad.left, H - pad.bottom);
  ctx.closePath();
  ctx.fillStyle = "rgba(99, 102, 241, 0.1)";
  ctx.fill();
}

function renderLogQuery(data) {
  const result = data.result;
  const logs = result.logs || [];
  const textFilter = data.input?.text_filter || "";

  panelVisual.innerHTML = "";
  if (logs.length === 0) {
    panelVisual.innerHTML = '<div class="placeholder">No matching logs</div>';
    return;
  }

  const container = document.createElement("div");
  for (const log of logs) {
    const div = document.createElement("div");
    div.className = "log-line";

    let msg = log.message;
    if (textFilter) {
      const re = new RegExp(`(${textFilter.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
      msg = msg.replace(re, '<span class="highlight">$1</span>');
    }

    div.innerHTML =
      `<span class="ts">${log.timestamp.substring(11, 19)}</span> ` +
      `<span class="svc">${log.service}</span> ` +
      `<span class="lvl-${log.level}">${log.level.padEnd(5)}</span> ` +
      `${msg}`;
    container.appendChild(div);
  }
  panelVisual.appendChild(container);
}

function renderTraceQuery(data) {
  const result = data.result;
  const traces = result.traces || [];

  panelVisual.innerHTML = "";
  if (traces.length === 0) {
    panelVisual.innerHTML = '<div class="placeholder">No matching traces</div>';
    return;
  }

  // Show first trace as a waterfall
  const trace = traces[0];
  const title = document.createElement("div");
  title.style.cssText = "margin-bottom:8px;color:var(--text-dim);font-size:12px;";
  title.textContent = `Request: ${trace.request_id}`;
  panelVisual.appendChild(title);

  const maxDur = Math.max(...trace.spans.map((s) => s.duration_ms)) || 1;

  const waterfall = document.createElement("div");
  waterfall.className = "waterfall";
  for (const span of trace.spans) {
    const row = document.createElement("div");
    row.className = "wf-row";

    const svc = document.createElement("div");
    svc.className = "wf-svc";
    svc.textContent = span.service;

    const barContainer = document.createElement("div");
    barContainer.className = "wf-bar-container";

    const bar = document.createElement("div");
    bar.className = `wf-bar ${span.status}`;
    const leftPct = 0;
    const widthPct = (span.duration_ms / maxDur) * 100;
    bar.style.left = leftPct + "%";
    bar.style.width = Math.max(widthPct, 2) + "%";
    bar.textContent = `${span.duration_ms}ms`;

    barContainer.appendChild(bar);
    row.appendChild(svc);
    row.appendChild(barContainer);
    waterfall.appendChild(row);
  }
  panelVisual.appendChild(waterfall);

  if (traces.length > 1) {
    const more = document.createElement("div");
    more.style.cssText = "margin-top:12px;color:var(--text-dim);font-size:12px;";
    more.textContent = `+ ${traces.length - 1} more trace${traces.length > 2 ? "s" : ""}`;
    panelVisual.appendChild(more);
  }
}

function renderGraphView(data) {
  const highlighted = data.highlighted_services || [];

  panelVisual.innerHTML = "";
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "graph-svg");
  svg.setAttribute("viewBox", "0 0 380 260");

  // Arrow marker
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
  marker.setAttribute("id", "arrowhead");
  marker.setAttribute("markerWidth", "10");
  marker.setAttribute("markerHeight", "7");
  marker.setAttribute("refX", "10");
  marker.setAttribute("refY", "3.5");
  marker.setAttribute("orient", "auto");
  const polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
  polygon.setAttribute("points", "0 0, 10 3.5, 0 7");
  polygon.setAttribute("fill", "#2a2d3a");
  marker.appendChild(polygon);
  defs.appendChild(marker);
  svg.appendChild(defs);

  // Node positions (top to bottom chain)
  const nodes = {
    "api-gateway":      { x: 190, y: 40 },
    "cart-service":     { x: 190, y: 100 },
    "payment-service":  { x: 190, y: 160 },
    "inventory-service": { x: 190, y: 220 },
  };

  // Edges
  const edges = [
    ["api-gateway", "cart-service"],
    ["cart-service", "payment-service"],
    ["payment-service", "inventory-service"],
  ];

  for (const [from, to] of edges) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", nodes[from].x);
    line.setAttribute("y1", nodes[from].y + 16);
    line.setAttribute("x2", nodes[to].x);
    line.setAttribute("y2", nodes[to].y - 16);
    line.setAttribute("class", "graph-edge");
    svg.appendChild(line);
  }

  // Nodes
  for (const [name, pos] of Object.entries(nodes)) {
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", pos.x - 60);
    rect.setAttribute("y", pos.y - 14);
    rect.setAttribute("width", 120);
    rect.setAttribute("height", 28);
    rect.setAttribute("rx", 6);
    const isHighlighted = highlighted.includes(name);
    rect.setAttribute("class", isHighlighted ? "graph-node highlighted" : "graph-node");
    svg.appendChild(rect);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", pos.x);
    label.setAttribute("y", pos.y);
    label.setAttribute("class", "graph-label");
    label.textContent = name;
    svg.appendChild(label);
  }

  panelVisual.appendChild(svg);
}

// ── Event dispatch ──────────────────────────────────────────────────
function handleEvent(event) {
  switch (event.type) {
    case "narration":
      renderNarration(event.text);
      break;
    case "metric_query":
      renderMetricQuery(event);
      break;
    case "log_query":
      renderLogQuery(event);
      break;
    case "trace_query":
      renderTraceQuery(event);
      break;
    case "graph_view":
      renderGraphView(event);
      break;
    case "final_answer":
      removeInvestigating();
      const ansDiv = addMessage(event.text, "assistant");
      // Append evidence summary
      break;
  }
}

// ── Submit question ─────────────────────────────────────────────────
function submitQuestion() {
  const question = chatInput.value.trim();
  if (!question || activeXHR) return;

  addMessage(question, "user");
  chatInput.value = "";
  sendBtn.disabled = true;
  addInvestigating();
  panelNarration.textContent = "Starting investigation...";
  panelVisual.innerHTML = '<div class="placeholder">Waiting for first tool call...</div>';

  activeXHR = new XMLHttpRequest();
  activeXHR.open("POST", "/ask");
  activeXHR.setRequestHeader("Content-Type", "application/json");

  let buffer = "";
  activeXHR.onprogress = function () {
    const raw = activeXHR.responseText;
    // Process only new data
    const newData = raw.substring(buffer.length);
    buffer = raw;

    const lines = newData.split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.substring(6));
          handleEvent(event);
        } catch (e) { /* skip malformed */ }
      }
    }
  };

  activeXHR.onload = function () {
    activeXHR = null;
    sendBtn.disabled = false;
    chatInput.focus();
  };

  activeXHR.onerror = function () {
    removeInvestigating();
    addMessage("Error connecting to backend.", "assistant");
    activeXHR = null;
    sendBtn.disabled = false;
  };

  activeXHR.send(JSON.stringify({ question }));
}

// ── Event listeners ─────────────────────────────────────────────────
sendBtn.addEventListener("click", submitQuestion);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitQuestion();
  }
});
