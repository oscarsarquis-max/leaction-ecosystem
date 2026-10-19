(function () {
  const KEY = "isa-demo-v1";
  const PEOPLE = {
    marina: { id: "pessoa-marina", name: "Marina Alves" },
    paulo: { id: "pessoa-paulo", name: "Paulo Nunes" },
    eveline: { id: "pessoa-eveline-demo", name: "Eveline (demonstração)" },
  };
  const EXPENSE_CATS = ["Alimentação", "Moradia", "Transporte", "Saúde", "Educação", "Lazer", "Compras", "Outros"];
  const INCOME_CATS = ["Salário", "Serviços", "Outros"];

  const state = load();

  function load() {
    const blank = {
      personId: "",
      month: new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit" }).format(new Date()),
      font: "normal",
      entries: [],
      draft: null,
      notice: "",
      recovery: "",
      filters: { q: "", direction: "", category: "", status: "", archived: false, mode: "", consumption: false },
      cameraError: "",
      accounts: [],
      batches: [],
      statementNotes: [],
      importPreview: null,
      importNotice: "",
      importAccountId: "",
      importNewName: "",
      importOrigin: "",
      importFileName: "",
      occurrences: [],
    };
    window.isaPublic = true;
    return blank;
  }

  function applyLabStorage() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(KEY) || "null");
      if (!saved) return;
      saved.entries = (saved.entries || []).map(function (entry) {
        delete entry.imageDataUrl;
        return entry;
      });
      if (saved.draft) delete saved.draft.imageDataUrl;
      Object.assign(state, saved);
    } catch (err) {
      return;
    }
  }

  function persist() {
    const copy = JSON.parse(JSON.stringify(state));
    (copy.entries || []).forEach(function (entry) { delete entry.imageDataUrl; });
    if (copy.draft) delete copy.draft.imageDataUrl;
    delete copy.stream;
    if (copy.importOrigin === "arquivo-teste") copy.importPreview = null;
    if (window.isaPublic) {
      copy.personId = "";
      copy.entries = [];
      copy.accounts = [];
      copy.batches = [];
      copy.statementNotes = [];
      copy.occurrences = [];
    }
    sessionStorage.setItem(KEY, JSON.stringify(copy));
  }

  function api(method, path, body) {
    var headers = { "Content-Type": "application/json" };
    if (!window.isaPublic && window.isaLabPerson) headers["X-ISA-Lab-Person"] = window.isaLabPerson;
    if (window.isaAccountContext) headers["X-ISA-Account"] = window.isaAccountContext;
    return fetch(path, {
      method: method,
      credentials: "include",
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try { data = JSON.parse(text); } catch (err) { data = {}; }
        }
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  function clearMoney() {
    state.personId = "";
    state.entries = [];
    state.accounts = [];
    state.batches = [];
    state.statementNotes = [];
    state.occurrences = [];
    state.draft = null;
    state.importPreview = null;
    state.profile = { displayName: "", accessLabel: "", ready: false };
    state.savedAccountId = "";
  }

  function applyWorkspace(data) {
    if (!data || !data.ownerId) return;
    state.personId = data.ownerId;
    state.accounts = data.accounts || [];
    state.entries = data.entries || [];
    state.occurrences = data.occurrences || [];
    state.statementNotes = data.notes || [];
    state.batches = data.batches || [];
    if (data.profile) state.profile = Object.assign({ ready: true }, data.profile);
    if (data.banks) state.banks = data.banks;
  }

  function mine() {
    return state.entries.filter(function (entry) {
      if (entry.ownerId !== state.personId) return false;
      if (!window.isaAccountContext || window.isaAccountContext === "all") return true;
      return (entry.accountId || "") === window.isaAccountContext;
    });
  }

  function go(hash) {
    if (location.hash !== hash) location.hash = hash;
    else render();
  }

  window.addEventListener("hashchange", render);

  function moneyText(minor, currency) {
    const code = currency || "BRL";
    const value = Number(minor);
    if (!Number.isFinite(value)) return "Não informado";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: code }).format(value / 100);
  }

  function brl(minor) {
    const n = Number(minor) || 0;
    const abs = Math.abs(n);
    const reais = Math.floor(abs / 100).toLocaleString("pt-BR");
    const cents = String(abs % 100).padStart(2, "0");
    return (n < 0 ? "-" : "") + "R$ " + reais + "," + cents;
  }

  function parseMoney(raw) {
    const text = String(raw || "").trim();
    if (!text) return { missing: true };
    if (/usd|eur|gbp|us\$|€|£/i.test(text)) return { review: true, raw: text };
    if (/^\d+\.\d{2}$/.test(text)) return { review: true, raw: text };
    const cleaned = text.replace(/[R$\s]/gi, "");
    if (!/^(\d{1,3}(\.\d{3})+|\d+),\d{2}$/.test(cleaned) && !/^\d+$/.test(cleaned)) {
      return { review: true, raw: text };
    }
    const normalized = cleaned.includes(",") ? cleaned.replace(/\./g, "").replace(",", ".") : cleaned;
    const value = Number(normalized);
    if (!Number.isFinite(value) || value < 0) return { review: true, raw: text };
    return { amountMinor: Math.round(value * 100) };
  }

  function cats(direction) {
    return direction === "ganho" ? INCOME_CATS : EXPENSE_CATS;
  }

  function statusLabel(status) {
    return { pago: "Pago", a_pagar: "A pagar", recebido: "Recebido", a_receber: "A receber" }[status] || status;
  }

  function natureLabel(nature) {
    return {
      consumo: "Consumo",
      transferencia: "Transferência entre contas",
      reembolso: "Reembolso",
      emprestimo: "Empréstimo",
      aplicacao: "Aplicação",
      bb_rende_facil: "Movimentação BB Rende Fácil",
      a_conferir: "Ainda sem natureza",
    }[nature] || "Consumo";
  }

  function blankDraft(direction, source) {
    return {
      id: "",
      direction: direction || "gasto",
      nature: "consumo",
      merchant: "",
      noteDate: "",
      dueDate: "",
      statusDate: "",
      amountText: "",
      currency: ((state.accounts || []).find(function (item) { return item.id === window.isaAccountContext; }) || {}).currency || "BRL",
      accountId: window.isaAccountContext && window.isaAccountContext !== "all" ? window.isaAccountContext : "",
      category: "",
      status: direction === "ganho" ? "a_receber" : "a_pagar",
      source: source || "digitado",
      read: source === "digitado" ? "manual" : "",
      documentId: "",
      fingerprint: "",
      imageDataUrl: "",
      imageLabel: "",
      simulated: false,
      allowDuplicate: false,
      saving: false,
    };
  }

  function scenes() {
    return {
      boa: {
        read: "boa",
        merchant: "Padaria do Largo",
        noteDate: "2026-10-12",
        amountText: "42,80",
        category: "Alimentação",
        documentId: "ISA-NOTA-100",
        fingerprint: "sintetico-padaria-100",
        imageLabel: "Exemplo sintético · Padaria do Largo",
        simulated: true,
      },
      parcial: {
        read: "parcial",
        merchant: "",
        noteDate: "2026-10-09",
        amountText: "18,50",
        category: "",
        documentId: "",
        fingerprint: "sintetico-parcial-09",
        imageLabel: "Exemplo sintético · leitura parcial",
        simulated: true,
      },
      ilegivel: { read: "ilegivel", simulated: true, imageLabel: "Exemplo sintético · imagem ilegível", fingerprint: "sintetico-ilegivel" },
      falha: { read: "falha", simulated: true, imageLabel: "Exemplo sintético · falha de serviço" },
      duplicata: {
        read: "boa",
        merchant: "Padaria do Largo",
        noteDate: "2026-10-12",
        amountText: "42,80",
        category: "Alimentação",
        documentId: "ISA-NOTA-100",
        fingerprint: "sintetico-padaria-100",
        imageLabel: "Segunda foto do mesmo exemplo sintético",
        simulated: true,
      },
    };
  }

  function applyScene(name) {
    const base = state.draft || blankDraft(state.draft && state.draft.direction, "simulado");
    state.draft = Object.assign(blankDraft(base.direction, "simulado"), scenes()[name], {
      direction: base.direction,
      status: base.direction === "ganho" ? "a_receber" : "a_pagar",
      imageDataUrl: base.imageDataUrl || "",
    });
    state.notice = "";
    persist();
    go("#conferir");
  }

  function simulate(name) {
    const direction = state.draft ? state.draft.direction : "gasto";
    state.draft = blankDraft(direction, "simulado");
    state.draft.read = "processando";
    state.draft.simulated = true;
    state.notice = "";
    persist();
    go("#conferir");
    window.setTimeout(function () {
      applyScene(name);
    }, 700);
  }

  function stopCamera() {
    if (state.stream) {
      state.stream.getTracks().forEach(function (track) { track.stop(); });
      state.stream = null;
    }
  }

  async function openCamera() {
    state.cameraError = "";
    stopCamera();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      state.cameraError = "Este navegador não ofereceu câmera. Use a galeria ou digite o lançamento.";
      render();
      return;
    }
    try {
      state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
      render();
      const video = document.getElementById("cam");
      if (video) video.srcObject = state.stream;
    } catch (err) {
      state.cameraError = "A câmera não foi autorizada. Escolha uma imagem ou digite o lançamento. Esta demonstração não insiste na permissão.";
      render();
    }
  }

  function captureFrame() {
    const video = document.getElementById("cam");
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const draft = state.draft || blankDraft("gasto", "camera");
    draft.source = "camera";
    draft.read = "sem-leitura";
    draft.imageDataUrl = canvas.toDataURL("image/jpeg", 0.7);
    draft.imageLabel = "Foto deste aparelho. Não foi enviada.";
    draft.simulated = false;
    state.draft = draft;
    stopCamera();
    persist();
    go("#conferir");
  }

  function onFile(file) {
    if (!file) return;
    const okType = /^image\/(jpeg|png|webp)$/.test(file.type);
    if (!okType || file.size > 8 * 1024 * 1024) {
      state.notice = "Use uma imagem JPEG, PNG ou WebP de até 8 MB.";
      render();
      return;
    }
    const reader = new FileReader();
    reader.onload = function () {
      const draft = state.draft || blankDraft("gasto", "galeria");
      draft.source = "galeria";
      draft.read = "sem-leitura";
      draft.imageDataUrl = String(reader.result || "");
      draft.imageLabel = "Imagem escolhida neste aparelho. Não foi enviada.";
      draft.simulated = false;
      state.draft = draft;
      state.notice = "";
      persist();
      go("#conferir");
    };
    reader.readAsDataURL(file);
  }

  function draftFromForm() {
    const form = document.getElementById("review-form");
    if (!form || !state.draft) return state.draft;
    const data = new FormData(form);
    ["merchant", "noteDate", "dueDate", "statusDate", "amountText", "category", "status", "nature", "currency"].forEach(function (key) {
      state.draft[key] = String(data.get(key) || "");
    });
    return state.draft;
  }

  function validate(draft) {
    const issues = [];
    const money = parseMoney(draft.amountText);
    if (draft.currency !== "BRL" || money.review) issues.push("moeda");
    if (money.missing || money.review) issues.push("valor");
    if (!draft.merchant.trim()) issues.push("estabelecimento");
    if (!draft.status) issues.push("situacao");
    if ((draft.status === "pago" || draft.status === "recebido") && !draft.statusDate) issues.push("data-situacao");
    if ((draft.status === "a_pagar" || draft.status === "a_receber") && draft.statusDate) issues.push("data-aberta");
    return { issues: issues, money: money };
  }

  function saveDraft() {
    const draft = draftFromForm();
    if (!draft || draft.saving) return;
    if (draft.read === "ilegivel" || draft.read === "falha" || draft.read === "processando") return;
    const check = validate(draft);
    if (check.issues.length) {
      state.notice = "Ainda há campo para conferir.";
      draft.issues = check.issues;
      render();
      return;
    }
    const candidate = {
      id: draft.id,
      ownerId: state.personId,
      merchant: draft.merchant.trim(),
      noteDate: draft.noteDate,
      amountMinor: check.money.amountMinor,
      documentId: draft.documentId,
      fingerprint: draft.fingerprint,
      archived: false,
    };
    const dup = draft.allowDuplicate ? null : IsaCalc.findDuplicate(candidate, mine());
    if (dup) {
      draft.duplicateOf = dup.entry.id;
      draft.duplicateKind = dup.kind;
      state.notice = "";
      render();
      return;
    }
    draft.saving = true;
    const now = new Date().toISOString();
    const record = {
      id: draft.id || ("lan-" + Date.now().toString(36)),
      ownerId: state.personId,
      direction: draft.direction,
      nature: draft.nature || "consumo",
      merchant: draft.merchant.trim(),
      noteDate: draft.noteDate,
      dueDate: draft.status === "pago" || draft.status === "recebido" ? "" : draft.dueDate,
      statusDate: draft.status === "pago" || draft.status === "recebido" ? draft.statusDate : "",
      amountMinor: check.money.amountMinor,
      currency: draft.currency || "BRL",
      accountId: draft.accountId || "",
      category: draft.category,
      categorizationStatus: draft.category ? "categorizado" : "a_categorizar",
      userLocked: !!draft.category,
      status: draft.status,
      source: draft.source,
      simulated: !!draft.simulated,
      documentId: draft.documentId || "",
      fingerprint: draft.fingerprint || "",
      imageLabel: draft.imageLabel || "",
      archived: false,
      updatedAt: now,
    };
    if (window.isaPublic) {
      api("POST", "/api/entries", { entry: record }).then(function (result) {
        if (!result.ok || !result.data.workspace) {
          draft.saving = false;
          state.notice = (result.data && result.data.error) || "Não foi possível salvar. O lançamento não entrou.";
          render();
          return;
        }
        applyWorkspace(result.data.workspace);
        const monthHint = (record.statusDate || record.dueDate || record.noteDate || "").slice(0, 7);
        if (monthHint) state.month = monthHint;
        state.draft = null;
        state.notice = "Lançamento gravado.";
        persist();
        go("#detalhe/" + record.id);
      }).catch(function () {
        draft.saving = false;
        state.notice = "Não foi possível salvar. O lançamento não entrou.";
        render();
      });
      return;
    }
    const index = state.entries.findIndex(function (entry) { return entry.id === record.id; });
    if (index >= 0) state.entries[index] = Object.assign(state.entries[index], record);
    else state.entries.push(record);
    const monthHint = (record.statusDate || record.dueDate || record.noteDate || "").slice(0, 7);
    if (monthHint) state.month = monthHint;
    state.draft = null;
    state.notice = index >= 0 ? "Lançamento atualizado." : "Lançamento gravado uma vez.";
    persist();
    go("#detalhe/" + record.id);
  }

  window.isaRefreshEntries = function () {
    return api("GET", "/api/workspace").then(function (r) {
      if (r.ok) { applyWorkspace(r.data); render(); }
    });
  };

  function openEntry(id) {
    state.draft = null;
    go("#detalhe/" + id);
  }

  function editEntry(id) {
    const entry = mine().find(function (item) { return item.id === id; });
    if (!entry) return;
    state.draft = {
      id: entry.id,
      direction: entry.direction,
      nature: entry.nature,
      merchant: entry.merchant,
      noteDate: entry.noteDate,
      dueDate: entry.dueDate || "",
      statusDate: entry.statusDate || "",
      amountText: (entry.amountMinor / 100).toFixed(2).replace(".", ","),
      currency: "BRL",
      category: entry.category,
      status: entry.status,
      source: entry.source,
      read: "manual",
      documentId: entry.documentId,
      fingerprint: entry.fingerprint,
      imageLabel: entry.imageLabel,
      simulated: entry.simulated,
      allowDuplicate: true,
      saving: false,
    };
    go("#conferir");
  }

  function archiveEntry(id, archived) {
    const entry = state.entries.find(function (item) { return item.id === id && item.ownerId === state.personId; });
    if (!entry) return;
    if (window.isaPublic) {
      const next = Object.assign({}, entry, { archived: archived });
      api("POST", "/api/entries", { entry: next }).then(function (result) {
        if (!result.ok || !result.data.workspace) {
          state.notice = "Não foi possível salvar.";
          render();
          return;
        }
        applyWorkspace(result.data.workspace);
        state.notice = archived ? "Lançamento arquivado. Dá para restaurar no filtro Arquivados." : "Lançamento restaurado.";
        persist();
        render();
      }).catch(function () {
        state.notice = "Não foi possível salvar.";
        render();
      });
      return;
    }
    entry.archived = archived;
    state.notice = archived ? "Lançamento arquivado. Dá para restaurar no filtro Arquivados." : "Lançamento restaurado.";
    persist();
    render();
  }

  function filtered() {
    const f = state.filters;
    return mine().filter(function (entry) {
      if (!!entry.archived !== !!f.archived) return false;
      const when = entry.statusDate || entry.dueDate || entry.noteDate || "";
      if (when.slice(0, 7) !== state.month && f.mode !== "todos-meses") return false;
      if (f.direction && entry.direction !== f.direction) return false;
      if (f.category && entry.category !== f.category) return false;
      if (f.status && entry.status !== f.status) return false;
      if (f.mode === "resultado" && (!(entry.status === "pago" || entry.status === "recebido") || (entry.nature && entry.nature !== "consumo"))) return false;
      if (f.consumption && entry.nature && entry.nature !== "consumo") return false;
      if (f.q) {
        const blob = (entry.merchant + " " + entry.category).toLocaleLowerCase("pt-BR");
        if (!blob.includes(f.q.toLocaleLowerCase("pt-BR"))) return false;
      }
      return true;
    });
  }

  function esc(value) {
    return String(value || "").replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function person() {
    if (!state.personId) return null;
    const profile = state.profile || {};
    if (window.isaPublic && state.personId) {
      return {
        id: state.personId,
        name: profile.displayName || "",
        ready: profile.ready === true,
        accessLabel: profile.accessLabel || "Sessão individual deste piloto",
      };
    }
    const found = Object.values(PEOPLE).find(function (item) { return item.id === state.personId; }) || { id: state.personId, name: "" };
    return {
      id: found.id,
      name: profile.displayName || found.name || "",
      ready: true,
      accessLabel: profile.accessLabel || "Demonstração nesta máquina",
    };
  }

  function personHeading(who) {
    if (!who || who.ready === false) return "Carregando";
    return who.name || "Seu perfil";
  }

  function render() {
    document.body.classList.toggle("text-lg", state.font === "large");
    const root = document.getElementById("app");
    const route = location.hash || "#entrar";
    if (!state.personId && route !== "#entrar") {
      location.hash = "#entrar";
      return;
    }
    if (route.indexOf("#detalhe/") === 0) root.innerHTML = viewDetail(route.slice(9));
    else if (route === "#inicio") root.innerHTML = viewHome();
    else if (route === "#lancamentos") root.innerHTML = viewList();
    else if (route === "#perfil") root.innerHTML = viewProfile();
    else if (route === "#contas" || route.indexOf("#contas/") === 0) root.innerHTML = viewAccounts(route);
    else if (route === "#registrar") root.innerHTML = viewRegister();
    else if (route === "#origem") root.innerHTML = viewOrigin();
    else if (route === "#conferir") root.innerHTML = viewReview();
    else if (route === "#importar") root.innerHTML = viewImport();
    else if (route === "#pendencias") root.innerHTML = viewPending();
    else if (route === "#planejar" || route.indexOf("#planejar/") === 0) root.innerHTML = shell("Planejar", destinationLine() + '<div id="plan-root"><p class="muted">Carregando suas informações…</p></div>');
    else root.innerHTML = viewGate();
    document.body.classList.toggle("wide-import", route === "#importar" || route === "#pendencias" || route === "#planejar" || route.indexOf("#planejar/") === 0);
    document.body.classList.toggle("wide-home", route === "#inicio");
    document.body.classList.toggle("wide-accounts", route === "#contas" || route.indexOf("#contas/") === 0 || route === "#perfil");
    if (state.personId) {
      const dock = document.createElement("div");
      dock.className = "dock";
      const hideRegistrar = route === "#importar" || route === "#conferir" || route === "#pendencias" || route === "#planejar" || route.indexOf("#planejar/") === 0;
      const current = function (hash) {
        if (hash === "#planejar") return route === "#planejar" || route.indexOf("#planejar/") === 0;
        if (hash === "#contas") return route === "#contas" || route.indexOf("#contas/") === 0;
        return route === hash;
      };
      const navButton = function (id, hash, label, icon) {
        return '<button type="button" id="' + id + '"' + (current(hash) ? ' aria-current="page"' : "") + ">" + icon + "<span>" + label + "</span></button>";
      };
      dock.innerHTML =
        '<nav class="nav" aria-label="Principal">' +
        navButton("nav-inicio", "#inicio", "Início", icon("home")) +
        navButton("nav-lista", "#lancamentos", "Lançamentos", icon("list")) +
        (hideRegistrar ? "" : '<button type="button" class="go" id="nav-registrar"><span>Registrar</span></button>') +
        navButton("nav-planejar", "#planejar", "Planejar", icon("plan")) +
        navButton("nav-contas", "#contas", "Contas", icon("account")) +
        "</nav>";
      root.appendChild(dock);
      document.getElementById("nav-inicio").onclick = function () { go("#inicio"); };
      const registrar = document.getElementById("nav-registrar");
      if (registrar) registrar.onclick = function () { state.draft = null; state.notice = ""; go("#registrar"); };
      document.getElementById("nav-lista").onclick = function () { go("#lancamentos"); };
      document.getElementById("nav-planejar").onclick = function () { go("#planejar"); };
      document.getElementById("nav-contas").onclick = function () { go("#contas"); };
    }
    window.isaLabPerson = state.personId === "pessoa-paulo" ? "paulo" : state.personId === "pessoa-marina" ? "marina" : state.personId === "pessoa-eveline-demo" ? "eveline" : "";
    bind();
    if (window.IsaHome && route === "#inicio") IsaHome.open();
    if (window.IsaPlan && (route === "#planejar" || route.indexOf("#planejar/") === 0)) IsaPlan.open();
    if (window.IsaAssistant) window.IsaAssistant.mount();
    const title = root.querySelector("h1");
    if (title) {
      title.setAttribute("tabindex", "-1");
      document.title = title.textContent + " — ISA";
    }
  }

  function icon(name) {
    const paths = {
      home: '<path d="M4 11 L12 4 L20 11 V20 H15 V14 H9 V20 H4 Z" fill="none" stroke="currentColor" stroke-width="1.6"/>',
      list: '<path d="M6 7 H18 M6 12 H18 M6 17 H14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
      plan: '<rect x="5" y="5" width="14" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 10 H16 M8 14 H13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
      account: '<rect x="4" y="7" width="16" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M4 11 H20" stroke="currentColor" stroke-width="1.6"/>',
      user: '<circle cx="12" cy="9" r="3" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6 19c1.4-3 3.6-4.2 6-4.2S16.6 16 18 19" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    };
    return '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true">' + (paths[name] || "") + "</svg>";
  }

  function accountSwitch() {
    const accounts = (state.accounts || []).filter(function (item) { return item.status !== "inactive"; });
    const current = window.isaAccountContext || "all";
    const options = '<option value="all"' + (current === "all" ? " selected" : "") + ">Todas as contas</option>" +
      accounts.map(function (item) {
        const inst = item.institution ? " · " + item.institution : "";
        const moneyName = item.currency && item.currency !== "BRL" ? " · " + item.currency : "";
        return '<option value="' + esc(item.id) + '"' + (item.id === current ? " selected" : "") + ">" + esc(item.name + inst + moneyName) + "</option>";
      }).join("");
    return '<label class="account-switch">Visualizando<select id="account-switch" aria-label="Visualizando">' + options + "</select></label>";
  }

  function destinationLine() {
    const chosen = (state.accounts || []).find(function (item) { return item.id === window.isaAccountContext; });
    if (!chosen || window.isaAccountContext === "all") return '<p class="money-context">Destino: sem conta definida, até você escolher uma.</p>';
    return '<p class="money-context">Destino: ' + esc(chosen.name) + " · " + esc(chosen.currencyName || chosen.currency) + ".</p>";
  }

  function shell(title, body) {
    const who = person();
    const route = location.hash || "#entrar";
    const current = function (hash) {
      if (hash === "#planejar") return route === "#planejar" || route.indexOf("#planejar/") === 0;
      if (hash === "#contas") return route === "#contas" || route.indexOf("#contas/") === 0;
      return route === hash;
    };
    const link = function (hash, label, id) {
      const on = current(hash);
      return '<a class="brand-link' + (on ? " is-current" : "") + '" href="' + hash + '" id="' + id + '"' + (on ? ' aria-current="page"' : "") + ">" + label + "</a>";
    };
    const menu = who
      ? '<nav class="brand-nav" aria-label="Áreas">' +
        link("#inicio", "Início", "desk-inicio") +
        link("#lancamentos", "Lançamentos", "desk-lista") +
        link("#planejar", "Planejar", "desk-planejar") +
        link("#contas", "Contas", "desk-contas") +
        link("#perfil", "Perfil", "desk-perfil") +
        '<a class="brand-go" href="#registrar" id="desk-registrar">Registrar</a></nav>'
      : "";
    const identity = who
      ? '<div class="identity"><a class="brand-who" href="#perfil" id="brand-person" title="' + esc(who.name || "Como você quer aparecer na ISA") + '">' + esc(personHeading(who)) + '</a><button type="button" class="brand-leave" id="brand-leave">Sair</button></div>'
      : "";
    return (
      '<header class="brand-bar"><div class="brand-top"><a class="brand-mark" href="' + (who ? "#inicio" : "#entrar") + '" aria-label="ISA"><img src="logoisantrans.png" alt="ISA" width="168" height="48"></a>' +
      (who ? accountSwitch() + identity : "") +
      "</div>" + menu +
      "</header><div class=\"page\"><h1>" + title + "</h1>" +
      body +
      "</div>"
    );
  }

  function viewGate() {
    if (window.isaPublic) {
      return shell(
        "Sua vida financeira, em um lugar só seu",
        "<p>Depois de entrar, duas ações: registrar um lançamento ou importar um extrato. Em seguida a ISA pergunta quanto está disponível, quando entra dinheiro e o que precisa pagar.</p>" +
        (state.recovery ? '<p class="note">' + esc(state.recovery) + "</p>" : "") +
        (window.isaRehearsal ? '<p class="note">Este botão entra por um provedor de ensaio nesta máquina. Não é o diretório real.</p>' : "") +
        '<div class="stack"><button class="primary" type="button" id="enter-public">Entrar</button>' +
        '<button class="quiet" type="button" id="recover-access">Recuperar o acesso</button></div>' +
        '<p class="muted">O acesso é individual. Os nomes de quem participa não aparecem nesta página.</p>'
      );
    }
    return shell(
      "Sua vida financeira, sem a empresa",
      '<p class="muted">Conta individual de demonstração. Nenhuma senha é pedida ou guardada.</p>' +
      (state.recovery ? '<p class="note">' + esc(state.recovery) + "</p>" : "") +
      '<div class="stack">' +
      '<button class="primary" type="button" id="enter-marina">Entrar como Marina Alves</button>' +
      '<button class="secondary" type="button" id="enter-paulo">Entrar como Paulo Nunes</button>' +
      '<button class="secondary" type="button" id="enter-eveline">Entrar como Eveline</button>' +
      '<button class="quiet" type="button" id="forgot">Esqueci o acesso</button>' +
      "</div>" +
      '<p class="muted">Na demonstração, o nome não abre a conta real de ninguém. Marina, Paulo e a Eveline de exemplo não veem os lançamentos uns dos outros.</p>'
    );
  }

  function viewHome() {
    const summary = IsaCalc.summarize(mine(), state.month);
    const recent = mine()
      .filter(function (entry) { return !entry.archived; })
      .slice()
      .sort(function (a, b) { return String(b.updatedAt).localeCompare(String(a.updatedAt)); })
      .slice(0, 4);
    const cats = Object.keys(summary.paidByCategory);
    const max = cats.reduce(function (acc, key) { return Math.max(acc, summary.paidByCategory[key]); }, 0);
    const chart = cats.length
      ? cats.map(function (cat) {
          const width = Math.max(8, Math.round((summary.paidByCategory[cat] / max) * 100));
          return '<button type="button" class="bar" data-cat="' + esc(cat) + '"><span>' + esc(cat) + "</span><span class=\"track\"><i style=\"width:" + width + '%\"></i></span><span>' + brl(summary.paidByCategory[cat]) + "</span></button>";
        }).join("")
      : "";
    const empty = !mine().some(function (entry) { return !entry.archived; });
    const partial = summary.unidentified > 0;
    const emptyFigure = partial ? "Nada identificado" : "Nada neste mês";
    return shell(
      "Seu dinheiro",
      '<div id="money-home"><p class="muted">Carregando suas informações…</p></div>' +
      '<section class="history"><h2>O que já aconteceu</h2>' +
      '<p class="muted">' + esc(monthName(state.month)) + ". Ganhos recebidos e gastos pagos. Não é o dinheiro disponível nem a projeção.</p>" +
      monthControl() +
      '<button type="button" class="secondary" id="open-import">Importar extrato</button>' +
      (pendingCount() ? '<button type="button" class="secondary" id="open-pending">Ver o que falta conferir (' + pendingCount() + ")</button>" : "") +
      (empty
        ? '<p class="muted">Este mês ainda não tem lançamento registrado.</p>'
        : '<div class="figures">' +
          figure("Ganhos recebidos", summary.received, "recebido", emptyFigure) +
          figure("Gastos pagos", summary.paid, "pago", emptyFigure) +
          '<button type="button" class="figure wide" data-mode="resultado"><small>' + (partial ? "Resultado identificado até agora" : "Resultado do mês") + "</small><strong>" + brl(summary.result) + '</strong><span class="meta">' + (partial ? summary.unidentified + " movimentações ainda sem natureza. Não é o resultado completo nem saldo disponível." : "Recebidos menos pagos. Não é saldo disponível.") + "</span></button>" +
          "</div>" +
          (partial ? '<p class="note">' + summary.unidentified + " movimentações do extrato ainda sem natureza. Entradas " + brl(summary.bankIn) + " e saídas " + brl(summary.bankOut) + ". O resultado não está completo.</p>" : "") +
          (summary.rende ? '<p class="muted">Há ' + brl(summary.rende) + " em movimentação BB Rende Fácil. O extrato não separa aplicação e rendimento, e não forma um patrimônio investido.</p>" : "") +
          (summary.excluded ? '<p class="note">Há ' + brl(summary.excluded) + " em transferência, reembolso ou empréstimo. Esse valor fica fora do resultado.</p>" : "") +
          (summary.aside ? '<p class="muted">Há ' + brl(summary.aside) + " fora do consumo. Também fica fora do resultado.</p>" : "") +
          (latestBalanceNote() ? '<p class="muted">Saldo informado no extrato em ' + showDate(latestBalanceNote().date) + ": " + brl(latestBalanceNote().cents) + ". Não é o resultado do mês nem saldo disponível.</p>" : "") +
          "<h2>Gastos pagos por categoria</h2>" +
          (chart || '<p class="muted">' + (partial ? "Nenhum gasto com natureza definida neste mês." : "Nenhum gasto pago neste mês.") + "</p>") +
          "<h2>Últimos lançamentos</h2>" +
          (recent.map(itemHtml).join("") || '<p class="muted">Nada por aqui.</p>')) +
      "</section>"
    );
  }

  function figure(label, amount, status, emptyText) {
    return '<button type="button" class="figure" data-status="' + status + '"><small>' + label + "</small><strong>" + (amount ? brl(amount) : esc(emptyText || "Nada neste mês")) + "</strong></button>";
  }

  function monthControl() {
    return '<div class="month"><button type="button" id="prev-month">Mês anterior</button><button type="button" id="next-month">Próximo mês</button></div>';
  }

  function monthName(key) {
    const [year, month] = key.split("-");
    const names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
    return names[Number(month) - 1] + " de " + year;
  }

  function shiftMonth(delta) {
    const [year, month] = state.month.split("-").map(Number);
    const date = new Date(year, month - 1 + delta, 1);
    state.month = date.getFullYear() + "-" + String(date.getMonth() + 1).padStart(2, "0");
    persist();
    render();
  }

  function isStatementEntry(entry) {
    return !!entry && (entry.source === "exemplo-sintetico" || entry.source === "arquivo-teste" || entry.source === "extrato-sintetico");
  }

  function movementKind(entry) {
    if (entry.nature === "bb_rende_facil" || entry.nature === "a_conferir") return entry.direction === "ganho" ? "Entrada" : "Saída";
    return entry.direction === "ganho" ? "Ganho" : "Gasto";
  }

  function itemHtml(entry) {
    const tag = entry.direction === "ganho" ? "ganho" : "";
    const open = entry.status === "a_pagar" || entry.status === "a_receber" ? " aberto" : "";
    const category = entry.category || (entry.nature === "consumo" ? "A categorizar" : "Sem categoria");
    return '<button type="button" class="item" data-id="' + esc(entry.id) + '"><span class="tag ' + tag + open + '">' +
      esc(movementKind(entry)) + " · " + esc(statusLabel(entry.status)) +
      '</span><strong>' + esc(entry.merchant) + "</strong><span>" + brl(entry.amountMinor) + " · " + esc(category) +
      (entry.nature && entry.nature !== "consumo" ? " · " + esc(natureLabel(entry.nature)) : "") +
      (isStatementEntry(entry) ? " · Extrato BB · " + esc(classLabel(entry.categorizationStatus)) : "") +
      "</span></button>";
  }

  function viewList() {
    const rows = filtered();
    const options = [""].concat(EXPENSE_CATS.filter(function (cat) { return INCOME_CATS.indexOf(cat) === -1; }), INCOME_CATS).filter(function (cat, index, all) {
      return all.indexOf(cat) === index;
    });
    return shell(
      "Lançamentos",
      (state.notice ? '<p class="oknote">' + esc(state.notice) + "</p>" : "") +
      '<button type="button" class="secondary" id="open-import">Importar extrato</button>' +
      (pendingCount() ? '<button type="button" class="secondary" id="open-pending">Ver o que falta conferir (' + pendingCount() + ")</button>" : "") +
      monthControl() +
      (state.filters.mode === "resultado" ? '<p class="muted">Estes são os recebidos e os pagos que formam o resultado. O que ainda vai acontecer, e a transferência, ficam de fora.</p>' : "") +
      '<div class="filters">' +
      '<label>Busca<input id="q" value="' + esc(state.filters.q) + '" placeholder="Descrição ou lugar"></label>' +
      '<label>Tipo<select id="f-dir"><option value="">Ganhos e gastos</option><option value="ganho">Ganhos</option><option value="gasto">Gastos</option></select></label>' +
      '<label>Categoria<select id="f-cat">' + options.map(function (cat) { return '<option value="' + esc(cat) + '">' + (cat || "Todas") + "</option>"; }).join("") + "</select></label>" +
      '<label>Situação<select id="f-status"><option value="">Todas</option><option value="pago">Pago</option><option value="a_pagar">A pagar</option><option value="recebido">Recebido</option><option value="a_receber">A receber</option></select></label>' +
      '<label><input type="checkbox" id="f-arch"> Arquivados</label>' +
      "</div>" +
      '<div class="list">' + (rows.map(itemHtml).join("") || '<div class="empty"><p>Nada com esses filtros. ' + (state.filters.archived ? "Não há arquivados neste mês." : "Registre um lançamento ou mude o mês.") + "</p></div>") + "</div>"
    );
  }

  function viewRegister() {
    return shell(
      "O que você quer registrar?",
      destinationLine() +
      '<div class="choices"><button type="button" class="choice" id="pick-gasto"><strong>Gasto</strong><span>Algo que você pagou ou ainda vai pagar.</span></button><button type="button" class="choice" id="pick-ganho"><strong>Ganho</strong><span>Algo que você recebeu ou ainda vai receber.</span></button></div>'
    );
  }

  function viewOrigin() {
    const draft = state.draft || blankDraft("gasto", "");
    return shell(
      draft.direction === "ganho" ? "Como lançar o ganho" : "Como lançar o gasto",
      (window.isaPublic
        ? '<p class="muted">Neste piloto o lançamento é digitado. A leitura automática de foto ainda não faz parte.</p>'
        : '<p class="muted">Fotografar, escolher imagem ou digitar. Enviar um arquivo não grava o lançamento.</p>') +
      (state.cameraError ? '<p class="note">' + esc(state.cameraError) + "</p>" : "") +
      (state.notice ? '<p class="note">' + esc(state.notice) + "</p>" : "") +
      '<div class="video-wrap" id="video-wrap"></div>' +
      (window.isaPublic
        ? '<div class="choices"><button type="button" class="choice" id="do-type"><strong>Digitar</strong><span>Você preenche o que é, o valor e a data.</span></button></div>'
        : '<div class="choices">' +
          '<button type="button" class="choice" id="do-photo"><strong>Fotografar comprovante</strong><span>Se a câmera for negada, a galeria e a digitação continuam disponíveis.</span></button>' +
          '<button type="button" class="choice" id="do-file"><strong>Escolher imagem</strong><span>A imagem fica neste aparelho. A leitura automática daqui é simulada.</span></button>' +
          '<button type="button" class="choice" id="do-type"><strong>Digitar</strong><span>Sem foto. Você preenche os campos curtos.</span></button>' +
          "</div>" +
          '<h2>Exemplos sintéticos de leitura</h2>' +
          '<p class="muted">Nenhuma IA é chamada. Os textos abaixo são inventados para a aprovação visual.</p>' +
          '<div class="stack">' +
          '<button type="button" class="secondary" id="sim-boa">Simular leitura boa</button>' +
          '<button type="button" class="secondary" id="sim-parcial">Simular leitura parcial</button>' +
          '<button type="button" class="secondary" id="sim-ilegivel">Simular imagem ilegível</button>' +
          '<button type="button" class="secondary" id="sim-falha">Simular falha de serviço</button>' +
          '<button type="button" class="secondary" id="sim-dup">Simular possível duplicata</button>' +
          "</div>") +
      '<input id="file" type="file" accept="image/jpeg,image/png,image/webp" hidden>'
    );
  }

  function viewReview() {
    const draft = state.draft;
    if (!draft) return shell("Conferir", '<p>Nada para conferir.</p><button class="secondary" type="button" id="back-origin">Voltar</button>');
    if (draft.read === "processando") {
      return shell("Lendo o exemplo", '<p class="note">Processando um exemplo sintético. Nada foi gravado e nenhum serviço externo foi chamado.</p>');
    }
    if (draft.read === "falha") {
      return shell("A leitura não aconteceu", '<p class="note">Falha simulada. O comprovante não foi gravado. Você pode tentar de novo, escolher outra imagem ou digitar.</p><div class="stack"><button class="primary" type="button" id="retry-sim">Tentar o exemplo de novo</button><button class="secondary" type="button" id="back-origin">Voltar sem gravar</button></div>');
    }
    if (draft.read === "ilegivel") {
      return shell("Não deu para ler", '<div class="thumb">' + esc(draft.imageLabel || "Imagem ilegível") + '</div><p class="note">A imagem de exemplo não tem campos confiáveis. Repita a foto, escolha outra imagem ou digite. Nada foi gravado.</p><div class="stack"><button class="primary" type="button" id="back-origin">Repetir ou escolher outro caminho</button></div>');
    }
    const issues = draft.issues || [];
    const suspect = function (name) { return issues.indexOf(name) >= 0 ? " suspect" : ""; };
    const money = parseMoney(draft.amountText);
    const detected = draft.allowDuplicate ? null : IsaCalc.findDuplicate({
      id: draft.id,
      merchant: draft.merchant,
      noteDate: draft.noteDate,
      amountMinor: money.amountMinor || 0,
      documentId: draft.documentId,
      fingerprint: draft.fingerprint,
    }, mine());
    const dup = detected ? detected.entry : null;
    if (detected) {
      draft.duplicateOf = detected.entry.id;
      draft.duplicateKind = detected.kind;
    }
    const soft = !dup && IsaCalc.sameAmountAndDateOnly({
      id: draft.id,
      merchant: draft.merchant,
      noteDate: draft.noteDate,
      amountMinor: money.amountMinor || 0,
    }, mine());
    const statuses = draft.direction === "ganho"
      ? [["a_receber", "A receber"], ["recebido", "Recebido"]]
      : [["a_pagar", "A pagar"], ["pago", "Pago"]];
    const settled = draft.status === "pago" || draft.status === "recebido";
    const whenLabel = draft.direction === "ganho" ? "Quando recebeu?" : "Quando pagou?";
    return shell(
      draft.id ? "Corrigir lançamento" : "Conferir antes de gravar",
      (draft.simulated ? '<p class="oknote">Leitura simulada. Confira os campos. A data do documento não quita o lançamento.</p>' : "") +
      (draft.read === "parcial" ? '<p class="note">Leitura parcial: o que ficou vazio precisa de você. Não há percentual de confiança.</p>' : "") +
      (state.notice ? '<p class="note">' + esc(state.notice) + "</p>" : "") +
      (dup ? '<p class="note">Possível duplicata pelo ' + esc(draft.duplicateKind) + ". " + esc(dup.merchant) + " · " + brl(dup.amountMinor) + '.</p><div class="split"><button type="button" class="secondary" id="open-dup">Abrir o existente</button><button type="button" class="secondary" id="keep-dup">É outro lançamento</button></div>' : "") +
      (soft ? '<p class="muted">Há outro lançamento com o mesmo valor e a mesma data. Isso sozinho não bloqueia. Confira se é outro.</p>' : "") +
      (draft.source === "digitado" ? "" : '<div class="thumb">' + (draft.imageDataUrl ? '<img alt="Comprovante neste aparelho" src="' + draft.imageDataUrl + '">' : esc(draft.imageLabel || "Sem imagem.")) + "</div>") +
      '<form id="review-form" class="stack">' +
      field("Estabelecimento ou descrição", "merchant", draft.merchant, "text", suspect("estabelecimento"), "Nome do lugar") +
      field("Data do documento", "noteDate", draft.noteDate, "date", "", "") +
      field("Valor em real, como 42,80", "amountText", draft.amountText, "text", suspect("valor") || suspect("moeda"), "") +
      (money.review || draft.currency !== "BRL" ? '<p class="note">Este formato ou moeda precisa de revisão. A ISA não converte sozinha.</p>' : "") +
      (draft.id ? '<div class="field"><label for="category">Categoria</label><select id="category" name="category">' +
      '<option value="">Deixar para depois</option>' + cats(draft.direction).map(function (cat) {
        return '<option' + (cat === draft.category ? " selected" : "") + ">" + esc(cat) + "</option>";
      }).join("") + "</select></div>" : '<p class="muted">Salve o lançamento. A ISA cuida da categoria depois.</p>') +
      '<div class="field"><label for="nature">Isto é consumo?</label><select id="nature" name="nature">' +
      ["consumo", "transferencia", "reembolso", "emprestimo", "bb_rende_facil", "aplicacao", "a_conferir"].map(function (nature) {
        return '<option value="' + nature + '"' + (draft.nature === nature ? " selected" : "") + ">" + esc(natureLabel(nature)) + "</option>";
      }).join("") + "</select></div>" +
      '<div class="field' + suspect("situacao") + '"><label for="status">Situação</label><select id="status" name="status">' +
      statuses.map(function (pair) {
        return '<option value="' + pair[0] + '"' + (draft.status === pair[0] ? " selected" : "") + ">" + pair[1] + "</option>";
      }).join("") + "</select></div>" +
      (settled
        ? '<div class="field' + suspect("data-situacao") + '"><label for="statusDate">' + whenLabel + '</label><input id="statusDate" name="statusDate" type="date" value="' + esc(draft.statusDate) + '"></div>'
        : '<div class="field"><label for="dueDate">Vence quando?</label><input id="dueDate" name="dueDate" type="date" value="' + esc(draft.dueDate) + '"></div>') +
      '<input type="hidden" name="currency" value="BRL">' +
      '<button class="primary" type="submit" id="save">Confirmar lançamento</button>' +
      '<button class="secondary" type="button" id="cancel">Cancelar</button>' +
      "</form>"
    );
  }

  function field(label, name, value, type, suspect, placeholder) {
    return '<div class="field' + suspect + '"><label for="' + name + '">' + label + '</label><input id="' + name + '" name="' + name + '" type="' + type + '" value="' + esc(value) + '"' + (placeholder ? ' placeholder="' + esc(placeholder) + '"' : "") + "></div>";
  }

  function viewDetail(id) {
    const entry = mine().find(function (item) { return item.id === id; });
    if (!entry) return shell("Lançamento", '<p>Este lançamento não está na sua conta.</p>');
    return shell(
      entry.merchant,
      (state.notice ? '<p class="oknote">' + esc(state.notice) + "</p>" : "") +
      '<p><span class="tag ' + (entry.direction === "ganho" ? "ganho" : "") + (entry.status.indexOf("a_") === 0 ? " aberto" : "") + '">' +
      esc(movementKind(entry)) + " · " + esc(statusLabel(entry.status)) + "</span></p>" +
      '<div class="detail-block" style="padding:12px"><p><strong>' + brl(entry.amountMinor) + "</strong></p>" +
      "<p>Categoria: " + esc(entry.category || "A ISA vai ajudar a organizar") + "</p>" +
      (entry.aiReason ? '<p class="ai-reason">' + esc(entry.aiReason) + '</p>' : "") +
      "<p>Natureza: " + esc(natureLabel(entry.nature)) + "</p>" +
      "<p>Data do documento: " + esc(entry.noteDate || "não informada") + "</p>" +
      "<p>" + (entry.status === "pago" || entry.status === "recebido" ? "Quando pagou ou recebeu: " + esc(entry.statusDate || "não informada") : "Vence quando: " + esc(entry.dueDate || "não informado")) + "</p>" +
      (isStatementEntry(entry)
        ? "<p>Origem: Extrato BB" + (window.isaPublic ? "." : (entry.source === "arquivo-teste" ? ", arquivo de teste." : ", exemplo sintético.")) + " A descrição acima é a do banco.</p><p>Classificação: " + esc(classLabel(entry.categorizationStatus)) + ". Nenhuma IA foi consultada.</p>"
        : "<p>" + esc(entry.imageLabel || "Sem comprovante anexado.") + (entry.simulated ? " Marcado como simulação." : "") + "</p>") +
      "</div>" +
      (linkCandidate(entry) ? '<p class="note">Há um lançamento com o mesmo valor e a mesma data. Pode ser o mesmo fato.</p><button type="button" class="secondary" id="link-same">Confirmar vínculo</button>' : "") +
      (entry.linkId ? '<button type="button" class="secondary" id="unlink">Desfazer vínculo</button>' : "") +
      (state.confirmArchive === entry.id
        ? '<p class="note">Arquivar tira o lançamento do mês. Ele continua recuperável.</p><div class="split"><button type="button" class="primary" id="do-archive">Arquivar</button><button type="button" class="secondary" id="no-archive">Manter</button></div>'
        : '<div class="stack"><button type="button" class="primary" id="edit">Corrigir</button>' +
          (!window.isaPublic && isStatementEntry(entry) && !entry.userLocked ? '<button type="button" class="secondary" id="classify-demo">Tentar classificação demonstrativa</button><button type="button" class="quiet" id="classify-fail">Simular falha da classificação</button>' : "") +
          (entry.archived ? '<button type="button" class="secondary" id="restore">Restaurar</button>' : '<button type="button" class="secondary" id="ask-archive">Arquivar</button>') +
          '<button type="button" class="quiet" id="back-list">Voltar aos lançamentos</button></div>')
    );
  }

  function classLabel(status) {
    return { a_categorizar: "A categorizar", categorizado: "Categorizado", precisa_de_ajuda: "Precisa de ajuda" }[status] || "A categorizar";
  }

  function linkCandidate(entry) {
    return mine().find(function (other) {
      if (!entry || other.id === entry.id || entry.linkId || other.linkId) return false;
      if (other.amountMinor !== entry.amountMinor) return false;
      const day = entry.statusDate || entry.noteDate;
      return !!day && day === (other.statusDate || other.noteDate) && isStatementEntry(entry) !== isStatementEntry(other);
    });
  }

  function showDate(iso) {
    const parts = String(iso || "").split("-");
    if (parts.length !== 3) return "";
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function latestBalanceNote() {
    const notes = (state.statementNotes || []).filter(function (note) {
      return note.ownerId === state.personId && (note.class === "saldo_informado" || note.class === "saldo_do_dia");
    });
    return notes.length ? notes[notes.length - 1] : null;
  }

  function ensureAccount() {
    if (!state.accounts) state.accounts = [];
    const id = "conta-bb-" + state.personId;
    if (!state.accounts.some(function (account) { return account.id === id; })) {
      state.accounts.push({ id: id, ownerId: state.personId, name: "Conta BB", currency: "BRL", declared: true });
    }
    if (!state.importAccountId) state.importAccountId = id;
    return state.accounts.filter(function (account) { return account.ownerId === state.personId && account.currency === "BRL"; });
  }

  function sameBatch(accountId, preview) {
    return (state.batches || []).some(function (batch) {
      return batch.ownerId === state.personId && batch.accountId === accountId && batch.batchId === preview.batchId;
    });
  }

  function statementLabel(name) {
    if (name === "bb-extrato-sintetico.csv") return "Exemplo sintético";
    if (name === "bb-extrato-sintetico-sobreposicao.csv") return "Exemplo com período sobreposto";
    if (name === "bb-extrato-sintetico-terceira.csv") return "Terceira carga de ensaio";
    return "Exemplo sintético";
  }

  async function loadStatement(name) {
    state.importNotice = "";
    state.importReading = true;
    state.importOrigin = "exemplo-sintetico";
    state.importFileName = statementLabel(name);
    render();
    const response = await fetch("fixtures/" + name);
    if (!response.ok) {
      state.importReading = false;
      state.importNotice = "O exemplo sintético não pôde ser lido.";
      render();
      return;
    }
    const parsed = IsaStatement.readStatement(new Uint8Array(await response.arrayBuffer()));
    state.importReading = false;
    state.importPreview = parsed;
    ensureAccount();
    if (window.isaPublic && parsed && parsed.ok) api("PUT", "/api/drafts/import", parsed);
    persist();
    render();
  }

  function chosenAccount() {
    const accounts = ensureAccount();
    const name = String(state.importNewName || "").trim();
    if (name) {
      return { id: "conta-" + Date.now().toString(36), ownerId: state.personId, name: name, currency: "BRL", declared: true, fresh: true };
    }
    return accounts.find(function (account) { return account.id === state.importAccountId; }) || accounts[0];
  }

  function pendingCount() {
    return (state.occurrences || []).filter(function (item) {
      return item.ownerId === state.personId && item.state === "pendente";
    }).length;
  }

  function statementSource() {
    return state.importOrigin === "arquivo-teste" ? "arquivo-teste" : "exemplo-sintetico";
  }

  function occurrenceFrom(row, account, preview, occurrenceState) {
    return {
      id: "occ-" + Math.random().toString(36).slice(2, 10),
      ownerId: state.personId,
      accountId: account.id,
      batchId: preview.batchId,
      signature: IsaStatement.lineSignature(row),
      date: row.date,
      history: row.history,
      cents: row.cents,
      class: row.class,
      family: row.family || "",
      document: row.document || "",
      source: statementSource(),
      simulated: statementSource() === "exemplo-sintetico",
      state: occurrenceState,
      movementId: "",
      decided: false,
    };
  }

  function entryFromOccurrence(item) {
    return {
      id: "ext-" + Math.random().toString(36).slice(2, 10),
      ownerId: item.ownerId,
      accountId: item.accountId,
      occurrenceId: item.id,
      lineSignature: item.signature,
      direction: item.class === "entrada" ? "ganho" : "gasto",
      nature: item.family === "bb_rende_facil" ? "bb_rende_facil" : "a_conferir",
      merchant: item.history,
      noteDate: item.date,
      dueDate: "",
      statusDate: item.date,
      amountMinor: Math.abs(item.cents),
      currency: "BRL",
      category: "",
      categorizationStatus: "a_categorizar",
      status: item.class === "entrada" ? "recebido" : "pago",
      source: item.source,
      simulated: !!item.simulated,
      documentId: "",
      bankDocument: item.document,
      fingerprint: "",
      imageLabel: "",
      archived: false,
      updatedAt: new Date().toISOString(),
    };
  }

  function serverConfirmImport(preview, account) {
    state.importNotice = "Salvando";
    render();
    const movements = preview.movements.map(function (row) {
      return {
        signature: IsaStatement.lineSignature(row),
        date: row.date,
        cents: row.cents,
        direction: row.class,
        label: row.history,
        history: row.history,
        document: row.document || "",
        nature: row.family === "bb_rende_facil" ? "bb_rende_facil" : "a_conferir",
      };
    });
    const notes = (preview.balances || []).map(function (row) {
      return {
        signature: IsaStatement.lineSignature(row),
        date: row.date,
        cents: row.cents,
        class: row.class,
      };
    });
    api("POST", "/api/imports", {
      batchKey: preview.batchId,
      origin: statementSource(),
      account: { id: account.fresh ? "" : account.id, name: account.name, currency: "BRL" },
      movements: movements,
      notes: notes,
    }).then(function (result) {
      state.importSaving = false;
      if (!result.ok || !result.data.workspace) {
        state.importNotice = (result.data && result.data.error) || "Não foi possível salvar. Nada entrou.";
        render();
        return;
      }
      applyWorkspace(result.data.workspace);
      state.importPreview = null;
      state.importNewName = "";
      api("PUT", "/api/drafts/import", { cleared: true });
      if (result.data.repeated) {
        state.notice = "Este arquivo já foi lido nesta conta. Nenhuma ocorrência nova foi criada.";
        persist();
        go("#lancamentos");
        return;
      }
      const dates = preview.movements.map(function (row) { return row.date; }).sort();
      if (dates.length) state.month = dates[0].slice(0, 7);
      const span = dates.length ? "Movimentações importadas de " + showDate(dates[0]) + " a " + showDate(dates[dates.length - 1]) + ". " : "";
      state.notice = span + "Entraram " + (result.data.imported || 0) + ". Ficaram " + (result.data.pending || 0) + " para conferir. A categoria não foi exigida.";
      persist();
      go((result.data.imported || 0) ? "#lancamentos" : "#pendencias");
    }).catch(function () {
      state.importSaving = false;
      state.importNotice = "Não foi possível salvar. Nada entrou.";
      render();
    });
  }

  function confirmImport() {
    const preview = state.importPreview;
    if (!preview || !preview.ok || !preview.chain.ok || state.importSaving) return;
    state.importSaving = true;
    const account = chosenAccount();
    if (!account || account.currency !== "BRL") {
      state.importSaving = false;
      state.importNotice = "Esta leitura só entra numa conta em Real.";
      render();
      return;
    }
    if (account.fresh) {
      delete account.fresh;
      state.accounts.push(account);
      state.importAccountId = account.id;
      state.importNewName = "";
    }
    const elsewhere = (state.batches || []).find(function (batch) {
      return batch.ownerId === state.personId && batch.batchId === preview.batchId && batch.accountId !== account.id;
    });
    if (elsewhere) {
      state.importSaving = false;
      state.importNotice = "Este arquivo já está em outra conta. Um nome novo não muda esse vínculo.";
      persist();
      render();
      return;
    }
    if (sameBatch(account.id, preview)) {
      state.importSaving = false;
      state.importNotice = "Este arquivo já foi lido nesta conta. As pendências anteriores continuam. Nenhuma ocorrência nova foi criada.";
      persist();
      render();
      return;
    }
    if (window.isaPublic) {
      serverConfirmImport(preview, account);
      return;
    }
    if (!state.occurrences) state.occurrences = [];
    const stored = state.occurrences.filter(function (item) {
      return item.ownerId === state.personId && item.accountId === account.id;
    });
    const plan = IsaStatement.planOccurrences(stored, preview.movements);
    plan.importRows.forEach(function (row) {
      const occurrence = occurrenceFrom(row, account, preview, "incorporada");
      const entry = entryFromOccurrence(occurrence);
      occurrence.movementId = entry.id;
      state.occurrences.push(occurrence);
      state.entries.push(entry);
    });
    plan.pendingRows.forEach(function (row) {
      state.occurrences.push(occurrenceFrom(row, account, preview, "pendente"));
    });
    const known = {};
    (state.statementNotes || []).forEach(function (note) {
      if (note.ownerId === state.personId && note.accountId === account.id) known[note.signature] = true;
    });
    preview.balances.forEach(function (row) {
      const signature = IsaStatement.lineSignature(row);
      if (known[signature]) return;
      state.statementNotes.push({
        ownerId: state.personId,
        accountId: account.id,
        date: row.date,
        cents: row.cents,
        class: row.class,
        signature: signature,
      });
    });
    state.batches.push({
      ownerId: state.personId,
      accountId: account.id,
      batchId: preview.batchId,
      imported: plan.importRows.length,
      pending: plan.pendingRows.length,
    });
    const dates = preview.movements.map(function (row) { return row.date; }).sort();
    if (plan.importRows.length) state.month = plan.importRows.map(function (row) { return row.date; }).sort()[0].slice(0, 7);
    state.importSaving = false;
    state.importPreview = null;
    state.filters = { q: "", direction: "", category: "", status: "", archived: false, mode: "", consumption: false };
    const span = dates.length ? "Movimentações importadas de " + showDate(dates[0]) + " a " + showDate(dates[dates.length - 1]) + ". " : "";
    state.notice = span + "Entraram " + plan.importRows.length + ". Ficaram " + plan.pendingRows.length + " para conferir. A categoria não foi exigida.";
    persist();
    go(plan.importRows.length ? "#lancamentos" : "#pendencias");
  }

  function decidePending(occurrenceId, kind) {
    if (window.isaPublic) {
      api("POST", "/api/occurrences/" + occurrenceId + "/decide", { kind: kind }).then(function (result) {
        if (!result.ok || !result.data.workspace) {
          state.notice = (result.data && result.data.error) || "Não foi possível salvar a decisão.";
          render();
          return;
        }
        applyWorkspace(result.data.workspace);
        state.notice = result.data.repeated
          ? "Essa decisão já foi registrada. Nenhum movimento novo foi criado."
          : (kind === "mesma" ? "Registrado como a mesma operação. Nada entrou de novo." : "Esta operação entrou como nova. Repetir não cria outra.");
        persist();
        render();
      }).catch(function () {
        state.notice = "Não foi possível salvar a decisão.";
        render();
      });
      return;
    }
    const item = (state.occurrences || []).find(function (row) {
      return row.id === occurrenceId && row.ownerId === state.personId;
    });
    if (!item || item.state !== "pendente") {
      state.notice = "Essa decisão já foi registrada. Nenhum movimento novo foi criado.";
      persist();
      render();
      return;
    }
    if (kind === "mesma") {
      item.state = "mesma";
      item.decided = true;
      state.notice = "Registrado como a mesma operação. Nada entrou de novo.";
    } else {
      const entry = entryFromOccurrence(item);
      item.state = "incorporada";
      item.movementId = entry.id;
      item.decided = true;
      state.entries.push(entry);
      state.notice = "Esta operação entrou como nova. Repetir não cria outra.";
    }
    persist();
    render();
  }

  function shortNote(row) {
    if (row.family === "bb_rende_facil") return "Movimentação BB Rende Fácil. O histórico não diz se é aplicação ou rendimento.";
    if (row.meio === "pix") return "Pix. Sem categoria.";
    if (row.meio === "transferencia") return "Transferência. Sem categoria.";
    if (row.meio === "cartao") return "Cartão. Sem categoria.";
    return "";
  }

  function viewImport() {
    const accounts = ensureAccount();
    const preview = state.importPreview;
    if (state.importReading) return shell("Lendo extrato", "<p>Lendo extrato.</p>");
    if (!preview) {
      return shell(
        "Importar extrato",
        (window.isaPublic
          ? '<p>Escolha o arquivo. A prévia não grava sozinha, e o banco não passa a atualizar este extrato depois.</p>'
          : '<p>Use o exemplo inventado ou um arquivo de teste. Ler não grava.</p>') +
        (window.isaPublic ? "" : '<p class="note">Use somente dados fictícios nesta demonstração.</p>') +
        '<div class="stack"><label class="choice">Escolher extrato CSV<input id="statement-file" type="file" accept=".csv,text/csv"></label>' +
        (window.isaPublic ? "" : '<button type="button" class="primary" id="load-synthetic">Usar o exemplo sintético</button>') + "</div>"
      );
    }
    if (!preview.ok) {
      return shell(
        "Importar extrato",
        '<p class="note">Não consegui ler este arquivo. Escolha outro extrato.</p>' +
        '<div class="stack"><label class="choice">Escolher outro extrato<input id="statement-file" type="file" accept=".csv,text/csv"></label>' +
        (window.isaPublic ? "" : '<button type="button" class="secondary" id="load-synthetic">Usar o exemplo sintético</button>') + "</div>"
      );
    }
    const accountId = state.importAccountId || accounts[0].id;
    const repeated = sameBatch(accountId, preview);
    const stored = (state.occurrences || []).filter(function (item) {
      return item.ownerId === state.personId && item.accountId === accountId;
    });
    const plan = IsaStatement.planOccurrences(stored, preview.movements);
    const dates = preview.movements.map(function (row) { return row.date; }).sort();
    const finalBalance = preview.balances.filter(function (row) { return row.class === "saldo_informado"; }).slice(-1)[0]
      || preview.balances.filter(function (row) { return row.class === "saldo_do_dia"; }).slice(-1)[0];
    const balanceLabel = { saldo_anterior: "Saldo anterior informado", saldo_do_dia: "Saldo informado no extrato", saldo_informado: "Saldo informado no extrato" };
    const count = repeated ? 0 : plan.importRows.length;
    const conferir = repeated ? pendingCount() : plan.pendingRows.length + plan.reused;
    const already = repeated
      ? ((state.batches || []).find(function (batch) { return batch.ownerId === state.personId && batch.accountId === accountId && batch.batchId === preview.batchId; }) || {}).imported || 0
      : Math.max(0, preview.movements.length - count - conferir);
    return shell(
      "Conferir o extrato",
      (state.importNotice ? '<p class="oknote">' + esc(state.importNotice) + "</p>" : "") +
      '<div class="import-layout"><div class="decision">' +
      "<p><strong>" + esc(state.importFileName || "Extrato") + "</strong></p>" +
      (dates.length ? "<p>Encontrado de " + showDate(dates[0]) + " a " + showDate(dates[dates.length - 1]) + ".</p>" : "") +
      '<form id="import-form" class="stack"><fieldset class="account-pick"><legend>Em qual conta você quer importar este extrato?</legend>' +
      accounts.map(function (account) {
        return '<label><input type="radio" name="conta" value="' + esc(account.id) + '"' + (account.id === accountId ? " checked" : "") + "> " + esc(account.name) + " · Real</label>";
      }).join("") +
      '<label class="stack-field">Ou crie um nome<input id="import-name" name="import-name" type="text" value="' + esc(state.importNewName) + '" placeholder="Nome da conta"></label>' +
      "</fieldset>" +
      '<p class="muted">O vínculo é o que você declarar. O banco não foi consultado.</p>' +
      '<div class="counts"><div><small>Novas</small><strong id="count-new">' + count + '</strong></div><div><small>Já importadas</small><strong>' + already + '</strong></div><div><small>A conferir</small><strong>' + conferir + "</strong></div></div>" +
      (conferir && !repeated ? '<p class="muted">A correspondência é candidata. Ela fica para conferir e não entra agora.</p>' : "") +
      (repeated ? '<p class="note">Este arquivo já foi lido nesta conta. Nenhuma ocorrência nova foi criada.</p><button class="secondary" type="button" id="open-pending">Abrir pendências</button>' : "") +
      (!preview.chain.ok ? '<p class="note">Não consegui conferir os saldos deste arquivo. Nada será gravado.</p>' : "") +
      (preview.chain.ok && !repeated ? '<button class="primary" type="submit" id="import-go">Importar ' + count + (count === 1 ? " movimentação" : " movimentações") + "</button>" : "") +
      "</form></div><div class=\"consult\">" +
      '<details class="fold"><summary>Detalhes da leitura</summary><p class="muted">Codificação ' + esc(preview.encoding) + ". O arquivo não informa a moeda. A conta de destino está em Real." +
      (preview.chain.ok ? " As observações de saldo fecham com as movimentações." : "") + "</p></details>" +
      '<details class="fold"><summary>Saldos do extrato</summary>' +
      (finalBalance ? "<p>Saldo informado no extrato em " + showDate(finalBalance.date) + ": " + brl(finalBalance.cents) + ".</p>" : "") +
      preview.balances.map(function (row) {
        return '<div class="item"><strong>' + balanceLabel[row.class] + "</strong><span>" + showDate(row.date) + " · " + brl(row.cents) + "</span></div>";
      }).join("") +
      '<p class="muted">O rótulo não prova saldo disponível, investimento ou limite.</p></details>' +
      '<details class="fold"><summary>Consultar ' + preview.counts.movements + " movimentações</summary>" +
      preview.movements.map(function (row) {
        const note = shortNote(row);
        return '<div class="item"><span class="tag' + (row.class === "entrada" ? " ganho" : "") + '">' + (row.class === "entrada" ? "Entrada" : "Saída") +
          '</span><strong>' + esc(row.history) + "</strong><span>" + showDate(row.date) + " · " + brl(row.cents) + "</span>" +
          (note ? '<span class="meta">' + esc(note) + "</span>" : "") + "</div>";
      }).join("") +
      "</details>" +
      (window.isaPublic ? "" : '<div class="demo-box"><p><strong>Demonstração</strong></p><p class="muted">Estes botões repetem exemplos inventados. Não fazem parte da importação de um arquivo seu.</p>' +
      '<button class="secondary" type="button" id="load-synthetic">Ler o mesmo exemplo de novo</button>' +
      '<button class="secondary" type="button" id="load-overlap">Ler outro exemplo, com período sobreposto</button>' +
      '<button class="secondary" type="button" id="load-third">Ler uma terceira carga de ensaio</button>' +
      "</div>") + "</div></div>"
    );
  }

  function viewPending() {
    const rows = (state.occurrences || []).filter(function (item) { return item.ownerId === state.personId; });
    const cards = rows.filter(function (item) { return item.state === "pendente" || item.decided; }).map(function (sample) {
      const existing = rows.filter(function (item) {
        return item.accountId === sample.accountId && item.signature === sample.signature && item.state === "incorporada" && item.id !== sample.id;
      });
      const word = sample.class === "entrada" ? "Entrada" : "Saída";
      const open = sample.state === "pendente";
      return '<div class="item"><span class="tag' + (sample.class === "entrada" ? " ganho" : "") + '">' + word + "</span><strong>" + esc(sample.history) + "</strong><span>Recebido: " +
        showDate(sample.date) + " · " + brl(sample.cents) + "</span>" +
        "<span>Na conta: " + (existing.length ? existing.length + " já incorporada" + (existing.length === 1 ? "" : "s") + ", " + esc(existing[0].history) : "nenhuma com esta correspondência") + "</span>" +
        (open
          ? '<div class="split"><button type="button" class="secondary" data-decide="mesma" data-occ="' + esc(sample.id) + '">É a mesma operação</button><button type="button" class="primary" data-decide="outra" data-occ="' + esc(sample.id) + '">É outra operação</button></div>'
          : '<p class="muted">Decisão já registrada. ' + (sample.state === "mesma" ? "Nada entrou de novo." : "A quantidade reconhecida como nova já entrou.") + "</p>" +
            '<button type="button" class="quiet" data-decide="mesma" data-occ="' + esc(sample.id) + '">Repetir a decisão</button>') +
        "</div>";
    }).join("");
    return shell(
      "O que falta conferir",
      (state.notice ? '<p class="oknote">' + esc(state.notice) + "</p>" : "") +
      "<p>Cada linha abaixo é uma correspondência, não uma certeza. Só entra o que você marcar como outra operação.</p>" +
      (cards || '<p class="muted">Não há pendência nesta conta.</p>')
    );
  }

  function moneyName(account) {
    if (!account) return "BRL · Real";
    return (account.currency || "BRL") + " · " + (account.currencyName || "Real");
  }

  function maskNumber(value) {
    const text = String(value || "").trim();
    if (!text) return "Número ainda não informado";
    const visible = text.length > 2 ? text.slice(-2) : text;
    return "•".repeat(Math.max(0, text.length - visible.length)) + visible;
  }

  function accountRoute(route) {
    const tail = String(route || "").replace(/^#contas\/?/, "");
    if (!tail) return { kind: "list" };
    if (tail === "nova") return { kind: "form", id: "" };
    const parts = tail.split("/");
    if (parts[1] === "editar") return { kind: "form", id: parts[0] };
    return { kind: "detail", id: parts[0] };
  }

  function viewAccounts(route) {
    const parsed = accountRoute(route);
    if (parsed.kind === "form") {
      const current = (state.accounts || []).find(function (item) { return item.id === parsed.id; }) || {};
      if (parsed.id && !current.id) {
        return shell("Conta", '<p class="notice error" role="alert">Essa conta não está disponível. Volte para a lista e escolha outra.</p><p><a class="primary" href="#contas">Ver suas contas</a></p>');
      }
      return accountForm(current);
    }
    if (parsed.kind === "detail") {
      const current = (state.accounts || []).find(function (item) { return item.id === parsed.id; });
      if (!current) return shell("Conta", '<p class="notice error" role="alert">Essa conta não está disponível. Volte para a lista e escolha outra.</p><p><a class="primary" href="#contas">Ver suas contas</a></p>');
      return accountDetail(current);
    }
    return accountList();
  }

  function accountList() {
    const accounts = state.accounts || [];
    const currencies = [];
    accounts.forEach(function (item) {
      if (currencies.indexOf(item.currency) < 0) currencies.push(item.currency);
    });
    const viewing = window.isaAccountContext && window.isaAccountContext !== "all";
    const rows = accounts.map(function (item) {
      const balance = item.balance
        ? moneyText(item.balance.cents, item.currency) + " em " + showDate(item.balance.asOf) + ". " + (item.balance.meaning || "Valor informado.")
        : "Saldo não informado";
      return '<article class="accountrow"' + (state.savedAccountId === item.id ? ' data-saved="true"' : "") + ">" +
        '<div class="grow"><h3>' + esc(item.name) + "</h3>" +
        (item.nickname ? '<p class="meta">' + esc(item.institution || "Banco não informado") + " · " + esc(item.numberMasked || "Número não informado") + "</p>" : "") +
        '<div class="tags"><span class="pill">' + esc(item.kindLabel || "Tipo não informado") + "</span><span class=\"pill\">" + esc(item.currency || "") + "</span><span class=\"pill\">" + esc(item.intakeLabel || "Lançamento manual") + "</span>" +
        (item.contactCount ? '<span class="pill">' + item.contactCount + (item.contactCount === 1 ? " contato" : " contatos") + "</span>" : "") +
        "</div><p class=\"meta\">" + esc(balance) + "</p>" +
        (item.status === "inactive" ? '<p class="meta">Conta inativa. O histórico permanece.</p>' : "") +
        '</div><div class="action"><a class="textbtn" href="#contas/' + esc(item.id) + '">Abrir conta</a></div></article>';
    }).join("");
    const side = '<aside class="panel rail"><div class="pad"><p class="eyebrow">Nesta lista</p><p><strong>' + accounts.length + "</strong> " + (accounts.length === 1 ? "conta" : "contas") + "</p><p>Moedas: " + esc(currencies.join(", ") || "nenhuma ainda") + ".</p>" +
      (currencies.length > 1 ? "<p>Valores de moedas diferentes ficam separados. Não há um total convertido.</p>" : "") +
      "<p>Para trazer movimentos, abra a conta e importe um arquivo. A conexão automática com o banco ainda não está disponível.</p></div></aside>";
    const body = (state.notice ? '<div class="notice success" role="status">' + esc(state.notice) + "</div>" : "") +
      (viewing ? '<p class="meta">A lista mostra todas as contas cadastradas. Início, lançamentos e planejamento seguem a conta escolhida em Visualizando.</p>' : "") +
      '<div class="accounts-layout"><section class="panel"><div class="listhead"><h2>Contas cadastradas</h2><span class="pill">' + accounts.length + (accounts.length === 1 ? " conta" : " contas") + "</span></div>" +
      (accounts.length ? rows : '<div class="pad"><h2>Adicione sua primeira conta</h2><p>Banco, número da conta e tipo bastam para começar.</p><p><a class="btn primary" href="#contas/nova">Adicionar conta</a></p></div>') +
      "</section>" + (accounts.length ? side : "") + "</div>";
    return shell("Suas contas", '<p class="lede">Bancos, poupanças e investimentos em um só lugar.</p><p class="page-action"><a class="btn primary" href="#contas/nova" id="add-account">Adicionar conta</a></p>' + body);
  }

  function accountDetail(account) {
    const tab = state.accountTab === "dados" ? "dados" : "acesso";
    const balance = account.balance
      ? moneyText(account.balance.cents, account.currency) + " em " + showDate(account.balance.asOf) + ". " + account.balance.meaning
      : "Saldo não informado";
    const contacts = (account.contacts || []).map(function (item) {
      return "<li><strong>" + esc(item.name || "Contato sem nome") + "</strong> · " + esc(item.roleLabel || "Contato") +
        (item.email ? "<br>E-mail: " + esc(item.email) : "") +
        (item.phone ? "<br>Telefone: " + esc(item.phone) + (item.extension ? " ramal " + esc(item.extension) : "") : "") +
        "<br>" + esc(item.scopeLabel || "") + (item.primary ? " · Principal" : "") + "</li>";
    }).join("");
    const access = '<section class="pad"><h2>Acesso automático</h2><p>' + esc((account.connection && account.connection.message) || "Não há integração automática com este banco.") + "</p><p class=\"meta\">Nenhum serviço de conexão está habilitado. A ISA não pede senha do banco.</p></section>" +
      '<section class="pad split-block"><h2>Importação por arquivo</h2><p>' + esc(account.reader) + "</p>" +
      (account.lastImport ? "<p>Última importação: " + esc(showDate(String(account.lastImport).slice(0, 10))) + ".</p>" : "<p>Ainda não há importação nesta conta.</p>") +
      '<button type="button" class="btn primary" id="import-this">Importar extrato</button></section>';
    const data = '<section class="pad"><h2>Dados da conta</h2><dl class="facts"><div><dt>Banco</dt><dd>' + esc(account.institution || "Não informado") + "</dd></div><div><dt>Número</dt><dd>" + esc(account.accountNumber || "Não informado") + "</dd></div><div><dt>Tipo</dt><dd>" + esc(account.kindLabel) + "</dd></div><div><dt>Moeda</dt><dd>" + esc(moneyName(account)) + "</dd></div><div><dt>Saldo</dt><dd>" + esc(balance) + "</dd></div></dl>" +
      (account.bankEmail ? "<p>E-mail do banco: " + esc(account.bankEmail) + ". Este endereço foi informado por você e não foi verificado.</p>" : "") +
      (contacts ? "<h2>Contatos</h2><ul class=\"contact-list\">" + contacts + "</ul>" : "<p>Nenhum contato cadastrado.</p>") +
      '<p><a class="btn secondary" href="#contas/' + esc(account.id) + '/editar">Editar dados</a></p></section>';
    return shell(
      account.name,
      '<p class="lede">' + esc(account.institution || "Banco não informado") + " · " + esc(account.numberMasked || "Número não informado") + " · " + esc(account.currency || "") + '</p><p><a class="btn secondary" href="#contas/' + esc(account.id) + '/editar">Editar dados</a></p>' +
      '<div class="tabs" role="tablist"><button type="button" class="tab' + (tab === "acesso" ? " is-current" : "") + '" id="tab-acesso" role="tab" aria-selected="' + (tab === "acesso") + '">Acesso e importação</button><button type="button" class="tab' + (tab === "dados" ? " is-current" : "") + '" id="tab-dados" role="tab" aria-selected="' + (tab === "dados") + '">Dados e contatos</button></div>' +
      '<div class="panel">' + (tab === "acesso" ? access : data) + "</div>"
    );
  }

  function fieldBox(id, label, value, placeholder, extra) {
    return '<label class="field' + (extra || "") + '">' + label + '<input id="' + id + '" name="' + id + '" type="text" autocomplete="off" value="' + esc(value || "") + '"' + (placeholder ? ' placeholder="' + esc(placeholder) + '"' : "") + "></label>";
  }

  function accountForm(account) {
    const creating = !account.id;
    if (creating && !state.accountDraftId) state.accountDraftId = "conta-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    if (state.formBuffer && state.formBuffer.id === (account.id || state.accountDraftId)) account = Object.assign({}, account, state.formBuffer);
    const draftId = creating ? state.accountDraftId : account.id;
    const currencies = [["BRL", "Real"], ["USD", "Dólar americano"], ["EUR", "Euro"]];
    const currency = account.currency || "BRL";
    const banks = state.banks || [];
    const contacts = account.contacts || [];
    const contactBox = function (item, index) {
      const role = item.role || "";
      return '<fieldset class="contact-card" data-contact="' + index + '" data-id="' + esc(item.id || "") + '"><legend>Contato ' + (index + 1) + '</legend>' +
        fieldBox("contact-name-" + index, "Nome", item.name, "Nome da pessoa") +
        '<label class="field">Função<select id="contact-role-' + index + '"><option value="">Escolha, se quiser</option>' +
        [["gerente_conta", "Gerente da conta"], ["gerente_agencia", "Gerente da agência"], ["atendimento", "Atendimento"], ["outro", "Outro"]].map(function (pair) {
          return '<option value="' + pair[0] + '"' + (role === pair[0] ? " selected" : "") + ">" + pair[1] + "</option>";
        }).join("") + "</select></label>" +
        fieldBox("contact-role-note-" + index, "Descrição da função", item.roleNote, "Só se escolher Outro") +
        fieldBox("contact-email-" + index, "E-mail", item.email, "nome@banco.exemplo") +
        fieldBox("contact-phone-" + index, "Telefone", item.phone, "") +
        fieldBox("contact-extension-" + index, "Ramal", item.extension, "") +
        '<label class="field">Atende<select id="contact-scope-' + index + '">' +
        [["conta", "Esta conta"], ["agencia", "A agência"], ["instituicao", "A instituição"]].map(function (pair) {
          return '<option value="' + pair[0] + '"' + ((item.scope || "conta") === pair[0] ? " selected" : "") + ">" + pair[1] + "</option>";
        }).join("") + "</select></label>" +
        '<label class="checkline"><input id="contact-primary-' + index + '" type="checkbox"' + (item.primary ? " checked" : "") + "> Contato principal</label>" +
        '<button type="button" class="btn quiet remove-contact" data-remove="' + index + '">Remover deste formulário</button></fieldset>';
    };
    const form = '<form id="account-form" class="panel" novalidate data-draft="' + esc(draftId) + '"><div class="pad"><div class="sectiontop"><div><h2>Dados da conta</h2><p class="small">Só estes três campos são obrigatórios.</p></div><span class="pill">Cadastro</span></div>' +
      '<div id="saveerror" class="notice error" role="alert" hidden></div><div class="fieldgrid">' +
      fieldBox("acc-institution", "Banco ou instituição", account.institution, "Ex.: Banco do Brasil", " full") +
      '<datalist id="bank-list">' + banks.map(function (item) { return '<option value="' + esc(item.name) + '"></option>'; }).join("") + "</datalist>" +
      fieldBox("acc-number", "Número da conta", account.accountNumber, "Ex.: 0012345-6") +
      '<label class="field">Tipo de conta<select id="acc-kind"><option value="">Escolha o tipo</option><option value="corrente"' + (account.kind === "corrente" ? " selected" : "") + '>Conta corrente</option><option value="poupanca"' + (account.kind === "poupanca" ? " selected" : "") + '>Poupança</option><option value="investimento"' + (account.kind === "investimento" ? " selected" : "") + ">Investimento</option></select></label></div>" +
      '<div class="currencyline"><span>Moeda</span><strong id="currencylabel">' + esc(moneyName(Object.assign({ currency: currency }, account))) + '</strong><button type="button" class="btn quiet" id="change-currency"' + (account.currencyLocked ? " hidden" : "") + ">Alterar</button></div>" +
      (account.currencyLocked ? '<p class="meta">Esta conta já tem movimentação. A moeda permanece ' + esc(moneyName(account)) + ".</p>" : "") +
      '<div id="currency-panel"' + (state.showCurrency ? "" : " hidden") + '><label class="field">Moeda<select id="acc-currency">' + currencies.map(function (item) {
        return '<option value="' + item[0] + '"' + (item[0] === currency ? " selected" : "") + ">" + item[0] + " · " + item[1] + "</option>";
      }).join("") + "</select></label></div>" +
      '<details class="more"' + (state.openAccountMore ? " open" : "") + '><summary>Mais informações</summary><div class="fieldgrid">' +
      fieldBox("acc-nickname", "Apelido", account.nickname, "Opcional") +
      fieldBox("acc-country", "País", account.country, "Opcional") +
      fieldBox("acc-bank-code", "Código do banco", account.bankCode, "Opcional") +
      fieldBox("acc-agency", "Agência", account.agency, "Opcional") +
      fieldBox("acc-digit", "Dígito", account.accountDigit, "Opcional") +
      '</div><div id="liquid-wrap"' + (account.kind === "investimento" ? "" : " hidden") + '><label class="checkline"><input id="acc-liquid" type="checkbox"' + (account.kind === "investimento" && account.liquid ? " checked" : "") + "> Este investimento pode ser usado para pagar compromissos</label><p class=\"meta\">Sem esta marca, o valor fica fora da margem disponível. Ele não vira renda.</p></div>" +
      (account.id ? '<label class="checkline"><input id="acc-inactive" type="checkbox"' + (account.status === "inactive" ? " checked" : "") + "> Inativar, preservando o histórico</label>" : "") +
      "</details>" +
      '<details class="more" id="contact-section"' + (state.openContacts ? " open" : "") + '><summary>Contatos do banco</summary><p class="meta">Opcionais. A ISA não envia mensagem, não verifica o endereço e não usa estes dados na leitura.</p>' +
      fieldBox("acc-bank-email", "E-mail institucional do banco", account.bankEmail, "Opcional") +
      fieldBox("acc-agency-email", "E-mail da agência", account.agencyEmail, "Opcional") +
      fieldBox("acc-agency-phone", "Telefone de atendimento", account.agencyPhone, "Opcional") +
      '<div id="contact-list">' + contacts.map(contactBox).join("") + '</div><button type="button" class="btn secondary" id="add-contact">Adicionar contato</button></details>' +
      '<div class="form-actions"><button class="btn primary" type="submit" id="account-save">Salvar conta</button><button class="btn secondary" type="button" id="account-cancel">Cancelar</button></div></div></form>';
    const rail = '<aside class="panel rail"><div class="pad"><p class="eyebrow">Assim sua conta aparece</p><h2 id="previewname">' + esc(account.name || account.institution || "Sua nova conta") + '</h2><p id="previewnumber">' + esc(account.numberMasked || "Número ainda não informado") + '</p><dl class="facts"><div><dt>Tipo</dt><dd id="previewkind">' + esc(account.kindLabel || "A escolher") + '</dd></div><div><dt>Moeda</dt><dd id="previewcurrency">' + esc(moneyName(Object.assign({ currency: currency }, account))) + '</dd></div><div><dt>Saldo</dt><dd>Não informado</dd></div></dl><p class="meta">O saldo aparece depois que você o informar ou receber dados compatíveis do banco.</p><h2>Depois de salvar</h2><p>A conta fica na lista. Em seguida você pode importar um arquivo ou ver que a conexão automática ainda não está disponível.</p></div></aside>';
    return shell(
      creating ? "Adicionar conta" : "Editar conta",
      '<p class="lede">Comece pelo banco, número e tipo da conta.</p><p><a class="textbtn" href="#contas">Voltar às contas</a></p><div class="accounts-layout">' + form + rail + "</div>"
    );
  }

  function viewProfile() {
    const who = person();
    return shell(
      who.name ? who.name : "Seu perfil",
      '<p class="lede">Identidade, apresentação e acesso. As contas financeiras ficam em Contas.</p>' +
      '<form id="profile-form" class="panel"><div class="pad"><h2>Como você quer aparecer na ISA?</h2><p class="meta">Identidade de acesso: ' + esc(who.accessLabel || "Sessão individual deste piloto") + ".</p>" +
      '<label class="field">Nome de apresentação<input id="profile-name" name="profile-name" type="text" maxlength="80" autocomplete="name" value="' + esc(who.name || "") + '"></label>' +
      '<div class="form-actions"><button class="btn primary" type="submit" id="save-profile">Salvar nome</button></div><p id="profile-state" class="meta" role="status"></p></div></form>' +
      '<div class="stack"><button type="button" class="secondary" id="font">' + (state.font === "large" ? "Usar texto padrão" : "Aumentar o texto") + "</button>" +
      (window.isaPublic ? "" : '<button type="button" class="secondary" id="other">' + (who.id === PEOPLE.marina.id ? "Ver a demonstração de Paulo" : "Ver a demonstração de Marina") + "</button>") +
      (window.isaPublic ? "" : '<button type="button" class="secondary" id="wipe">Apagar os dados desta demonstração</button>') +
      "</div>" +
      (window.isaPublic
        ? "<h2>Um recado</h2><p>O recado não anexa extrato, lançamento nem captura.</p><label class=\"stack-field\">Assunto<input id=\"feedback-subject\" type=\"text\" maxlength=\"80\"></label><label class=\"stack-field\">Mensagem<textarea id=\"feedback-text\" maxlength=\"1000\" rows=\"4\"></textarea></label><button type=\"button\" class=\"secondary\" id=\"send-feedback\">Enviar recado</button><p id=\"feedback-state\" class=\"muted\"></p>"
        : "") +
      "<h2>Privacidade</h2><p>Os registros ficam separados por pessoa. A assistência usa Claude pela AWS só com os dados necessários. Sugestões e decisões ficam gravadas. A cópia guarda sete dias para recuperação; isso não apaga o cadastro. Quem opera a publicação pode precisar acessar a base para manter o serviço. Não há foto nem conexão automática com o banco.</p>"
    );
  }

  function bind() {
    const on = function (id, fn) {
      const node = document.getElementById(id);
      if (node) node.onclick = fn;
    };
    const switcher = document.getElementById("account-switch");
    if (switcher) switcher.onchange = function () {
      window.isaAccountContext = switcher.value || "all";
      api("POST", "/api/accounts/select", { context: window.isaAccountContext }).finally(function () { render(); });
    };
    on("brand-leave", function () { leavePerson(); });
    const accountFormNode = document.getElementById("account-form");
    if (accountFormNode) {
      accountFormNode.onsubmit = saveAccount;
      const bank = document.getElementById("acc-institution");
      if (bank) bank.setAttribute("list", "bank-list");
      accountFormNode.addEventListener("input", refreshPreview);
      accountFormNode.addEventListener("change", refreshPreview);
    }
    on("change-currency", function () {
      state.showCurrency = true;
      const panel = document.getElementById("currency-panel");
      if (panel) panel.hidden = false;
      const select = document.getElementById("acc-currency");
      if (select) select.focus();
    });
    on("add-contact", function () {
      state.formBuffer = collectAccount();
      state.formBuffer.contacts.push({ name: "", role: "", roleNote: "", email: "", phone: "", extension: "", scope: "conta", primary: false });
      state.openContacts = true;
      state.accountDirty = true;
      render();
    });
    document.querySelectorAll(".remove-contact").forEach(function (button) {
      button.onclick = function () {
        const index = Number(button.getAttribute("data-remove"));
        state.formBuffer = collectAccount();
        state.formBuffer.contacts.splice(index, 1);
        state.openContacts = true;
        state.accountDirty = true;
        render();
      };
    });
    on("account-cancel", function () {
      const back = state.accountReturn || "#contas";
      if (state.accountDirty && !window.confirm("Descartar o preenchimento desta conta?")) return;
      state.formBuffer = null;
      state.accountDraftId = "";
      state.accountDirty = false;
      state.accountReturn = "";
      go(back);
    });
    on("tab-acesso", function () { state.accountTab = "acesso"; render(); });
    on("tab-dados", function () { state.accountTab = "dados"; render(); });
    on("import-this", function () {
      const parsed = accountRoute(location.hash);
      state.importAccountId = parsed.id;
      go("#importar");
    });
    const kind = document.getElementById("acc-kind");
    if (kind) kind.addEventListener("change", function () {
      const wrap = document.getElementById("liquid-wrap");
      if (wrap) wrap.hidden = kind.value !== "investimento";
    });
    const profileForm = document.getElementById("profile-form");
    if (profileForm) profileForm.onsubmit = function (event) {
      event.preventDefault();
      const input = document.getElementById("profile-name");
      const note = document.getElementById("profile-state");
      const button = document.getElementById("save-profile");
      if (button) button.disabled = true;
      api("POST", "/api/profile", { displayName: input.value.trim() }).then(function (result) {
        if (!result.ok) {
          if (note) note.textContent = (result.data && result.data.error) || "Não conseguimos salvar agora. Seu preenchimento foi mantido. Tente novamente.";
          if (button) button.disabled = false;
          return;
        }
        if (result.data.workspace) applyWorkspace(result.data.workspace);
        else if (result.data.profile) state.profile = Object.assign({ ready: true }, result.data.profile);
        if (note) note.textContent = "Nome salvo.";
        render();
      }).catch(function () {
        if (note) note.textContent = "Não conseguimos salvar agora. Seu preenchimento foi mantido. Tente novamente.";
        if (button) button.disabled = false;
      });
    };
    on("enter-marina", function () { enter("marina"); });
    on("enter-paulo", function () { enter("paulo"); });
    on("enter-eveline", function () { enter("eveline"); });
    on("enter-public", function () {
      window.location.assign("/api/login/start");
    });
    on("recover-access", function () {
      window.location.assign("/api/login/recovery");
    });
    on("send-feedback", function () {
      var node = document.getElementById("feedback-state");
      var text = document.getElementById("feedback-text").value;
      if (node) node.textContent = "Salvando";
      fetch("/api/feedback", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      }).then(function (response) {
        return response.json().then(function (data) {
          if (node) node.textContent = response.ok ? "Recado guardado." : (data.error || "Não foi possível salvar. Tente de novo.");
        });
      }).catch(function () {
        if (node) node.textContent = "Não foi possível salvar. O texto continua nesta tela.";
      });
    });
    on("forgot", function () {
      state.recovery = "Nenhum e-mail foi enviado. Nesta demonstração, entre de novo como Marina Alves ou Paulo Nunes. Não há senha para recuperar.";
      render();
    });
    on("prev-month", function () { shiftMonth(-1); });
    on("next-month", function () { shiftMonth(1); });
    on("empty-add", function () { go("#registrar"); });
    on("pick-gasto", function () { state.draft = blankDraft("gasto"); go("#origem"); });
    on("pick-ganho", function () { state.draft = blankDraft("ganho"); go("#origem"); });
    on("do-photo", function () { openCamera(); });
    on("do-file", function () { document.getElementById("file").click(); });
    on("do-type", function () {
      const direction = state.draft ? state.draft.direction : "gasto";
      state.draft = blankDraft(direction, "digitado");
      go("#conferir");
    });
    on("sim-boa", function () { simulate("boa"); });
    on("sim-parcial", function () { simulate("parcial"); });
    on("sim-ilegivel", function () { simulate("ilegivel"); });
    on("sim-falha", function () { simulate("falha"); });
    on("sim-dup", function () { simulate("duplicata"); });
    on("retry-sim", function () { simulate("boa"); });
    on("back-origin", function () { go("#origem"); });
    on("cancel", function () { state.draft = null; state.notice = ""; go("#inicio"); });
    on("open-dup", function () { const id = state.draft && state.draft.duplicateOf; state.draft = null; openEntry(id); });
    on("keep-dup", function () { state.draft.allowDuplicate = true; state.draft.duplicateOf = ""; saveDraft(); });
    on("edit", function () { const id = location.hash.slice(9); editEntry(id); });
    on("ask-archive", function () { state.confirmArchive = location.hash.slice(9); render(); });
    on("no-archive", function () { state.confirmArchive = ""; render(); });
    on("do-archive", function () { const id = state.confirmArchive; state.confirmArchive = ""; archiveEntry(id, true); });
    on("restore", function () { archiveEntry(location.hash.slice(9), false); });
    on("back-list", function () { state.notice = ""; go("#lancamentos"); });
    on("font", function () { state.font = state.font === "large" ? "normal" : "large"; persist(); render(); });
    on("open-import", function () { state.importNotice = ""; go("#importar"); });
    on("load-synthetic", function () { loadStatement("bb-extrato-sintetico.csv"); });
    on("load-overlap", function () { loadStatement("bb-extrato-sintetico-sobreposicao.csv"); });
    on("load-third", function () { loadStatement("bb-extrato-sintetico-terceira.csv"); });
    on("open-pending", function () { state.notice = ""; go("#pendencias"); });
    on("classify-demo", function () {
      const entry = mine().find(function (item) { return item.id === location.hash.slice(9); });
      if (!entry || entry.userLocked) {
        state.notice = "Sua categoria permanece.";
        persist();
        render();
        return;
      }
      const next = Object.assign({}, entry, { categorizationStatus: "precisa_de_ajuda" });
      if (window.isaPublic) {
        api("POST", "/api/entries", { entry: next }).then(function (result) {
          if (!result.ok || !result.data.workspace) {
            state.notice = "Não foi possível salvar a categoria.";
            render();
            return;
          }
          applyWorkspace(result.data.workspace);
          state.notice = "A categoria não foi definida. O lançamento continua gravado.";
          persist();
          render();
        });
        return;
      }
      entry.categorizationStatus = "precisa_de_ajuda";
      state.notice = "A demonstração não definiu categoria. O lançamento continua gravado. Nenhuma IA foi consultada.";
      persist();
      render();
    });
    on("classify-fail", function () {
      state.notice = "A classificação demonstrativa não respondeu. A importação não foi refeita.";
      render();
    });
    on("link-same", function () {
      const entry = mine().find(function (item) { return item.id === location.hash.slice(9); });
      const other = entry && linkCandidate(entry);
      if (!(entry && other)) {
        render();
        return;
      }
      const left = Object.assign({}, entry, { linkId: other.id });
      const right = Object.assign({}, other, { linkId: entry.id });
      if (window.isaPublic) {
        api("POST", "/api/entries", { entry: left }).then(function (first) {
          if (!first.ok) throw new Error("vinculo");
          return api("POST", "/api/entries", { entry: right });
        }).then(function (second) {
          if (!second.ok || !second.data.workspace) throw new Error("vinculo");
          applyWorkspace(second.data.workspace);
          state.notice = "Vínculo confirmado. Os dois registros continuam. O mês conta uma vez.";
          persist();
          render();
        }).catch(function () {
          state.notice = "Não foi possível salvar o vínculo.";
          render();
        });
        return;
      }
      entry.linkId = other.id;
      other.linkId = entry.id;
      state.notice = "Vínculo confirmado. Os dois registros continuam. O mês conta uma vez.";
      persist();
      render();
    });
    on("unlink", function () {
      const entry = mine().find(function (item) { return item.id === location.hash.slice(9); });
      const other = entry && mine().find(function (item) { return item.id === entry.linkId; });
      if (window.isaPublic && entry) {
        const left = Object.assign({}, entry, { linkId: "" });
        api("POST", "/api/entries", { entry: left }).then(function (first) {
          if (!first.ok) throw new Error("desfazer");
          if (!other) return first;
          return api("POST", "/api/entries", { entry: Object.assign({}, other, { linkId: "" }) });
        }).then(function (result) {
          if (result && result.data && result.data.workspace) applyWorkspace(result.data.workspace);
          state.notice = "Vínculo desfeito. Os dois registros continuam.";
          persist();
          render();
        }).catch(function () {
          state.notice = "Não foi possível desfazer o vínculo.";
          render();
        });
        return;
      }
      if (entry) entry.linkId = "";
      if (other) other.linkId = "";
      state.notice = "Vínculo desfeito. Os dois registros continuam.";
      persist();
      render();
    });
    on("other", function () {
      state.personId = state.personId === PEOPLE.marina.id ? PEOPLE.paulo.id : PEOPLE.marina.id;
      window.isaLabPerson = state.personId === PEOPLE.paulo.id ? "paulo" : "marina";
      window.isaAccountContext = "";
      state.draft = null;
      state.importPreview = null;
      state.importAccountId = "";
      state.importNotice = "";
      persist();
      refreshAccounts(function () { go("#inicio"); });
    });
    on("wipe", function () {
      state.entries = state.entries.filter(function (entry) { return entry.ownerId !== state.personId; });
      state.batches = (state.batches || []).filter(function (batch) { return batch.ownerId !== state.personId; });
      state.occurrences = (state.occurrences || []).filter(function (item) { return item.ownerId !== state.personId; });
      state.statementNotes = (state.statementNotes || []).filter(function (note) { return note.ownerId !== state.personId; });
      state.importPreview = null;
      state.notice = "Os lançamentos desta pessoa foram apagados neste navegador.";
      persist();
      go("#inicio");
    });
    on("leave", function () { leavePerson(); });
    document.querySelectorAll("[data-status]").forEach(function (node) {
      node.onclick = function () {
        state.filters = { q: "", direction: "", category: "", status: node.getAttribute("data-status"), archived: false, mode: "", consumption: true };
        persist();
        go("#lancamentos");
      };
    });
    document.querySelectorAll("[data-mode]").forEach(function (node) {
      node.onclick = function () {
        state.filters = { q: "", direction: "", category: "", status: "", archived: false, mode: "resultado", consumption: true };
        persist();
        go("#lancamentos");
      };
    });
    document.querySelectorAll("[data-cat]").forEach(function (node) {
      node.onclick = function () {
        state.filters = { q: "", direction: "gasto", category: node.getAttribute("data-cat"), status: "pago", archived: false, mode: "", consumption: true };
        persist();
        go("#lancamentos");
      };
    });
    document.querySelectorAll("[data-id]").forEach(function (node) {
      node.onclick = function () { openEntry(node.getAttribute("data-id")); };
    });
    document.querySelectorAll("[data-decide]").forEach(function (node) {
      node.onclick = function (event) {
        event.preventDefault();
        decidePending(node.getAttribute("data-occ"), node.getAttribute("data-decide"));
      };
    });
    const file = document.getElementById("file");
    if (file) file.onchange = function () { onFile(file.files && file.files[0]); };
    const form = document.getElementById("review-form");
    if (form) form.onsubmit = function (event) { event.preventDefault(); saveDraft(); };
    const statementFile = document.getElementById("statement-file");
    if (statementFile) statementFile.onchange = function () {
      const file = statementFile.files && statementFile.files[0];
      statementFile.value = "";
      if (!file) return;
      state.importReading = true;
      state.importPreview = null;
      state.importOrigin = "arquivo-teste";
      state.importFileName = file.name;
      render();
      const reader = new FileReader();
      reader.onload = function () {
        const bytes = new Uint8Array(reader.result);
        state.importPreview = IsaStatement.readStatement(bytes);
        state.importReading = false;
        ensureAccount();
        render();
      };
      reader.onerror = function () {
        state.importReading = false;
        state.importPreview = { ok: false };
        render();
      };
      reader.readAsArrayBuffer(file);
    };
    const statusField = document.getElementById("status");
    if (statusField) statusField.onchange = function () {
      draftFromForm();
      render();
    };
    const importForm = document.getElementById("import-form");
    if (importForm) {
      importForm.onsubmit = function (event) {
        event.preventDefault();
        const selected = importForm.querySelector('input[name="conta"]:checked');
        if (selected) state.importAccountId = selected.value;
        const name = document.getElementById("import-name");
        state.importNewName = name ? name.value : "";
        confirmImport(false);
      };
    }
    ["q", "f-dir", "f-cat", "f-status", "f-arch"].forEach(function (id) {
      const node = document.getElementById(id);
      if (!node) return;
      if (id === "f-dir") node.value = state.filters.direction;
      if (id === "f-cat") node.value = state.filters.category;
      if (id === "f-status") node.value = state.filters.status;
      if (id === "f-arch") node.checked = !!state.filters.archived;
      node.oninput = node.onchange = function () {
        state.filters.q = document.getElementById("q").value;
        state.filters.direction = document.getElementById("f-dir").value;
        state.filters.category = document.getElementById("f-cat").value;
        state.filters.status = document.getElementById("f-status").value;
        state.filters.archived = document.getElementById("f-arch").checked;
        state.filters.mode = "";
        state.filters.consumption = false;
        persist();
        render();
        const again = document.getElementById(id);
        if (again) again.focus();
      };
    });
    document.querySelectorAll("input, select, textarea").forEach(function (node) {
      node.addEventListener("focus", function () {
        const dock = document.querySelector(".dock");
        const limit = dock ? dock.getBoundingClientRect().top : window.innerHeight;
        const rect = node.getBoundingClientRect();
        if (rect.bottom > limit - 12 || rect.top < 8) node.scrollIntoView({ block: "center" });
      });
    });
    const video = document.getElementById("cam");
    if (video && state.stream) video.srcObject = state.stream;
    if (location.hash === "#origem" && state.stream && !video) {
      const wrap = document.getElementById("video-wrap");
      if (wrap) {
        wrap.innerHTML = '<video id="cam" autoplay playsinline></video><div class="split"><button type="button" id="shoot">Usar esta foto</button><button type="button" id="retake">Repetir</button></div>';
        document.getElementById("cam").srcObject = state.stream;
        document.getElementById("shoot").onclick = captureFrame;
        document.getElementById("retake").onclick = openCamera;
      }
    } else if (location.hash === "#origem" && state.stream) {
      const wrap = document.getElementById("video-wrap");
      if (wrap && !document.getElementById("shoot")) {
        wrap.innerHTML = '<video id="cam" autoplay playsinline></video><div class="split"><button type="button" id="shoot">Usar esta foto</button><button type="button" id="retake">Repetir</button></div>';
        document.getElementById("cam").srcObject = state.stream;
        document.getElementById("shoot").onclick = captureFrame;
        document.getElementById("retake").onclick = openCamera;
      }
    }
  }

  function leavePerson() {
    stopCamera();
    window.isaAccountContext = "";
    state.draft = null;
    const finish = function (url) {
      clearMoney();
      persist();
      if (url) window.location.assign(url);
      else go("#entrar");
    };
    if (window.isaPublic) {
      api("POST", "/api/logout", {}).then(function (result) {
        finish(result.ok && result.data && result.data.logoutUrl);
      }).catch(function () { finish(); });
      return;
    }
    state.personId = "";
    finish();
  }

  function setFieldError(id, message) {
    const input = document.getElementById(id);
    if (!input) return;
    let error = document.getElementById(id + "-error");
    if (!message) {
      if (error) error.remove();
      input.removeAttribute("aria-invalid");
      input.removeAttribute("aria-describedby");
      return;
    }
    if (!error) {
      error = document.createElement("p");
      error.id = id + "-error";
      error.className = "field-error";
      input.parentNode.appendChild(error);
    }
    error.textContent = message;
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", error.id);
  }

  function emailOk(value) {
    return !value || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
  }

  function collectAccount() {
    const form = document.getElementById("account-form");
    const contacts = [];
    document.querySelectorAll("[data-contact]").forEach(function (node) {
      const index = node.getAttribute("data-contact");
      contacts.push({
        id: node.getAttribute("data-id") || "",
        name: document.getElementById("contact-name-" + index).value.trim(),
        role: document.getElementById("contact-role-" + index).value,
        roleNote: document.getElementById("contact-role-note-" + index).value.trim(),
        email: document.getElementById("contact-email-" + index).value.trim(),
        phone: document.getElementById("contact-phone-" + index).value.trim(),
        extension: document.getElementById("contact-extension-" + index).value.trim(),
        scope: document.getElementById("contact-scope-" + index).value,
        primary: document.getElementById("contact-primary-" + index).checked,
      });
    });
    const currency = document.getElementById("acc-currency");
    return {
      id: form ? form.getAttribute("data-draft") : "",
      institution: document.getElementById("acc-institution").value.trim(),
      accountNumber: document.getElementById("acc-number").value.trim(),
      kind: document.getElementById("acc-kind").value,
      currency: currency ? currency.value : "BRL",
      nickname: document.getElementById("acc-nickname").value.trim(),
      country: document.getElementById("acc-country").value.trim(),
      bankCode: document.getElementById("acc-bank-code").value.trim(),
      agency: document.getElementById("acc-agency").value.trim(),
      accountDigit: document.getElementById("acc-digit").value.trim(),
      bankEmail: document.getElementById("acc-bank-email").value.trim(),
      agencyEmail: document.getElementById("acc-agency-email").value.trim(),
      agencyPhone: document.getElementById("acc-agency-phone").value.trim(),
      liquid: !!(document.getElementById("acc-liquid") && document.getElementById("acc-liquid").checked),
      status: document.getElementById("acc-inactive") && document.getElementById("acc-inactive").checked ? "inactive" : "active",
      contacts: contacts,
    };
  }

  function refreshPreview() {
    const bank = document.getElementById("acc-institution");
    if (!bank || !document.getElementById("previewname")) return;
    const number = document.getElementById("acc-number").value.trim();
    const nick = document.getElementById("acc-nickname").value.trim();
    const bankName = bank.value.trim();
    const shown = nick || (bankName && number ? bankName + " · " + maskNumber(number) : bankName || "Sua nova conta");
    document.getElementById("previewname").textContent = shown;
    document.getElementById("previewnumber").textContent = number ? maskNumber(number) : "Número ainda não informado";
    const labels = { corrente: "Conta corrente", poupanca: "Poupança", investimento: "Investimento" };
    document.getElementById("previewkind").textContent = labels[document.getElementById("acc-kind").value] || "A escolher";
    const currency = document.getElementById("acc-currency");
    const names = { BRL: "Real", USD: "Dólar americano", EUR: "Euro" };
    const code = currency ? currency.value : "BRL";
    document.getElementById("previewcurrency").textContent = code + " · " + (names[code] || "");
    document.getElementById("currencylabel").textContent = code + " · " + (names[code] || "");
    state.accountDirty = true;
  }

  function saveAccount(event) {
    event.preventDefault();
    const button = document.getElementById("account-save");
    ["acc-institution", "acc-number", "acc-kind", "acc-bank-email", "acc-agency-email"].forEach(function (id) { setFieldError(id, ""); });
    const body = collectAccount();
    let first = "";
    function fail(id, message) {
      setFieldError(id, message);
      if (!first) first = id;
    }
    if (!body.institution) fail("acc-institution", "Informe o banco ou a instituição.");
    if (!body.accountNumber) fail("acc-number", "Informe o número da conta.");
    if (!body.kind) fail("acc-kind", "Escolha o tipo da conta.");
    if (!emailOk(body.bankEmail) || !emailOk(body.agencyEmail)) {
      const section = document.getElementById("contact-section");
      if (section) section.open = true;
    }
    if (!emailOk(body.bankEmail)) fail("acc-bank-email", "O e-mail do banco precisa ter o formato de um e-mail.");
    if (!emailOk(body.agencyEmail)) fail("acc-agency-email", "O e-mail da agência precisa ter o formato de um e-mail.");
    body.contacts.forEach(function (item, index) {
      if (!emailOk(item.email)) {
        state.openContacts = true;
        const section = document.getElementById("contact-section");
        if (section) section.open = true;
        fail("contact-email-" + index, "O e-mail do contato precisa ter o formato de um e-mail.");
      }
    });
    if (first) {
      const node = document.getElementById(first);
      if (node) node.focus();
      return;
    }
    if (button) {
      button.disabled = true;
      button.textContent = "Salvando…";
    }
    const editing = location.hash.indexOf("/editar") >= 0;
    const path = editing ? "/api/accounts/" + body.id : "/api/accounts";
    const sent = Object.assign({}, body, { registration: true });
    if (!sent.contacts.some(function (item) { return item.id; })) {
      sent.contacts = sent.contacts.map(function (item) {
        const copy = Object.assign({}, item);
        delete copy.id;
        return copy;
      });
    }
    api("POST", path, sent).then(function (result) {
      if (!result.ok) {
        const banner = document.getElementById("saveerror");
        if (banner) {
          banner.hidden = false;
          banner.textContent = (result.data && result.data.error) || "Não conseguimos salvar agora. Seu preenchimento foi mantido. Tente novamente.";
        }
        if (button) {
          button.disabled = false;
          button.textContent = "Salvar conta";
        }
        return;
      }
      if (result.data.workspace) applyWorkspace(result.data.workspace);
      else if (result.data.account) state.accounts = (state.accounts || []).filter(function (item) { return item.id !== result.data.account.id; }).concat([result.data.account]);
      state.notice = "Conta salva. Agora você pode escolher como trazer os dados.";
      state.savedAccountId = result.data.account ? result.data.account.id : "";
      state.formBuffer = null;
      state.accountDraftId = "";
      state.accountDirty = false;
      const back = state.accountReturn || "#contas";
      state.accountReturn = "";
      if (back.indexOf("import") >= 0 && result.data.account) state.importAccountId = result.data.account.id;
      persist();
      go(back);
    }).catch(function () {
      const banner = document.getElementById("saveerror");
      if (banner) {
        banner.hidden = false;
        banner.textContent = "Não conseguimos salvar agora. Seu preenchimento foi mantido. Tente novamente.";
      }
      if (button) {
        button.disabled = false;
        button.textContent = "Salvar conta";
      }
    });
  }

  function refreshAccounts(done) {
    const previous = window.isaAccountContext;
    window.isaAccountContext = "";
    api("GET", "/api/accounts").then(function (result) {
      window.isaAccountContext = previous;
      if (result.ok) {
        state.accounts = result.data.accounts || [];
        const ctx = result.data.context || {};
        window.isaAccountContext = ctx.accountId || "all";
        if (result.data.profile) state.profile = Object.assign({ ready: true }, result.data.profile);
        if (result.data.banks) state.banks = result.data.banks;
      }
      if (done) done();
    }).catch(function () {
      window.isaAccountContext = previous || "all";
      if (done) done();
    });
  }

  function enter(key) {
    state.personId = PEOPLE[key].id;
    window.isaLabPerson = key;
    state.recovery = "";
    state.draft = null;
    state.profile = { displayName: "", accessLabel: "", ready: false };
    window.isaAccountContext = "";
    persist();
    refreshAccounts(function () { go("#inicio"); });
  }

  if (!location.hash) location.hash = "#entrar";
  var booted = false;
  function boot() {
    if (booted) return;
    booted = true;
    render();
  }
  var bootTimer = setTimeout(boot, 1500);
  fetch("/api/health", { credentials: "include" }).then(function (response) { return response.json(); }).then(function (data) {
    clearTimeout(bootTimer);
    window.isaAuth = data.auth || "";
    window.isaVersion = data.version || "";
    window.isaRehearsal = !!data.rehearsal;
    if (data.lab === true && window.isaRuntime === "lab") {
      window.isaPublic = false;
      window.isaLabConfirmed = true;
      applyLabStorage();
      booted = false;
      boot();
      return;
    }
    window.isaPublic = true;
    api("GET", "/api/workspace").then(function (result) {
      if (result.ok) {
        applyWorkspace(result.data);
        if (result.data.context) window.isaAccountContext = result.data.context.accountId || "all";
      }
      return api("GET", "/api/drafts/import");
    }).then(function (draft) {
      if (draft && draft.ok && draft.data && draft.data.body && draft.data.body.movements) state.importPreview = draft.data.body;
      booted = false;
      if (state.personId && (!location.hash || location.hash === "#entrar")) location.hash = "#inicio";
      boot();
    }).catch(function () {
      booted = false;
      boot();
    });
  }).catch(boot);
})();
