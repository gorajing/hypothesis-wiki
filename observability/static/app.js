const app = document.getElementById("app");

let state = null;
let activeRun = "run_002";
let activeClaimId = null;

init();

async function init() {
  try {
    const response = await fetch("/api/state", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`state endpoint returned ${response.status}`);
    state = await response.json();
    activeClaimId = state.provenance.trusted_claims[0]?.claim_id || null;
    render();
  } catch (error) {
    app.innerHTML = `
      <main class="boot error">
        <p class="eyebrow">Benchmark Claim Wiki</p>
        <h1>Could not load observability state</h1>
        <p>${escapeHtml(error.message)}</p>
      </main>`;
  }
}

function render() {
  app.innerHTML = `
    ${topBar()}
    <main class="shell">
      ${questionBand()}
      ${spine()}
      ${pipeline()}
      ${provenance()}
    </main>
  `;

  document.querySelectorAll("[data-run]").forEach((button) => {
    button.addEventListener("click", () => {
      activeRun = button.dataset.run;
      render();
    });
  });

  document.querySelectorAll("[data-claim]").forEach((button) => {
    button.addEventListener("click", () => {
      activeClaimId = button.dataset.claim;
      render();
    });
  });
}

function topBar() {
  const meta = state.meta;
  return `
    <header class="topbar">
      <div>
        <p class="eyebrow">${escapeHtml(meta.project)}</p>
        <h1>Observability</h1>
      </div>
      <div class="status-strip" aria-label="Backend status">
        ${statusPill("Redis", meta.session_backend)}
        ${statusPill("Cognee", meta.graph_backend)}
        ${statusPill("State", meta.state_source)}
      </div>
    </header>
  `;
}

function statusPill(label, value) {
  return `
    <span class="status-pill">
      <span class="status-dot"></span>
      <span>${escapeHtml(label)}</span>
      <code>${escapeHtml(value)}</code>
    </span>
  `;
}

function questionBand() {
  return `
    <section class="question-band">
      <div>
        <p class="eyebrow">Research question</p>
        <h2>${escapeHtml(state.research_question)}</h2>
      </div>
      <div class="meta-grid">
        <span><strong>API</strong><code>${escapeHtml(state.meta.api_endpoint)}</code></span>
        <span><strong>Redis</strong><code>${escapeHtml(state.meta.redis_url)}</code></span>
        <span><strong>Dataset</strong><code>${escapeHtml(state.meta.cognee_dataset)}</code></span>
      </div>
    </section>
  `;
}

