const state = { status: null, examples: [
  "Traceback (most recent call last):\n  File \"train_proxy_sanity.py\", line 332, in __init__\nRuntimeError: No usable samples found under dataset for split test",
  "Traceback (most recent call last):\n_pickle.UnpicklingError: Weights only load failed. Unsupported global: GLOBAL pathlib.PosixPath",
  "epoch=100/100 validation_loss=0.0135\nartifact_manifest=outputs/demo_run/artifacts.json\nstatus: COMPLETED"
], exampleIndex: 0 };

const agentScenarios = {
  knowledge: {
    request: "What signed focus values are valid in the public demonstration?",
    context: {}
  },
  validate: {
    request: "Check this configuration before planning",
    context: {config: {task_id: "portfolio_review", grid_size: 128, max_solver_calls: 2, conditions: [
      {run_id: "dose44_focus_minus0p03", dose: 44, focus: -0.03},
      {run_id: "dose48_focus_plus0p03", dose: 48, focus: 0.03}
    ]}}
  },
  plan: {
    request: "Create a dry-run plan for human review",
    context: {config: {task_id: "portfolio_plan", grid_size: 128, max_solver_calls: 2, conditions: [
      {run_id: "dose44_focus_minus0p03", dose: 44, focus: -0.03},
      {run_id: "dose48_focus_plus0p03", dose: 48, focus: 0.03}
    ]}}
  },
  inspect: {request: "Inspect the run status", context: {run_id: "layout holdout"}},
  summarize: {request: "Summarize the result metrics", context: {run_id: "runtime profile"}}
};

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed: ${response.status}`);
  return payload;
}

function sourceMarkup(source) {
  return `<article class="source-item">
    <div class="source-topline"><span class="source-title">${escapeHtml(source.title)}</span><span class="source-type">${escapeHtml(source.source_type)}</span></div>
    <div class="source-path">${escapeHtml(source.path)} · ${escapeHtml(source.section || "Document")}</div>
    <p class="source-excerpt">${escapeHtml(source.excerpt)}</p>
    <div class="source-hash">SHA-256 ${escapeHtml(source.sha256)}</div>
  </article>`;
}

function renderDiagnosis(payload) {
  const findings = payload.findings.map((finding) => `<article class="finding">
    <div class="finding-label">
      <span class="badge ${finding.confidence.toLowerCase()}">${escapeHtml(finding.confidence)} confidence</span>
      <strong>${escapeHtml(finding.category.replaceAll("_", " "))}</strong>
    </div>
    <div class="finding-body">
      <p>${escapeHtml(finding.message)}</p>
      <div class="evidence-box">${escapeHtml(finding.evidence.text)}</div>
      <div class="action-line"><span>Human action</span><strong>${escapeHtml(finding.action)}</strong></div>
    </div>
  </article>`).join("");
  const sources = payload.sources.length
    ? payload.sources.map(sourceMarkup).join("")
    : `<div class="empty-state compact"><p>No indexed source matched this signature.</p></div>`;
  document.querySelector("#diagnosis-region").innerHTML = `
    <div class="diagnosis-header"><div><h2>Diagnosis complete</h2><p>${escapeHtml(payload.privacy)}</p></div><span class="badge">${payload.finding_count} finding${payload.finding_count === 1 ? "" : "s"}</span></div>
    <div class="assistant-summary"><span>${escapeHtml(payload.assistant_summary.mode.replaceAll("_", " "))}</span><p>${escapeHtml(payload.assistant_summary.text)}</p></div>
    ${findings}
    <div class="retrieval-block"><h2>Retrieved evidence</h2><div class="source-list">${sources}</div></div>`;
}

async function analyze() {
  const button = document.querySelector("#analyze-button");
  const text = document.querySelector("#log-input").value;
  button.disabled = true;
  button.textContent = "Analyzing...";
  try {
    renderDiagnosis(await request("/api/diagnose", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({text})
    }));
  } catch (error) {
    document.querySelector("#diagnosis-region").innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = "Analyze log";
  }
}

async function searchKnowledge(event) {
  event.preventDefault();
  const query = document.querySelector("#knowledge-query").value;
  const mode = document.querySelector("#retrieval-mode").value;
  const container = document.querySelector("#knowledge-results");
  container.innerHTML = `<div class="empty-state compact"><p>Searching indexed evidence...</p></div>`;
  try {
    const payload = await request("/api/search", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({query, mode, limit: 10})
    });
    container.innerHTML = payload.results.length
      ? payload.results.map(sourceMarkup).join("")
      : `<div class="empty-state compact"><h2>No matching evidence</h2><p>Try a simulator error signature or experiment identifier.</p></div>`;
  } catch (error) {
    container.innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
  }
}

async function askKnowledge() {
  const question = document.querySelector("#knowledge-query").value;
  const mode = document.querySelector("#retrieval-mode").value;
  const container = document.querySelector("#knowledge-results");
  container.innerHTML = `<div class="empty-state compact"><p>Checking the evidence boundary...</p></div>`;
  try {
    const payload = await request("/api/ask", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question, mode})
    });
    const citations = payload.citations.length
      ? payload.citations.map((item) => `<li><code>${escapeHtml(item.path)}</code> · ${escapeHtml(item.section)} · sha ${escapeHtml(item.sha256.slice(0, 12))}</li>`).join("")
      : "<li>No source cited.</li>";
    const evidence = payload.retrieval.length
      ? payload.retrieval.map(sourceMarkup).join("")
      : `<div class="empty-state compact"><p>No evidence retrieved.</p></div>`;
    container.innerHTML = `<article class="answer-card">
      <div class="answer-status">${escapeHtml(payload.status.replaceAll("_", " "))}</div>
      <p>${escapeHtml(payload.answer)}</p>
      <h2>Citations</h2><ul class="citation-list">${citations}</ul>
    </article><div class="source-list">${evidence}</div>`;
  } catch (error) {
    container.innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
  }
}

function setAgentScenario() {
  const scenario = agentScenarios[document.querySelector("#agent-scenario").value];
  document.querySelector("#agent-request").value = scenario.request;
}

function renderAgent(payload) {
  const trace = payload.trace.map((item) => `<div class="trace-row">
    <span>${escapeHtml(item.step)}</span><strong>${escapeHtml(item.tool)}</strong>
    <span>${escapeHtml(item.status)}</span><small>${escapeHtml(item.arguments_source.replaceAll("_", " "))}</small>
  </div>`).join("");
  const citations = payload.citations.length
    ? payload.citations.map((item) => `<li><code>${escapeHtml(item.path)}</code> · ${escapeHtml(item.section)} · sha ${escapeHtml(item.sha256.slice(0, 12))}</li>`).join("")
    : "<li>No citation required or available.</li>";
  document.querySelector("#agent-results").innerHTML = `<div class="agent-result-header">
    <div><span class="answer-status">${escapeHtml(payload.status)}</span><h2>${escapeHtml(payload.message)}</h2></div>
    <span class="badge">${escapeHtml(payload.planner_mode.replaceAll("_", " "))}</span>
  </div>
  <div class="agent-result-grid">
    <div><h2>Tool trace</h2><div class="trace-list">${trace}</div></div>
    <div><h2>Evidence</h2><ul class="citation-list">${citations}</ul></div>
  </div>
  <details class="payload-details"><summary>Structured tool result</summary><pre>${escapeHtml(JSON.stringify(payload.tool_result, null, 2))}</pre></details>`;
}

async function runAgent() {
  const button = document.querySelector("#agent-run-button");
  const scenario = agentScenarios[document.querySelector("#agent-scenario").value];
  const requestText = document.querySelector("#agent-request").value;
  button.disabled = true;
  button.textContent = "Reviewing...";
  try {
    renderAgent(await request("/api/agent", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({request: requestText, context: scenario.context})
    }));
  } catch (error) {
    document.querySelector("#agent-results").innerHTML = `<div class="error-message">${escapeHtml(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = "Run review";
  }
}

