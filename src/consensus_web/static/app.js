(() => {
  "use strict";

  const form = document.querySelector("#architect-form");
  const submitButton = document.querySelector("#submit-button");
  const loadExampleButton = document.querySelector("#load-example");
  const statusElement = document.querySelector("#form-status");
  const resultElement = document.querySelector("#result");
  const matrixElement = document.querySelector("#matrix");
  const debateElement = document.querySelector("#debate");
  const adrElement = document.querySelector("#adr");
  const modeBeginner = document.querySelector("#mode-beginner");
  const modeExpert = document.querySelector("#mode-expert");

  const fields = {
    description: document.querySelector("#description"),
    task: document.querySelector("#task"),
    rows: document.querySelector("#rows"),
    budget: document.querySelector("#budget"),
    docs: document.querySelector("#docs"),
    privacy: document.querySelector("#privacy"),
    labeled: document.querySelector("#labeled"),
    dataChanges: document.querySelector("#data-changes"),
    cpu: document.querySelector("#cpu"),
    ram: document.querySelector("#ram"),
    vram: document.querySelector("#vram"),
    hasGpu: document.querySelector("#has-gpu"),
    unified: document.querySelector("#unified"),
  };

  const techniqueLabels = { rag: "RAG", agents: "Agents", lora: "LoRA", fine_tuning: "Fine-Tuning" };
  const agentLabels = {
    security: "Security",
    cost: "Cost",
    best_practices: "Best Practices",
    product: "Product",
    devils_advocate: "Devil's Advocate",
  };
  const strategyLabels = { rag: "RAG", agents: "Agentes", lora: "LoRA", fine_tuning: "Fine-Tuning" };

  let mode = "beginner";
  let lastData = null;
  let lastPayload = null;

  async function downloadArtifacts() {
    if (!lastPayload) return;
    setStatus("Generando artefactos…");
    try {
      const response = await fetch("api/artifacts.zip", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastPayload),
      });
      if (!response.ok) {
        let message = "No se pudieron generar los artefactos.";
        try {
          message = (await response.json()).error || message;
        } catch (_) {}
        throw new Error(message);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ai-architecture-artifacts.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus("Artefactos descargados.", "success");
    } catch (error) {
      setStatus(error.message || "No se pudieron generar los artefactos.", "error");
    }
  }

  function setStatus(message, type = "") {
    statusElement.textContent = message;
    statusElement.className = `form-status ${type}`;
  }

  function intOrUndefined(input) {
    const raw = input.value.trim();
    if (raw === "") return undefined;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) {
      throw new Error("Revisa los valores numéricos: deben ser positivos.");
    }
    return value;
  }

  function collectPayload() {
    const description = fields.description.value.trim();
    if (!description) {
      throw new Error("Describe la solución de IA que quieres construir.");
    }
    const cpu = Number(fields.cpu.value);
    const ram = Number(fields.ram.value);
    if (!Number.isFinite(cpu) || cpu < 1 || !Number.isFinite(ram) || ram < 1) {
      throw new Error("CPU y RAM deben ser mayores que cero.");
    }
    const payload = {
      description,
      hardware: {
        cpu_cores: cpu,
        ram_gb: ram,
        has_gpu: fields.hasGpu.checked,
        vram_gb: intOrUndefined(fields.vram) ?? 0,
        unified_memory: fields.unified.checked,
      },
      constraints: {
        privacy: fields.privacy.value,
        data_changes_frequently: fields.dataChanges.checked,
      },
    };
    if (fields.task.value) payload.task = fields.task.value;
    payload.dataset_labeled = fields.labeled.checked;
    const rows = intOrUndefined(fields.rows);
    if (rows !== undefined) payload.dataset_rows = rows;
    const budget = intOrUndefined(fields.budget);
    if (budget !== undefined) payload.constraints.monthly_budget_usd = budget;
    const docs = intOrUndefined(fields.docs);
    if (docs !== undefined) payload.knowledge_base_docs = docs;
    return payload;
  }

  function addText(parent, tag, text, className = "") {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    parent.appendChild(el);
    return el;
  }

  function renderMatrix(rows) {
    matrixElement.replaceChildren();
    rows.forEach((row) => {
      const item = document.createElement("div");
      item.className = `matrix-row${row.recommended ? " ok" : " no"}`;
      addText(item, "span", techniqueLabels[row.technique] || row.technique, "matrix-name");
      const barWrap = document.createElement("div");
      barWrap.className = "bar-wrap";
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.style.width = `${row.score}%`;
      barWrap.appendChild(bar);
      item.appendChild(barWrap);
      addText(item, "span", `${row.score}%`, "matrix-score");
      if (mode === "expert") {
        addText(item, "p", row.reason, "matrix-reason");
      }
      matrixElement.appendChild(item);
    });
  }

  function verdictClass(verdict) {
    return verdict === "FAIL" ? "fail" : verdict === "WARN" ? "warn" : "pass";
  }

  function renderDebate(data) {
    debateElement.replaceChildren();
    // Rejected candidates (earlier rounds) first, then the converged one.
    data.rejected_alternatives.forEach((alt, index) => {
      const card = document.createElement("article");
      card.className = "debate-card rejected";
      addText(card, "h3", `Ronda ${index + 1}: Architect propone ${strategyLabels[alt.strategy] || alt.strategy}`);
      const tags = document.createElement("div");
      tags.className = "verdict-tags";
      alt.board_summary.split(" · ").forEach((part) => {
        const [agent, verdict] = part.split(" ");
        const chip = document.createElement("span");
        chip.className = `chip ${verdictClass(verdict)}`;
        chip.textContent = `${agentLabels[agent] || agent}: ${verdict}`;
        tags.appendChild(chip);
      });
      card.appendChild(tags);
      addText(card, "p", "El Board la rechaza y pide una re-propuesta.", "debate-note");
      if (mode === "expert") {
        const ul = document.createElement("ul");
        alt.reasons.forEach((r) => addText(ul, "li", r));
        card.appendChild(ul);
      }
      debateElement.appendChild(card);
    });

    const win = document.createElement("article");
    win.className = "debate-card converged";
    addText(win, "h3", `Ronda ${data.rounds}: Consenso en ${strategyLabels[data.recommendation.strategy] || data.recommendation.strategy}`);
    addText(win, "p", data.forced ? "Entrega forzada: la mejor arquitectura disponible con riesgos abiertos." : "El Board converge sin bloqueos.", "debate-note");
    debateElement.appendChild(win);
  }

  function renderAdr(data) {
    adrElement.replaceChildren();
    const rec = data.recommendation;

    const head = document.createElement("div");
    head.className = "adr-head";
    const left = document.createElement("div");
    addText(left, "p", "RECOMENDACIÓN", "eyebrow");
    addText(left, "h3", strategyLabels[rec.strategy] || rec.strategy);
    head.appendChild(left);
    const score = document.createElement("div");
    score.className = "adr-score";
    addText(score, "strong", `${data.confidence}%`);
    addText(score, "span", "confidence calculado");
    head.appendChild(score);
    adrElement.appendChild(head);

    if (rec.estimated_monthly_usd != null) {
      addText(adrElement, "p", `Costo estimado: $${rec.estimated_monthly_usd.toLocaleString()}/mes`, "adr-cost");
    }

    if (mode === "beginner") {
      addText(adrElement, "p", rec.rationale.split(".")[0] + ".", "adr-plain");
    } else {
      const spec = document.createElement("dl");
      spec.className = "adr-spec";
      [["Modelo", rec.model], ["Infra", rec.infrastructure], ["Base de datos", rec.database], ["Framework", rec.framework]].forEach(([k, v]) => {
        addText(spec, "dt", k);
        addText(spec, "dd", v);
      });
      adrElement.appendChild(spec);
      addText(adrElement, "p", rec.rationale, "helper-text");
    }

    addRiskBlock("Riesgos aceptados", data.accepted_risks);
    if (data.unresolved_risks.length) addRiskBlock("Riesgos no resueltos", data.unresolved_risks);

    const artifacts = document.createElement("div");
    artifacts.className = "artifacts-actions";
    const dl = document.createElement("button");
    dl.type = "button";
    dl.className = "button primary";
    dl.textContent = "Descargar artefactos (ZIP)";
    dl.addEventListener("click", downloadArtifacts);
    artifacts.appendChild(dl);
    addText(artifacts, "span", "Terraform, Dockerfile, CI, ADR y stubs listos para revisar.", "helper-text");
    adrElement.appendChild(artifacts);

    const rej = document.createElement("section");
    rej.className = "rejected-block";
    addText(rej, "h4", "Rejected Alternatives");
    if (!data.rejected_alternatives.length) {
      addText(rej, "p", "Ninguna: la primera propuesta convergió.", "helper-text");
    } else {
      data.rejected_alternatives.forEach((alt) => {
        const card = document.createElement("div");
        card.className = "rejected-item";
        addText(card, "strong", strategyLabels[alt.strategy] || alt.strategy);
        addText(card, "span", alt.board_summary, "rejected-summary");
        const ul = document.createElement("ul");
        alt.reasons.forEach((r) => addText(ul, "li", r));
        card.appendChild(ul);
        rej.appendChild(card);
      });
    }
    adrElement.appendChild(rej);

    if (mode === "expert") {
      const details = document.createElement("details");
      details.className = "technical-result";
      addText(details, "summary", "Ver JSON del ADR");
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(data, null, 2);
      details.appendChild(pre);
      adrElement.appendChild(details);
    }
  }

  function addRiskBlock(title, risks) {
    if (!risks.length) return;
    const block = document.createElement("section");
    block.className = "risk-block";
    addText(block, "h4", title);
    const ul = document.createElement("ul");
    risks.forEach((r) => addText(ul, "li", r));
    block.appendChild(ul);
    adrElement.appendChild(block);
  }

  function renderProblem(data) {
    const el = document.querySelector("#problem-family");
    el.textContent = data.problem ? data.problem.label : "";
  }

  function renderTechniques(options) {
    const container = document.querySelector("#techniques");
    container.replaceChildren();
    (options || []).forEach((t) => {
      const card = document.createElement("article");
      card.className = `tech-card${t.recommended ? " recommended" : ""}`;
      const head = document.createElement("div");
      head.className = "tech-head";
      addText(head, "strong", t.name);
      if (t.recommended) chipEl(head, "Recomendada", "reco");
      chipEl(head, t.needs_gpu ? "GPU" : "CPU", t.needs_gpu ? "warn" : "pass");
      chipEl(head, `complejidad ${t.complexity}`, "muted");
      card.appendChild(head);
      addText(card, "p", t.summary, "tech-summary");
      if (mode === "expert") {
        addText(card, "p", `Cuándo: ${t.when_to_use}`, "helper-text");
        addText(card, "p", `Frameworks: ${t.frameworks.join(", ")}`, "helper-text");
      }
      container.appendChild(card);
    });
  }

  function renderDeploy(options) {
    const container = document.querySelector("#deploy");
    container.replaceChildren();
    (options || []).forEach((o) => {
      const row = document.createElement("article");
      row.className = `deploy-card${o.within_budget ? "" : " over"}`;
      const head = document.createElement("div");
      head.className = "deploy-head";
      addText(head, "strong", o.name);
      addText(head, "span", `$${o.estimated_monthly_usd.toLocaleString()}/mes`, "deploy-cost");
      if (!o.within_budget) chipEl(head, "excede presupuesto", "fail");
      row.appendChild(head);
      addText(row, "p", o.best_for, "helper-text");
      if (mode === "expert") addText(row, "p", o.summary, "helper-text");
      container.appendChild(row);
    });
  }

  function chipEl(parent, text, kind) {
    const span = document.createElement("span");
    span.className = `chip ${kind}`;
    span.textContent = text;
    parent.appendChild(span);
    return span;
  }

  function renderAll() {
    if (!lastData) return;
    renderProblem(lastData);
    renderTechniques(lastData.technique_options);
    renderMatrix(lastData.capability_matrix);
    renderDebate(lastData);
    renderDeploy(lastData.deployment_options);
    renderAdr(lastData);
  }

  function setMode(next) {
    mode = next;
    const isBeginner = next === "beginner";
    modeBeginner.classList.toggle("active", isBeginner);
    modeExpert.classList.toggle("active", !isBeginner);
    modeBeginner.setAttribute("aria-pressed", String(isBeginner));
    modeExpert.setAttribute("aria-pressed", String(!isBeginner));
    renderAll();
  }

  async function submit(event) {
    event.preventDefault();
    let payload;
    try {
      payload = collectPayload();
    } catch (error) {
      setStatus(error.message, "error");
      return;
    }
    submitButton.disabled = true;
    setStatus("El Architecture Review Board está debatiendo…");
    lastPayload = payload;
    try {
      const response = await fetch("api/architect", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      let data;
      try {
        data = await response.json();
      } catch (_) {
        throw new Error("El servidor devolvió una respuesta no válida.");
      }
      if (!response.ok) {
        throw new Error(data.error || "No se pudo ejecutar el Board.");
      }
      lastData = data;
      resultElement.hidden = false;
      renderAll();
      setStatus("Decisión lista.", "success");
      resultElement.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setStatus(error.message || "No se pudo conectar con el servidor.", "error");
    } finally {
      submitButton.disabled = false;
    }
  }

  function loadExample() {
    fields.description.value = "Quiero predecir el precio de venta de casas a partir de un set de datos etiquetado.";
    fields.task.value = "regression";
    fields.rows.value = "8000";
    fields.budget.value = "100";
    fields.docs.value = "";
    fields.privacy.value = "private_cloud";
    fields.labeled.checked = true;
    fields.dataChanges.checked = false;
    fields.cpu.value = "10";
    fields.ram.value = "16";
    fields.vram.value = "0";
    fields.hasGpu.checked = false;
    fields.unified.checked = true;
    setStatus("Ejemplo cargado. Pulsa «Convocar al Board».");
  }

  form.addEventListener("submit", submit);
  loadExampleButton.addEventListener("click", loadExample);
  modeBeginner.addEventListener("click", () => setMode("beginner"));
  modeExpert.addEventListener("click", () => setMode("expert"));
})();
