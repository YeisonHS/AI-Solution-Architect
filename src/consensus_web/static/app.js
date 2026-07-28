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
    latency: document.querySelector("#latency"),
    servingMode: document.querySelector("#serving-mode"),
    interpretability: document.querySelector("#interpretability"),
    imbalance: document.querySelector("#imbalance"),
    cpu: document.querySelector("#cpu"),
    ram: document.querySelector("#ram"),
    vram: document.querySelector("#vram"),
    hasGpu: document.querySelector("#has-gpu"),
    unified: document.querySelector("#unified"),
    hwNote: document.querySelector("#hw-note"),
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
        serving_mode: fields.servingMode.value,
        interpretability_required: fields.interpretability.checked,
        class_imbalance: fields.imbalance.checked,
      },
    };
    const latency = intOrUndefined(fields.latency);
    if (latency !== undefined) payload.constraints.max_latency_ms = latency;
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

  function renderEvaluation(evaluation) {
    const container = document.querySelector("#evaluation");
    container.replaceChildren();
    if (!evaluation) return;

    addText(container, "p", "Cómo medir y validar la solución recomendada.", "helper-text");

    const metrics = document.createElement("section");
    metrics.className = "result-block";
    addText(metrics, "h4", "Métricas sugeridas");
    const chips = document.createElement("div");
    chips.className = "chips";
    evaluation.metrics.forEach((m) => chipEval(chips, m.name));
    metrics.appendChild(chips);
    if (mode === "expert") {
      const ul = document.createElement("ul");
      ul.className = "result-list";
      evaluation.metrics.forEach((m) => addText(ul, "li", `${m.name}: ${m.note}`));
      metrics.appendChild(ul);
    }
    container.appendChild(metrics);

    const val = document.createElement("section");
    val.className = "result-block";
    addText(val, "h4", "Validación");
    const vul = document.createElement("ul");
    vul.className = "result-list";
    evaluation.validation.forEach((v) => addText(vul, "li", v));
    val.appendChild(vul);
    addText(val, "p", `Baseline a superar: ${evaluation.baseline}`, "helper-text");
    container.appendChild(val);

    if (mode === "expert" && evaluation.pitfalls.length) {
      const pit = document.createElement("section");
      pit.className = "result-block";
      addText(pit, "h4", "Errores comunes a evitar");
      const pul = document.createElement("ul");
      pul.className = "result-list";
      evaluation.pitfalls.forEach((p) => addText(pul, "li", p));
      pit.appendChild(pul);
      container.appendChild(pit);
    }
  }

  function chipEval(parent, text) {
    const span = document.createElement("span");
    span.className = "chip pass";
    span.textContent = text;
    parent.appendChild(span);
  }

  function renderPlan(plan) {
    const container = document.querySelector("#plan");
    container.replaceChildren();
    if (!plan || !plan.length) return;
    addText(container, "p", "Pasos sugeridos para llevar la solución a producción.", "helper-text");
    const effortKind = { bajo: "pass", medio: "warn", alto: "fail" };
    plan.forEach((step) => {
      const card = document.createElement("article");
      card.className = "plan-step";
      const head = document.createElement("div");
      head.className = "plan-head";
      addText(head, "strong", step.title);
      const chip = document.createElement("span");
      chip.className = "chip " + (effortKind[step.effort] || "muted");
      chip.textContent = "esfuerzo " + step.effort;
      head.appendChild(chip);
      card.appendChild(head);
      addText(card, "p", step.detail, "helper-text");
      container.appendChild(card);
    });
  }

  function renderAll() {
    if (!lastData) return;
    renderProblem(lastData);
    renderTechniques(lastData.technique_options);
    renderMatrix(lastData.capability_matrix);
    renderDebate(lastData);
    renderDeploy(lastData.deployment_options);
    renderAdr(lastData);
    renderEvaluation(lastData.evaluation);
    renderPlan(lastData.implementation_plan);
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
    if (fields.latency) fields.latency.value = "";
    if (fields.servingMode) fields.servingMode.value = "realtime";
    if (fields.interpretability) fields.interpretability.checked = false;
    if (fields.imbalance) fields.imbalance.checked = false;
    setStatus("Ejemplo cargado. Pulsa «Convocar al Board».");
  }

  form.addEventListener("submit", submit);
  loadExampleButton.addEventListener("click", loadExample);
  modeBeginner.addEventListener("click", () => setMode("beginner"));
  modeExpert.addEventListener("click", () => setMode("expert"));

  // ---- Best-effort hardware auto-detection (browser-side) ----
  async function detectHardware() {
    try {
      let detected = [];
      if (navigator.hardwareConcurrency) {
        fields.cpu.value = String(navigator.hardwareConcurrency);
        detected.push("CPU");
      }
      if (navigator.deviceMemory) {
        fields.ram.value = String(navigator.deviceMemory);
        detected.push("RAM (aprox.)");
      }
      let platform = (navigator.platform || navigator.userAgent || "");
      let isMac = /mac/i.test(platform);
      let isArm = false;
      let archKnown = false;
      const uaData = navigator.userAgentData;
      if (uaData && uaData.getHighEntropyValues) {
        try {
          const hev = await uaData.getHighEntropyValues(["architecture", "platform"]);
          if (hev.platform) isMac = /mac/i.test(hev.platform);
          if (typeof hev.architecture === "string") {
            isArm = /arm/i.test(hev.architecture);
            archKnown = true;
          }
        } catch (_) {}
      }
      // Unified memory only applies to Apple Silicon (Mac + ARM).
      // On Linux/Windows this is always unchecked.
      fields.unified.checked = isMac && (archKnown ? isArm : true);

      const os = isMac ? "macOS" : (/win/i.test(platform) ? "Windows" : /linux/i.test(platform) ? "Linux" : "tu sistema");
      const note = detected.length
        ? "Detectado en " + os + ": " + detected.join(", ") + ". GPU/VRAM no se detectan desde el navegador: ingrésalas si aplica. Ajusta cualquier valor."
        : "Tu navegador no expone specs de hardware. Ingresa CPU, RAM y GPU manualmente.";
      if (fields.hwNote) fields.hwNote.textContent = note;
    } catch (_) {
      if (fields.hwNote) fields.hwNote.textContent = "";
    }
  }
  detectHardware();

  // ---- EDA sub-tool ----
  const eda = {
    csv: document.querySelector("#eda-csv"),
    header: document.querySelector("#eda-header"),
    file: document.querySelector("#eda-file"),
    run: document.querySelector("#eda-run"),
    status: document.querySelector("#eda-status"),
    result: document.querySelector("#eda-result"),
  };

  function edaStatus(message, type = "") {
    eda.status.textContent = message;
    eda.status.className = `form-status ${type}`;
  }

  if (eda.file) {
    eda.file.addEventListener("change", () => {
      const file = eda.file.files && eda.file.files[0];
      if (!file) return;
      if (file.size > 1000000) {
        edaStatus("El archivo supera 1 MB; usa una muestra más pequeña.", "error");
        return;
      }
      const reader = new FileReader();
      reader.onload = () => { eda.csv.value = String(reader.result || ""); };
      reader.readAsText(file);
    });
  }

  async function runEda() {
    const csv = eda.csv.value.trim();
    if (!csv) {
      edaStatus("Pega o sube un CSV para analizar.", "error");
      return;
    }
    eda.run.disabled = true;
    edaStatus("Analizando en memoria…");
    try {
      const response = await fetch("api/eda", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv, has_header: eda.header.checked }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "No se pudo analizar el CSV.");
      renderEda(data);
      edaStatus(data.privacy, "success");
    } catch (error) {
      edaStatus(error.message || "No se pudo analizar el CSV.", "error");
    } finally {
      eda.run.disabled = false;
    }
  }

  function renderEda(data) {
    eda.result.replaceChildren();
    eda.result.hidden = false;

    const summary = document.createElement("p");
    summary.className = "helper-text";
    summary.textContent = `${data.rows_analyzed} filas × ${data.columns_analyzed} columnas analizadas.`;
    eda.result.appendChild(summary);

    // Columns table
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    const table = document.createElement("table");
    const thead = document.createElement("tr");
    ["Columna", "Tipo", "Únicos", "Faltantes", "Sugerencia"].forEach((h) => addText(thead, "th", h));
    const head = document.createElement("thead");
    head.appendChild(thead);
    table.appendChild(head);
    const tbody = document.createElement("tbody");
    data.columns.forEach((c) => {
      const tr = document.createElement("tr");
      addText(tr, "td", c.name);
      addText(tr, "td", c.type);
      addText(tr, "td", String(c.n_unique));
      addText(tr, "td", String(c.n_missing));
      let hint = c.note || "";
      if (c.type === "enumerator") hint = `Encoding: ${c.encoding}`;
      else if (c.type === "datetime") hint = "Fecha → considera forecasting";
      else if (c.type === "numeric" && c.normalization) hint = `Escalar: ${c.normalization.recommended}`;
      if (c.high_missing) hint = (hint ? hint + " · " : "") + "muchos faltantes";
      else if (c.near_constant) hint = (hint ? hint + " · " : "") + "casi constante";
      addText(tr, "td", hint);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    eda.result.appendChild(wrap);

    // Enumerators with mapping
    if (data.enumerators.length) {
      const block = document.createElement("section");
      block.className = "result-block";
      addText(block, "h4", "Enumeradores normalizados (label encoding)");
      data.enumerators.forEach((e) => {
        const pairs = Object.entries(e.encoding_map).map(([k, v]) => `${k}→${v}`).join(", ");
        addText(block, "p", `${e.name} [${e.encoding}]: ${pairs}`, "helper-text");
      });
      eda.result.appendChild(block);
    }

    // High correlations
    const corr = document.createElement("section");
    corr.className = "result-block";
    addText(corr, "h4", "Correlaciones altas (|r| ≥ 0.7)");
    if (!data.high_correlations.length) {
      addText(corr, "p", "No se detectaron correlaciones altas.", "helper-text");
    } else {
      const ul = document.createElement("ul");
      ul.className = "result-list";
      data.high_correlations.forEach((p) => addText(ul, "li", `${p.a} ↔ ${p.b}: r = ${p.r}`));
      corr.appendChild(ul);
    }
    eda.result.appendChild(corr);

    // Correlation heatmap
    renderHeatmap(data.correlations);

    // Feature ranking vs target
    if (data.target_correlations && data.target_correlations.length) {
      const target = data.suggested_context && data.suggested_context.primary_target;
      const block = document.createElement("section");
      block.className = "result-block";
      addText(block, "h4", "Relación de cada variable con el objetivo" + (target ? " (" + target + ")" : ""));
      const list = document.createElement("ul");
      list.className = "result-list";
      data.target_correlations.forEach((item) => {
        const strength = Math.abs(item.r) >= 0.7 ? "fuerte" : Math.abs(item.r) >= 0.4 ? "moderada" : "débil";
        addText(list, "li", `${item.feature}: r = ${item.r} (relación ${strength})`);
      });
      block.appendChild(list);
      eda.result.appendChild(block);
    }

    // Target column suggestion
    const ctx = data.suggested_context || {};
    if (ctx.target_candidates && ctx.target_candidates.length) {
      const block = document.createElement("section");
      block.className = "result-block";
      addText(block, "h4", "Columna objetivo sugerida");
      const taskWord = { regression: "Regresión", classification: "Clasificación" };
      const select = document.createElement("select");
      select.id = "eda-target";
      ctx.target_candidates.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.column;
        opt.dataset.task = c.suggested_task;
        opt.textContent = `${c.column} → ${taskWord[c.suggested_task] || c.suggested_task}`;
        if (c.column === ctx.primary_target) opt.selected = true;
        select.appendChild(opt);
      });
      const label = document.createElement("label");
      label.textContent = "Objetivo (define el tipo de problema)";
      label.appendChild(select);
      block.appendChild(label);
      addText(block, "p", ctx.note || "", "helper-text");
      eda.result.appendChild(block);
    }

    // Recommendations
    if (data.recommendations.length) {
      const rec = document.createElement("section");
      rec.className = "result-block";
      addText(rec, "h4", "Recomendaciones de preparación");
      const ul = document.createElement("ul");
      ul.className = "result-list";
      data.recommendations.forEach((r) => addText(ul, "li", r));
      rec.appendChild(ul);
      eda.result.appendChild(rec);
    }

    // Prefill wizard
    const actions = document.createElement("div");
    actions.className = "artifacts-actions";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "button secondary";
    btn.textContent = "Usar en el wizard";
    btn.addEventListener("click", () => {
      if (data.suggested_context && data.suggested_context.dataset_rows) {
        fields.rows.value = String(data.suggested_context.dataset_rows);
      }
      fields.labeled.checked = true;
      const targetSelect = document.querySelector("#eda-target");
      let applied = "filas del dataset";
      if (targetSelect) {
        const opt = targetSelect.options[targetSelect.selectedIndex];
        const task = opt && opt.dataset.task;
        if (task) {
          fields.task.value = task;
          applied = `tipo de problema (${task}) y filas`;
        }
      }
      edaStatus(`Señales aplicadas al wizard: ${applied}.`, "success");
      fields.description.focus();
    });
    actions.appendChild(btn);
    addText(actions, "span", "Aplica el objetivo detectado (tipo de problema) y el nº de filas.", "helper-text");
    eda.result.appendChild(actions);
  }

  function corrColor(r) {
    if (r === null || r === undefined) return "#eef1f7";
    const intensity = Math.round(Math.min(Math.abs(r), 1) * 200);
    if (r >= 0) return `rgb(${255 - intensity},${255 - Math.round(intensity / 3)},255)`;
    return `rgb(255,${255 - intensity},${255 - intensity})`;
  }

  function renderHeatmap(correlations) {
    const names = correlations ? Object.keys(correlations) : [];
    if (names.length < 2) return;
    const block = document.createElement("section");
    block.className = "result-block";
    addText(block, "h4", "Matriz de correlación");
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    const table = document.createElement("table");
    table.className = "heatmap";
    const head = document.createElement("thead");
    const hr = document.createElement("tr");
    addText(hr, "th", "");
    names.forEach((n) => addText(hr, "th", n));
    head.appendChild(hr);
    table.appendChild(head);
    const body = document.createElement("tbody");
    names.forEach((rowName) => {
      const tr = document.createElement("tr");
      addText(tr, "th", rowName);
      names.forEach((colName) => {
        const r = correlations[rowName][colName];
        const td = addText(tr, "td", r === null || r === undefined ? "—" : r.toFixed(2));
        td.style.background = corrColor(r);
        td.style.textAlign = "center";
      });
      body.appendChild(tr);
    });
    table.appendChild(body);
    wrap.appendChild(table);
    block.appendChild(wrap);
    eda.result.appendChild(block);
  }

  eda.run.addEventListener("click", runEda);

  // Salary Dataset (Kaggle: abhishek14398/salary-dataset-simple-linear-regression)
  const SALARY_EXAMPLE = [
    ",YearsExperience,Salary",
    "0,1.1,39343.0", "1,1.3,46205.0", "2,1.5,37731.0", "3,2.0,43525.0",
    "4,2.2,39891.0", "5,2.9,56642.0", "6,3.0,60150.0", "7,3.2,54445.0",
    "8,3.2,64445.0", "9,3.7,57189.0", "10,3.9,63218.0", "11,4.0,55794.0",
    "12,4.0,56957.0", "13,4.1,57081.0", "14,4.5,61111.0", "15,4.9,67938.0",
    "16,5.1,66029.0", "17,5.3,83088.0", "18,5.9,81363.0", "19,6.0,93940.0",
    "20,6.8,91738.0", "21,7.1,98273.0", "22,7.9,101302.0", "23,8.2,113812.0",
    "24,8.7,109431.0", "25,9.0,105582.0", "26,9.5,116969.0", "27,9.6,112635.0",
    "28,10.3,122391.0", "29,10.5,121872.0",
  ].join("\n") + "\n";

  const edaExampleButton = document.querySelector("#eda-example");
  if (edaExampleButton) {
    edaExampleButton.addEventListener("click", () => {
      eda.csv.value = SALARY_EXAMPLE;
      eda.header.checked = true;
      edaStatus("Ejemplo del Salary Dataset cargado. Pulsa «Analizar datos».");
    });
  }

  // ---- What-if scenarios ----
  const whatifRun = document.querySelector("#whatif-run");
  const whatifOut = document.querySelector("#whatif");
  const strategyWord = strategyLabels;

  async function runWhatif() {
    let payload;
    try {
      payload = collectPayload();
    } catch (error) {
      setStatus(error.message, "error");
      return;
    }
    whatifRun.disabled = true;
    whatifOut.replaceChildren();
    const loading = document.createElement("p");
    loading.className = "helper-text";
    loading.textContent = "Comparando escenarios…";
    whatifOut.appendChild(loading);
    try {
      const response = await fetch("api/whatif", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "No se pudo comparar.");
      renderWhatif(data.scenarios);
    } catch (error) {
      whatifOut.replaceChildren();
      const err = document.createElement("p");
      err.className = "form-status error";
      err.textContent = error.message || "No se pudo comparar.";
      whatifOut.appendChild(err);
    } finally {
      whatifRun.disabled = false;
    }
  }

  function renderWhatif(scenarios) {
    whatifOut.replaceChildren();
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const hr = document.createElement("tr");
    ["Escenario", "Técnica", "Despliegue", "Costo/mes", "Confianza", "Estado"].forEach((h) => addText(hr, "th", h));
    head.appendChild(hr);
    table.appendChild(head);
    const body = document.createElement("tbody");
    scenarios.forEach((s) => {
      const tr = document.createElement("tr");
      addText(tr, "td", s.label);
      addText(tr, "td", strategyWord[s.strategy] || s.strategy);
      addText(tr, "td", s.deploy_target || "—");
      addText(tr, "td", s.estimated_monthly_usd != null ? `$${s.estimated_monthly_usd.toLocaleString()}` : "—");
      addText(tr, "td", `${s.confidence}%`);
      addText(tr, "td", s.forced ? "Forzado" : "OK");
      body.appendChild(tr);
    });
    table.appendChild(body);
    wrap.appendChild(table);
    whatifOut.appendChild(wrap);
  }

  whatifRun.addEventListener("click", runWhatif);

  // ---- Router hint (EDA vs recommendation) ----
  const routeHint = document.querySelector("#route-hint");
  let routeTimer = null;

  async function refreshRouteHint() {
    const description = fields.description.value.trim();
    if (!description) {
      routeHint.hidden = true;
      return;
    }
    const payload = {
      description,
      has_dataset: eda.csv.value.trim().length > 0,
    };
    if (fields.task.value) payload.task = fields.task.value;
    try {
      const response = await fetch("api/route", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        routeHint.hidden = true;
        return;
      }
      routeHint.hidden = false;
      routeHint.className = "route-hint " + (data.eda_suggested ? "eda" : "direct");
      routeHint.replaceChildren();
      const title = document.createElement("span");
      title.className = "route-title";
      title.textContent = data.eda_suggested
        ? "Sugerido: analiza tu dataset (EDA) primero"
        : "Sugerido: ve directo a la recomendación del Board";
      routeHint.appendChild(title);
      routeHint.appendChild(document.createTextNode(data.reason));
    } catch (_) {
      routeHint.hidden = true;
    }
  }

  function scheduleRouteHint() {
    if (routeTimer) clearTimeout(routeTimer);
    routeTimer = setTimeout(refreshRouteHint, 400);
  }

  fields.description.addEventListener("input", scheduleRouteHint);
  fields.task.addEventListener("change", refreshRouteHint);
  eda.csv.addEventListener("input", scheduleRouteHint);
})();