function formatMetric(metric) {
  let value = metric.value;
  if (typeof value === "number") value = Number.isInteger(value) ? value : Number(value.toPrecision(4));
  const name = metric.name.split(".").slice(-2).join(".");
  return `<span class="metric-chip">${escapeHtml(name)}: ${escapeHtml(value)}</span>`;
}

function metricEntries(metrics) {
  return Object.entries(metrics || {}).map(([name, value]) => ({name, value}));
}

async function loadExperiments(query = "") {
  const payload = await request(`/api/experiments?q=${encodeURIComponent(query)}&limit=60`);
  document.querySelector("#experiment-rows").innerHTML = payload.results.map((card) => `<tr>
    <td><strong>${escapeHtml(card.title)}</strong><div class="source-cell">${escapeHtml(card.experiment_id)}</div></td>
    <td>${escapeHtml(card.category)}</td>
    <td><span class="status-text">${escapeHtml(card.status)}</span></td>
    <td><div class="metric-list">${metricEntries(card.metrics).slice(0, 5).map(formatMetric).join("") || "--"}</div></td>
    <td class="source-cell">${escapeHtml(card.source)}<br>sha ${escapeHtml(card.source_sha256.slice(0, 12))}</td>
  </tr>`).join("");
}

async function loadPlan() {
  const plan = await request("/api/plan");
  const budget = plan.budget || {};
  const gate = plan.launch_gate || {};
  document.querySelector("#plan-summary").innerHTML = [
    ["Task", plan.task_id || "--"], ["Validation", plan.validation || "--"],
    ["Planned calls", budget.planned_solver_calls ?? "--"], ["Launch gate", gate.state || "--"]
  ].map(([label, value]) => `<div class="plan-stat"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("");
  document.querySelector("#plan-rows").innerHTML = plan.conditions.map((item) => `<tr>
    <td><strong>${escapeHtml(item.run_id)}</strong></td><td>${escapeHtml(item.dose)} arb.</td>
    <td>${escapeHtml(item.focus)} arb.</td><td>${escapeHtml(item.solver_calls_if_live)}</td>
    <td><span class="status-text">${item.dry_run_enforced ? "DRY RUN" : "REVIEW"}</span></td>
  </tr>`).join("");
}

async function initialize() {
  try {
    state.status = await request("/api/status");
    document.querySelector("#knowledge-count").textContent = state.status.knowledge_chunks;
    document.querySelector("#experiment-count").textContent = state.status.experiment_cards;
    document.querySelector("#data-policy").textContent = state.status.data_policy === "SYNTHETIC_ONLY" ? "Synthetic" : "Review";
    document.querySelector("#mode-label").textContent = state.status.mode.replaceAll("_", " ").toLowerCase();
    await Promise.all([loadExperiments(), loadPlan()]);
    const params = new URLSearchParams(window.location.search);
    if (params.get("rag") === "1") {
      document.querySelector('[data-view="knowledge"]').click();
      document.querySelector("#knowledge-query").value = "What signed focus values are valid in the public demonstration?";
      await askKnowledge();
    } else if (params.get("agent") === "1") {
      document.querySelector('[data-view="agent"]').click();
      setAgentScenario();
      await runAgent();
    } else if (params.get("demo") === "1") {
      document.querySelector("#log-input").value = state.examples[0];
      await analyze();
    }
  } catch (error) {
    document.querySelector("#input-note").textContent = `Service unavailable: ${error.message}`;
  }
}

document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item === button));
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${button.dataset.view}`));
}));
document.querySelector("#analyze-button").addEventListener("click", analyze);
document.querySelector("#sample-button").addEventListener("click", () => {
  document.querySelector("#log-input").value = state.examples[state.exampleIndex % state.examples.length];
  state.exampleIndex += 1;
});
document.querySelector("#log-file").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  document.querySelector("#log-input").value = await file.text();
  document.querySelector("#input-note").textContent = `${file.name} loaded locally; content has not been persisted.`;
});
document.querySelector("#knowledge-form").addEventListener("submit", searchKnowledge);
document.querySelector("#ask-button").addEventListener("click", askKnowledge);
document.querySelector("#agent-scenario").addEventListener("change", setAgentScenario);
document.querySelector("#agent-run-button").addEventListener("click", runAgent);
let filterTimer;
document.querySelector("#experiment-query").addEventListener("input", (event) => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => loadExperiments(event.target.value), 180);
});

initialize();
setAgentScenario();