function spine() {
  const run1 = state.runs.run_001;
  const run2 = state.runs.run_002;
  return `
    <section class="section">
      ${sectionHeader("01", "Run spine", "Run 1 failure, skill update, Run 2 evidence")}
      <div class="spine-grid">
        ${runPanel(run1, "before")}
        ${skillPanel()}
        ${runPanel(run2, "after")}
      </div>
      <div class="before-after">
        ${state.before_after.map((row) => `
          <div class="delta ${escapeHtml(row.tone)}">
            <span>${escapeHtml(row.label)}</span>
            <strong>${escapeHtml(row.display)}</strong>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function runPanel(run, flavor) {
  return `
    <article class="run-panel ${flavor}">
      <div class="run-heading">
        <p>${escapeHtml(run.label)}</p>
        <code>${escapeHtml(run.skill_name)}</code>
      </div>
      <div class="answer-card">
        <p class="label">Answer</p>
        <p>${escapeHtml(run.answer)}</p>
      </div>
      <div class="score-card">
        <p class="label">Critic scorecard</p>
        ${run.scorecard_rows.map((row) => `
          <div class="score-row ${escapeHtml(row.tone)}">
            <span>${escapeHtml(row.label)}</span>
            <strong>${escapeHtml(row.current)}</strong>
          </div>
        `).join("")}
      </div>
      <div class="graph-card">
        <p class="label">Trusted graph state</p>
        ${countGrid(run.trusted_graph.counts)}
        ${notes(run.notes)}
      </div>
    </article>
  `;
}

function skillPanel() {
  return `
    <article class="skill-panel">
      <div class="run-heading">
        <p>Self-improvement</p>
        <code>${escapeHtml(state.self_improvement.proposed_skill_path)}</code>
      </div>
      <div class="feedback-count">
        <span>critic + gate feedback</span>
        <strong>${escapeHtml(String(state.self_improvement.feedback_count))} signals</strong>
      </div>
      <div class="diff-card" aria-label="Skill diff">
        ${state.self_improvement.skill_diff.map((row) => `
          <div class="diff-line ${escapeHtml(row.kind)}">
            <span>${diffMarker(row.kind)}</span>
            <code>${escapeHtml(row.text) || "&nbsp;"}</code>
          </div>
        `).join("")}
      </div>
    </article>
  `;
}

function pipeline() {
  const run = state.runs[activeRun];
  return `
    <section class="section">
      ${sectionHeader("02", "Gate pipeline", "Redis quarantine -> distillation decision -> Cognee trusted graph")}
      <div class="tabs" role="tablist">
        ${Object.values(state.runs).map((runOption) => `
          <button class="${runOption.id === activeRun ? "active" : ""}" data-run="${escapeHtml(runOption.id)}">
            ${escapeHtml(runOption.label)}
          </button>
        `).join("")}
      </div>
      <div class="pipeline-grid">
        <div class="pipeline-column">
          <h3>Redis quarantine candidates</h3>
          ${run.pipeline.map((entry) => candidateCard(entry)).join("")}
        </div>
        <div class="pipeline-column">
          <h3>Distillation gate</h3>
          ${run.pipeline.map((entry) => decisionCard(entry)).join("")}
        </div>
        <div class="pipeline-column">
          <h3>Cognee trusted nodes</h3>
          ${run.trusted_graph.claims.length
            ? run.trusted_graph.claims.map((claim) => trustedNodeCard(claim)).join("")
            : `<div class="empty-state">No claims promoted in this run.</div>`}
        </div>
      </div>
    </section>
  `;
}

function candidateCard(entry) {
  return `
    <article class="mini-card">
      <div class="mini-card-head">
        <code>${escapeHtml(entry.candidate.id)}</code>
        <span>${escapeHtml(entry.candidate.kind)}</span>
      </div>
      <p>${escapeHtml(entry.candidate.text)}</p>
      ${chips(entry.candidate.scope_conditions)}
    </article>
  `;
}

function decisionCard(entry) {
  const decision = entry.decision;
  return `
    <article class="mini-card decision ${decision.promote ? "promote" : "reject"}">
      <div class="mini-card-head">
        <code>${escapeHtml(entry.candidate.id)}</code>
        <span>${escapeHtml(decision.status)}</span>
      </div>
      <p>${escapeHtml(decision.reason)}</p>
      <small>confidence ${escapeHtml(String(decision.confidence))}</small>
    </article>
  `;
}

function trustedNodeCard(claim) {
  return `
    <article class="mini-card trusted">
      <div class="mini-card-head">
        <code>${escapeHtml(claim.id)}</code>
        <span>${escapeHtml(claim.kind)}</span>
      </div>
      <p>${escapeHtml(claim.text)}</p>
      ${chips(claim.scope_conditions)}
    </article>
  `;
}

function provenance() {
  const claims = state.provenance.trusted_claims;
  const selected = claims.find((claim) => claim.claim_id === activeClaimId) || claims[0];
  return `
    <section class="section">
      ${sectionHeader("03", "Provenance drill-down", "Click a promoted claim to inspect the validated source span")}
      <div class="provenance-grid">
        <aside class="claim-list">
          ${claims.map((claim) => `
            <button class="${claim.claim_id === selected.claim_id ? "active" : ""}" data-claim="${escapeHtml(claim.claim_id)}">
              <code>${escapeHtml(claim.claim_id)}</code>
              <span>${escapeHtml(claim.audit_verdict)}</span>
            </button>
          `).join("")}
        </aside>
        <article class="source-card">
          <div class="source-head">
            <div>
              <p class="label">Promoted claim</p>
              <h3>${escapeHtml(selected.text)}</h3>
            </div>
            <a href="${escapeHtml(selected.source_url)}" target="_blank" rel="noreferrer">source</a>
          </div>
          ${chips(selected.scope_conditions)}
          <div class="source-text">
            <span>${escapeHtml(selected.source_preview.before)}</span><mark>${escapeHtml(selected.source_preview.highlight)}</mark><span>${escapeHtml(selected.source_preview.after)}</span>
          </div>
          <div class="provenance-meta">
            <span><strong>Evidence offsets</strong><code>${escapeHtml(String(selected.evidence_start))}-${escapeHtml(String(selected.evidence_end))}</code></span>
            <span><strong>Promotion</strong><code>${escapeHtml(selected.promotion_status)} / ${escapeHtml(String(selected.promotion_confidence))}</code></span>
            <span><strong>Span valid</strong><code>${escapeHtml(String(selected.evidence_span_valid))}</code></span>
          </div>
        </article>
      </div>
    </section>
  `;
}

function sectionHeader(index, title, subtitle) {
  return `
    <div class="section-header">
      <span>${escapeHtml(index)}</span>
      <div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(subtitle)}</p>
      </div>
    </div>
  `;
}

function countGrid(counts) {
  return `
    <div class="count-grid">
      ${Object.entries(counts).map(([key, value]) => `
        <span><strong>${escapeHtml(String(value))}</strong><em>${escapeHtml(key.replaceAll("_", " "))}</em></span>
      `).join("")}
    </div>
  `;
}

function notes(items) {
  if (!items.length) return `<p class="quiet">No critic notes.</p>`;
  return `
    <ul class="notes">
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function chips(values) {
  if (!values || !values.length) return `<div class="chips empty">scope erased</div>`;
  return `
    <div class="chips">
      ${values.map((value) => `<span>${escapeHtml(value)}</span>`).join("")}
    </div>
  `;
}

function diffMarker(kind) {
  if (kind === "added") return "+";
  if (kind === "removed") return "-";
  return " ";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

