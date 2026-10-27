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
      filters: { q: "", direction: "", category: "", status: "", archived: false, mode: "", consumption: false, view: "lancamentos", quick: "", currency: "", dateFrom: "", dateTo: "", open: false, batchId: "", page: 1 },
      workBatches: { items: [], activeWorkBatchId: "" },
      ledgerError: "",
      justSaved: [],
      saveIntent: "",
      returnHash: "#lancamentos",
      returnFocus: "",
      cameraError: "",
      accounts: [],
      accountsReady: false,
      accountsError: "",
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
    if (copy.importOrigin === "arquivo-teste" || copy.importOrigin === "extrato-bb-arquivo") copy.importPreview = null;
    if (window.isaPublic) {
      copy.personId = "";
      copy.entries = [];
      copy.accounts = [];
      copy.batches = [];
      copy.statementNotes = [];
      copy.occurrences = [];
      copy.workBatches = { items: [], activeWorkBatchId: "" };
    }
    sessionStorage.setItem(KEY, JSON.stringify(copy));
  }

  function api(method, path, body, extraHeaders) {
    var headers = Object.assign({ "Content-Type": "application/json" }, extraHeaders || {});
    if (!window.isaPublic && window.isaLabPerson) headers["X-ISA-Lab-Person"] = window.isaLabPerson;
    if (window.isaAccountContext) headers["X-ISA-Account"] = window.isaAccountContext;
    if (state && state.personId) headers["X-ISA-Slice"] = sliceSpec();
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
    state.accountsReady = false;
    state.accountsError = "";
    state.batches = [];
    state.statementNotes = [];
    state.occurrences = [];
    state.workBatches = { items: [], activeWorkBatchId: "" };
    state.draft = null;
    state.importPreview = null;
    state.profile = { displayName: "", accessLabel: "", ready: false };
    state.savedAccountId = "";
  }

  function applyWorkspace(data) {
    if (!data || !data.ownerId) return;
    if (window.isaOwnerId && window.isaOwnerId !== data.ownerId && window.IsaHome) window.IsaHome.reset();
    window.isaOwnerId = data.ownerId;
    if (data.context) window.isaHomeCurrency = data.context.currency || "";
    state.personId = data.ownerId;
    state.accounts = data.accounts || [];
    state.accountsReady = true;
    state.accountsError = "";
    state.entries = data.entries || [];
    state.occurrences = data.occurrences || [];
    state.statementNotes = data.notes || [];
    state.batches = data.batches || [];
    state.workBatches = data.workBatches || { items: [], activeWorkBatchId: "" };
    state.ledgerError = "";
    if (data.profile) state.profile = Object.assign({ ready: true }, data.profile);
    if (data.banks) state.banks = data.banks;
    if (!data.slice || data.slice === sliceSpec()) state.loadedSlice = sliceSpec();
  }

  function sliceSpec() {
    var f = state.filters || {};
    var route = location.hash || "";
    var parts = [];
    if (f.batchId) parts.push("batch=" + f.batchId);
    else if (route.indexOf("#lote/") === 0) parts.push("batch=" + route.slice(6));
    else if (f.mode === "todos-meses") parts.push("scope=all");
    else parts.push("month=" + (state.month || currentMonthKey()));
    if (f.archived) parts.push("archived=1");
    return parts.join("&");
  }

  function ensureBanks() {
    if (state.banks || state.banksBusy) return;
    state.banksBusy = true;
    api("GET", "/api/banks").then(function (result) {
      state.banksBusy = false;
      state.banks = result.ok && result.data.banks ? result.data.banks : [];
      render();
    }).catch(function () {
      state.banksBusy = false;
      state.banks = [];
      render();
    });
  }

  function mine() {
    return state.entries.filter(function (entry) {
      if (entry.ownerId !== state.personId) return false;
      if (!window.isaAccountContext || window.isaAccountContext === "all") return true;
      return (entry.accountId || "") === window.isaAccountContext;
    });
  }

  function go(hash) {
    document.body.setAttribute("data-click", "1");
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
    ["merchant", "noteDate", "dueDate", "statusDate", "amountText", "category", "status", "nature", "currency", "accountId"].forEach(function (key) {
      state.draft[key] = String(data.get(key) || "");
    });
    return state.draft;
  }

  function validate(draft) {
    const issues = [];
    const money = parseMoney(draft.amountText);
    if (["BRL", "USD", "EUR"].indexOf(draft.currency || "BRL") < 0 || money.review) issues.push("moeda");
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
    if (!draft.allowDuplicate && !draft.duplicateCleared) {
      api("POST", "/api/entries/duplicate-check", { entry: candidate }).then(function (result) {
        if (!result.ok) {
          state.notice = "Não foi possível conferir duplicidade. Nada foi gravado.";
          render();
          return;
        }
        if (result.data && result.data.kind && result.data.entry) {
          draft.duplicateOf = result.data.entry.id;
          draft.duplicateKind = result.data.kind;
          state.notice = "";
          render();
          return;
        }
        draft.duplicateCleared = true;
        saveDraft();
      });
      return;
    }
    draft.duplicateCleared = false;
    draft.saving = true;
    const editing = !!draft.id;
    if (!draft.id) draft.id = "lan-" + Date.now().toString(36);
    if (!draft.saveKey) draft.saveKey = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : draft.id;
    const lot = draft.solo ? null : (batchById(draft.workBatchId) || activeBatch());
    const intent = state.saveIntent || (lot && !editing ? "another" : "close");
    state.saveIntent = "";
    const record = {
      id: draft.id,
      ownerId: state.personId,
      direction: draft.direction,
      nature: draft.nature || "consumo",
      merchant: draft.merchant.trim(),
      noteDate: draft.noteDate,
      dueDate: draft.status === "pago" || draft.status === "recebido" ? "" : draft.dueDate,
      statusDate: draft.status === "pago" || draft.status === "recebido" ? draft.statusDate : "",
      amountMinor: check.money.amountMinor,
      currency: draft.currency || "BRL",
      accountId: draft.accountId || (lot && lot.defaultAccountId) || "",
      category: draft.category,
      categorizationStatus: draft.category ? "categorizado" : "a_categorizar",
      userLocked: !!draft.category,
      status: draft.status,
      source: draft.source,
      simulated: !!draft.simulated,
      documentId: draft.documentId || "",
      fingerprint: draft.fingerprint || "",
      imageLabel: draft.imageLabel || "",
      archived: !!draft.archived,
      updatedAt: new Date().toISOString(),
    };
    if (lot) record.workBatchId = lot.id;
    state.notice = "Salvando…";
    render();
    api("POST", "/api/entries", { entry: record }, { "Idempotency-Key": draft.saveKey }).then(function (result) {
      if (!result.ok || !result.data.workspace) {
        draft.saving = false;
        state.notice = (result.data && result.data.error) || "Não foi possível salvar. O rascunho continua aqui.";
        render();
        return;
      }
      applyWorkspace(result.data.workspace);
      const monthHint = window.IsaLotes ? IsaLotes.monthOf(record) : "";
      if (monthHint) state.month = monthHint;
      state.justSaved = (state.justSaved || []).concat(record.id).slice(-20);
      const finish = function () {
        if (intent === "another") {
          const next = blankDraft(draft.direction, "digitado");
          next.accountId = record.accountId;
          next.currency = record.currency;
          next.nature = draft.nature;
          next.status = draft.status;
          next.noteDate = draft.noteDate;
          next.statusDate = draft.statusDate;
          next.dueDate = draft.dueDate;
          next.workBatchId = record.workBatchId || "";
          state.draft = next;
          state.notice = "Salvo. " + moneyText(record.amountMinor, record.currency) + " entrou no lote. Pode lançar outro.";
          persist();
          render();
          return;
        }
        state.draft = null;
        if (intent !== "conclude") state.notice = "Salvo.";
        persist();
        go(intent === "conclude" ? "#lancamentos" : "#detalhe/" + record.id);
      };
      if (intent === "conclude" && record.workBatchId) {
        api("POST", "/api/work-batches/" + record.workBatchId + "/conclude", {}).then(function (done) {
          if (done.ok && done.data.workspace) applyWorkspace(done.data.workspace);
          state.notice = "Salvo. A organização deste lote foi concluída.";
          finish();
        }).catch(finish);
        return;
      }
      finish();
    }).catch(function () {
      draft.saving = false;
      state.notice = "Não foi possível salvar. O rascunho continua aqui.";
      render();
    });
  }

  window.isaRefreshEntries = function () {
    return api("GET", "/api/workspace").then(function (r) {
      if (r.ok) { applyWorkspace(r.data); render(); }
    });
  };

  function openEntry(id) {
    state.returnHash = location.hash || "#lancamentos";
    state.returnFocus = id;
    state.scrollY = window.scrollY;
    state.draft = null;
    go("#detalhe/" + id);
  }

  function resume() {
    const hash = state.returnHash || "#lancamentos";
    const focus = state.returnFocus;
    const y = state.scrollY || 0;
    go(hash);
    requestAnimationFrame(function () {
      const node = focus && document.querySelector('[data-id="' + focus + '"]');
      if (node) node.focus();
      window.scrollTo(0, y);
    });
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
      amountText: moneyInput(entry.amountMinor),
      currency: entry.currency || "BRL",
      accountId: entry.accountId || "",
      workBatchId: entry.workBatchId || "",
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
      const when = window.IsaLotes ? IsaLotes.whenOf(entry) : "";
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
    document.body.removeAttribute("data-click");
    document.body.classList.toggle("text-lg", state.font === "large");
    const root = document.getElementById("app");
    const route = location.hash || "#entrar";
    if (!state.personId && route !== "#entrar") {
      location.hash = "#entrar";
      return;
    }
    if (state.personId && route !== "#entrar") refreshSlice();
    if (route === "#contas" || route.indexOf("#contas/") === 0 || route === "#importar") ensureBanks();
    if (route.indexOf("#detalhe/") === 0) root.innerHTML = viewDetail(route.slice(9));
    else if (route.indexOf("#lote/") === 0) root.innerHTML = viewBatch(route.slice(6));
    else if (route === "#inicio") root.innerHTML = viewHome();
    else if (route === "#lancamentos" || route === "#lotes") root.innerHTML = viewList();
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
    document.body.classList.toggle("wide-ledger", route === "#lancamentos" || route === "#lotes" || route.indexOf("#lote/") === 0 || route === "#conferir");
    const task = route === "#registrar" || route === "#importar" || route === "#conferir";
    const accountOn = route === "#inicio" || route === "#lancamentos" || route === "#lotes" || route === "#planejar" || route.indexOf("#planejar/") === 0 || route === "#contas";
    document.body.classList.toggle("task", task);
    document.body.classList.toggle("account-on", !!state.personId && accountOn);
    if (state.personId) {
      const wire = function (id, fn) {
        const node = document.getElementById(id);
        if (node) node.onclick = fn;
      };
      wire("nav-inicio", function () { go("#inicio"); });
      wire("nav-registrar", function () { state.draft = null; state.notice = ""; go("#registrar"); });
      wire("nav-lista", function () { go("#lancamentos"); });
      wire("nav-planejar", function () { go("#planejar"); });
      wire("nav-contas", function () { go("#contas"); });
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
      home: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
      list: '<path d="M4 6h16M4 12h16M4 18h10"/>',
      plan: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
      account: '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 10h18"/>',
      user: '<circle cx="12" cy="9" r="3"/><path d="M6 19c1.4-3 3.6-4.2 6-4.2S16.6 16 18 19"/>',
    };
    return '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2">' + (paths[name] || "") + "</svg>";
  }

  function accountSwitch() {
    const accounts = (state.accounts || []).filter(function (item) { return item.status !== "inactive"; });
    const current = window.isaAccountContext || "all";
    const options = '<option value="all"' + (current === "all" ? " selected" : "") + ">Todas as contas · BRL</option>" +
      accounts.map(function (item) {
        const inst = item.institution ? " · " + item.institution : "";
        const moneyName = " · " + (item.currency || "BRL");
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
    const task = route === "#registrar" || route === "#importar" || route === "#conferir";
    const hideRegistrar = false;
    const showAccount = route === "#inicio" || route === "#lancamentos" || route === "#lotes" || route === "#planejar" || route.indexOf("#planejar/") === 0 || route === "#contas";
    const taskBack = route === "#registrar" ? "#inicio" : "#lancamentos";
    const taskLabel = route === "#importar" ? "Cancelar" : "Voltar";
    if (!window.IsaUi) {
      return '<div class="page">' + (title ? "<h1>" + title + "</h1>" : "") + body + "</div>";
    }
    return IsaUi.shell({
      signedIn: !!who,
      name: who ? personHeading(who) : "",
      route: route,
      accountHtml: who && showAccount ? accountSwitch() : "",
      showAccount: !!who && showAccount,
      hideRegistrar: hideRegistrar,
      title: title,
      body: body,
      task: task,
      taskBack: taskBack,
      taskLabel: taskLabel,
      taskTitle: title,
    });
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
    return shell(
      "",
      '<div class="home-top"><div><h1>Seu dinheiro</h1><p class="lede">O que já aconteceu e o que vem pela frente.</p></div></div>' +
      '<div id="money-home"><p class="muted" role="status">Carregando suas informações…</p></div>'
    );
  }

  function figure(label, amount, status, emptyText) {
    return '<button type="button" class="figure" data-status="' + status + '"><small>' + label + "</small><strong>" + (amount ? brl(amount) : esc(emptyText || "Nada neste mês")) + "</strong></button>";
  }

  function monthControl(title, current) {
    if (!window.IsaUi) {
      return '<div class="month"><button type="button" id="prev-month">Mês anterior</button><strong>' + esc(title || "") + '</strong><button type="button" id="next-month">Próximo mês</button></div>';
    }
    return IsaUi.monthControl({
      title: title,
      current: !!current,
      today: IsaUi.todayLine(),
      ids: { prev: "prev-month", next: "next-month", current: "current-month" },
    });
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
    return !!entry && (entry.source === "exemplo-sintetico" || entry.source === "arquivo-teste" || entry.source === "extrato-sintetico" || entry.source === "extrato-bb-arquivo");
  }

  function movementKind(entry) {
    if (entry.nature === "bb_rende_facil" || entry.nature === "a_conferir") return entry.direction === "ganho" ? "Entrada" : "Saída";
    return entry.direction === "ganho" ? "Ganho" : "Gasto";
  }

  function defaultFilters() {
    return { q: "", direction: "", category: "", status: "", archived: false, mode: "", consumption: false, view: "lancamentos", quick: "", currency: "", dateFrom: "", dateTo: "", open: false, batchId: "", page: 1 };
  }

  function useFilters(partial) {
    state.filters = Object.assign(defaultFilters(), partial || {});
  }

  function ensureFilters() {
    state.filters = Object.assign(defaultFilters(), state.filters || {});
  }

  function workPack() {
    return state.workBatches || { items: [], activeWorkBatchId: "" };
  }

  function batchById(id) {
    return (workPack().items || []).find(function (item) { return item.id === id; }) || null;
  }

  function activeBatch() {
    const pack = workPack();
    return (pack.items || []).find(function (item) { return item.id === pack.activeWorkBatchId && item.state === "aberto"; }) || null;
  }

  function monthTitle(key) {
    const label = monthName(key);
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  function currentMonthKey() {
    if (window.isaReferenceDate) return String(window.isaReferenceDate).slice(0, 7);
    return new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit" }).format(new Date());
  }

  function todayKey() {
    return new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo" }).format(new Date());
  }

  function entryBlob(entry) {
    const batch = batchById(entry.workBatchId || "");
    return [
      entry.merchant, entry.category, entry.documentId, entry.bankDocument, entry.supplier,
      batch ? batch.name : "", batch ? batch.documentRef : "", batch ? batch.supplier : "", batch ? batch.criterionLabel : "",
    ].join(" ");
  }

  function reviewKind(entry) {
    return IsaLotes.reviewKind(entry);
  }

  function matchesQuick(entry, quick) {
    return IsaLotes.matchesQuick(entry, quick);
  }

  function ledgerPool() {
    ensureFilters();
    const f = state.filters;
    return mine().filter(function (entry) {
      return IsaLotes.inList(entry, f, state.month, (workPack().items || []));
    });
  }

  function itemHtml(entry) {
    const tag = entry.direction === "ganho" ? "ganho" : "";
    const open = entry.status === "a_pagar" || entry.status === "a_receber" ? " aberto" : "";
    const category = entry.category || (entry.nature === "consumo" || !entry.nature ? "A categorizar" : natureLabel(entry.nature));
    const batch = batchById(entry.workBatchId || "");
    const fresh = (state.justSaved || []).indexOf(entry.id) >= 0 ? " Registrado agora." : "";
    return '<div class="item-row"><button type="button" class="item" data-id="' + esc(entry.id) + '"><span class="tag ' + tag + open + '">' +
      esc(movementKind(entry)) + " · " + esc(statusLabel(entry.status)) +
      '</span><strong>' + esc(entry.merchant) + "</strong><span>" + (window.IsaUi ? IsaUi.amount(entry.amountMinor, entry.direction === "ganho" ? "entrada" : "saida") : esc(moneyText(entry.amountMinor, entry.currency))) + " · " + esc(category) +
      (entry.nature && entry.nature !== "consumo" ? " · " + esc(natureLabel(entry.nature)) : "") +
      (isStatementEntry(entry) ? " · Extrato · " + esc(classLabel(entry.categorizationStatus)) : "") +
      esc(fresh) + "</span></button>" +
      (batch ? '<button type="button" class="lot-chip" data-open-batch="' + esc(batch.id) + '">' + esc(batch.name) + "</button>" : '<span class="lot-chip quiet">Sem lote</span>') +
      "</div>";
  }

  function lotStrip(batch) {
    if (!batch) return "";
    const outside = batch.outsideAccount != null ? batch.outsideAccount : Math.max(0, (batch.memberIds || []).length - (batch.memberIds || []).filter(function (id) {
      return mine().some(function (entry) { return entry.id === id && !entry.outsideSlice; });
    }).length);
    return '<section class="lot-strip" aria-label="Lote em andamento"><p><strong>Lote em andamento · ' + esc(batch.name) + "</strong></p><p>" +
      batch.count + (batch.count === 1 ? " registro gravado" : " registros gravados") + ". " + esc(lotHeadline(batch)) + "</p>" +
      (outside ? '<p class="muted">Lote completo. ' + outside + (outside === 1 ? " item está fora" : " itens estão fora") + " desta visualização de conta.</p>" : "") +
      '<div class="split"><button type="button" class="secondary" id="see-lot">Ver registros</button><button type="button" class="primary" id="launch-lot">Lançar neste lote</button></div></section>';
  }

  function lotHeadline(batch) {
    const codes = Object.keys((batch.totals && batch.totals.byCurrency) || {});
    if (!codes.length) return "Nenhum valor gravado ainda.";
    return codes.map(function (code) {
      const slot = batch.totals.byCurrency[code];
      return "Gastos pagos " + moneyText(slot.gastosPagos || 0, code);
    }).join(" · ");
  }

  function viewList() {
    ensureFilters();
    if ((location.hash || "") === "#lotes") state.filters.view = "lotes";
    const f = state.filters;
    const pool = ledgerPool();
    const quickPool = pool.filter(function (entry) { return matchesQuick(entry, f.quick); });
    const pageSize = 30;
    const pages = Math.max(1, Math.ceil(quickPool.length / pageSize));
    const page = Math.min(Math.max(f.page || 1, 1), pages);
    const rows = quickPool.slice((page - 1) * pageSize, page * pageSize);
    const counts = {
      todos: pool.length,
      realizados: pool.filter(function (entry) { return matchesQuick(entry, "realizados"); }).length,
      previstos: pool.filter(function (entry) { return matchesQuick(entry, "previstos"); }).length,
      conferir: pool.filter(function (entry) { return matchesQuick(entry, "conferir"); }).length,
      categoria: pool.filter(function (entry) { return reviewKind(entry) === "categoria"; }).length,
      natureza: pool.filter(function (entry) { return reviewKind(entry) === "natureza"; }).length,
    };
    const occurrences = (state.occurrences || []).filter(function (item) {
      return item.state === "pendente" && String(item.date || "").slice(0, 7) === state.month;
    });
    const active = ["q", "direction", "category", "status", "currency", "dateFrom", "dateTo", "quick", "batchId"].filter(function (key) { return !!f[key]; }).length + (f.archived ? 1 : 0);
    const openBatch = f.batchId ? batchById(f.batchId) : null;
    const foundTotals = IsaLotes.summarize(quickPool);
    const sliceTotals = IsaLotes.summarize(pool);
    const compCurrency = f.currency || "BRL";
    const comp = IsaLotes.composition(pool.filter(function (entry) { return !f.batchId || true; }), compCurrency, "pagos");
    const options = [""].concat(EXPENSE_CATS, INCOME_CATS).filter(function (cat, index, all) { return all.indexOf(cat) === index; });
    const lotCards = (workPack().items || []).map(function (batch) {
      const found = quickPool.filter(function (entry) { return entry.workBatchId === batch.id; });
      const foundMoney = IsaLotes.summarize(found);
      return '<article class="lot-card"><h2>' + esc(batch.name) + '</h2><p>' + esc(batch.criterionLabel) + " · " + esc(batch.state === "concluido" ? "Concluído" : "Em andamento") + " · " +
        found.length + " encontrado" + (found.length === 1 ? "" : "s") + " de " + batch.count + "</p>" +
        '<p>Valor dos encontrados: ' + esc(lotHeadline({ totals: foundMoney })) + "</p>" +
        '<p>Valor do lote completo: ' + esc(lotHeadline(batch)) + "</p>" +
        '<button type="button" class="secondary" data-open-batch="' + esc(batch.id) + '" data-full="1">Abrir lote completo</button>' +
        found.slice(0, 5).map(itemHtml).join("") + "</article>";
    }).join("");
    const loose = quickPool.filter(function (entry) { return !entry.workBatchId; });
    const listBody = f.view === "lotes"
      ? (lotCards || '<div class="empty"><p>Nenhum lote neste recorte. Os lançamentos sem lote continuam na outra visão.</p></div>') +
        (loose.length ? '<section class="lot-card"><h2>Sem lote</h2><p>' + loose.length + " lançamento" + (loose.length === 1 ? "" : "s") + ". Isto não é um lote financeiro.</p>" + loose.map(itemHtml).join("") + "</section>" : "")
      : '<div class="list">' + (rows.map(itemHtml).join("") || '<div class="empty"><p>' + (state.ledgerError ? "Não foi possível carregar os lançamentos." : (pool.length ? "Nada neste filtro." : "Nada neste mês. Você pode registrar uma compra sem escolher categoria.")) + "</p>" +
        (state.ledgerError ? '<button type="button" class="secondary" id="retry-ledger">Tentar de novo</button>' : "") + "</div>") + "</div>" +
        (pages > 1 ? '<div class="split"><button type="button" id="page-prev"' + (page <= 1 ? " disabled" : "") + '>Anterior</button><span>Página ' + page + " de " + pages + "</span><button type=\"button\" id=\"page-next\"" + (page >= pages ? " disabled" : "") + ">Próxima</button></div><p class=\"muted\">Os totais usam os " + quickPool.length + " encontrados, não só esta página.</p>" : "");
    const conferirNote = f.quick === "conferir"
      ? '<p class="muted">Dentro da conferência: ' + counts.categoria + " com categoria pendente, " + counts.natureza + " com natureza desconhecida e " + occurrences.length + " ocorrência de importação ainda não consolidada. Essas contagens se sobrepõem e não são partes de Todos.</p>" +
        occurrences.map(function (item) {
          return '<p class="item"><strong>' + esc(item.history || "Ocorrência do extrato") + "</strong><span> Importação ainda não consolidada · " + moneyText(Math.abs(item.cents || 0), "BRL") + "</span></p>";
        }).join("")
      : "";
    return shell("",
      '<div id="ledger" class="ledger-grid"><section>' +
      '<div class="lan-top"><div><h1>Lançamentos</h1><p class="lede">Os registros do período e, se você quiser, o lote em que eles estão.</p></div>' +
      '<div class="lan-actions"><button type="button" class="secondary" id="open-import">Importar extrato</button></div></div>' +
      (state.notice ? '<p class="oknote">' + esc(state.notice) + "</p>" : "") +
      (state.ledgerError ? '<p class="note">' + esc(state.ledgerError) + '</p><button type="button" class="secondary" id="retry-ledger">Tentar de novo</button>' : "") +
      lotStrip(activeBatch()) +
      (openBatch ? '<p class="note">Recorte dentro do lote ' + esc(openBatch.name) + ". O total do lote não muda com esta busca." +
        (f.category ? " Categoria: " + esc(f.category) + "." : "") + ' <button type="button" class="quiet" id="clear-batch-filter">Limpar filtro</button></p>' : "") +
      monthControl(f.mode === "todos-meses" ? "Todos os meses" : monthTitle(state.month), f.mode !== "todos-meses" && state.month === currentMonthKey()) +
      '<div class="month-extra"><button type="button" class="secondary" id="all-months">' + (f.mode === "todos-meses" ? "Ver só este mês" : "Todos os meses") + "</button></div>" +
      '<p class="muted">Datas no fuso de Brasília. Na lista, a data do mês é a do pagamento, do recebimento ou, se ainda estiver em aberto, a do vencimento.</p>' +
      '<label class="search-line">Busca<input id="q" value="' + esc(f.q) + '" placeholder="Descrição, lugar, documento ou lote"></label>' +
      '<div class="view-switch" role="group" aria-label="Forma de consulta"><button type="button" id="view-entries"' + (f.view !== "lotes" ? ' aria-current="true"' : "") + '>Lançamentos</button><button type="button" id="view-lots"' + (f.view === "lotes" ? ' aria-current="true"' : "") + ">Lotes</button></div>" +
      '<div class="quick-filters" role="group" aria-label="Situação dos registros">' +
      quickButton("", "Todos", counts.todos) + quickButton("realizados", "Realizados", counts.realizados) + quickButton("previstos", "Previstos", counts.previstos) + quickButton("conferir", "A conferir", counts.conferir) +
      "</div><p class=\"muted\">A conferir pode incluir lançamentos que também estão em Realizados. As contagens não são parcelas que somam Todos.</p>" +
      '<div class="split"><button type="button" id="toggle-filters">Filtros' + (active ? " (" + active + ")" : "") + '</button><button type="button" class="quiet" id="clear-filters">Limpar</button>' +
      (activeBatch() ? '<button type="button" class="quiet" id="new-lot">Criar outro lote</button>' : '<button type="button" class="quiet" id="new-lot">Começar um lote</button>') + "</div>" +
      (f.open ? '<div class="filters"><label>Tipo<select id="f-dir"><option value="">Ganhos e gastos</option><option value="ganho"' + (f.direction === "ganho" ? " selected" : "") + '>Ganhos</option><option value="gasto"' + (f.direction === "gasto" ? " selected" : "") + ">Gastos</option></select></label>" +
        '<label>Categoria<select id="f-cat">' + options.map(function (cat) { return '<option value="' + esc(cat) + '"' + (cat === f.category ? " selected" : "") + ">" + esc(cat || "Todas") + "</option>"; }).join("") + "</select></label>" +
        '<label>Situação<select id="f-status"><option value="">Todas</option><option value="pago">Pago</option><option value="a_pagar">A pagar</option><option value="recebido">Recebido</option><option value="a_receber">A receber</option></select></label>' +
        '<label>Moeda<select id="f-currency"><option value="">Todas</option><option value="BRL">Real</option><option value="USD">Dólar</option><option value="EUR">Euro</option></select></label>' +
        '<label>De<input id="f-from" type="date" value="' + esc(f.dateFrom) + '"></label><label>Até<input id="f-to" type="date" value="' + esc(f.dateTo) + '"></label>' +
        '<label><input type="checkbox" id="f-arch"' + (f.archived ? " checked" : "") + "> Arquivados</label></div>" : "") +
      conferirNote + listBody +
      '</section><aside class="ledger-side"><h2>Resumo do recorte</h2><p class="muted">' + esc(f.mode === "todos-meses" ? "Todos os meses" : (openBatch ? "Lote " + openBatch.name : monthTitle(state.month))) + ". Base: " + (f.q ? "busca. " : "") + (f.quick ? f.quick : "todos os registros deste recorte") + ".</p>" +
      IsaLotes.moneyLines(f.quick ? foundTotals : sliceTotals, moneyText, "Gastos do recorte") +
      (counts.natureza ? '<p class="muted">Resultado identificado até agora. ' + counts.natureza + " valor" + (counts.natureza === 1 ? "" : "es") + " ainda com natureza pendente, fora desse resultado.</p>" : '<p class="muted">Recebidos e pagos deste recorte. Não é saldo disponível.</p>') +
      "<h2>Gastos pagos por categoria</h2>" + IsaLotes.bars(comp, moneyText) +
      '<p class="muted">A categoria pode esperar. A ISA sugere depois de salvar, e você corrige se quiser.</p></aside></div>'
    );
  }

  function quickButton(value, label, count) {
    const on = (state.filters.quick || "") === value;
    return '<button type="button" data-quick="' + value + '"' + (on ? ' aria-current="true"' : "") + ">" + label + " <span>" + count + "</span></button>";
  }

  function viewBatch(id) {
    const batch = batchById(id);
    if (!batch) return shell("Lote", '<p>Este lote não está na sua conta.</p><button type="button" class="secondary" id="back-list">Voltar</button>');
    const members = mine().filter(function (entry) { return (batch.memberIds || []).indexOf(entry.id) >= 0; });
    const shown = state.lotCategory ? members.filter(function (entry) { return (entry.category || "A categorizar") === state.lotCategory; }) : members;
    const outside = batch.outsideAccount != null ? batch.outsideAccount : Math.max(0, (batch.memberIds || []).length - members.length);
    const comp = (batch.compositions || [])[0];
    return shell("",
      '<div class="lan-top"><div><h1>' + esc(batch.name) + '</h1><p class="lede">' + esc(batch.criterionLabel) + " · " + (batch.state === "concluido" ? "Organização concluída" : "Em andamento") + " · " + batch.count + " lançamento" + (batch.count === 1 ? "" : "s") + ".</p></div>" +
      '<div class="lan-actions"><button type="button" class="secondary" id="edit-cover">Editar capa</button>' +
      (batch.state === "concluido" ? '<button type="button" class="secondary" id="reopen-lot">Reabrir lote</button>' : '<button type="button" class="secondary" id="close-lot">Concluir lote</button>') +
      '<button type="button" class="primary" id="launch-lot">Lançar neste lote</button></div></div>' +
      (state.openedFromSearch ? '<p class="note">Você saiu do recorte da busca. Os totais abaixo são do lote completo e não mudam enquanto a busca é digitada.</p>' : "") +
      (outside ? '<p class="muted">Lote completo. ' + outside + " item fora da conta que você está vendo.</p>" : "") +
      (state.lotCategory ? '<p class="note">Itens de ' + esc(state.lotCategory) + ' dentro de ' + esc(batch.name) + '. <button type="button" class="quiet" id="clear-lot-cat">Limpar filtro</button></p>' : "") +
      (state.notice ? '<p class="oknote">' + esc(state.notice) + "</p>" : "") +
      '<div class="ledger-grid"><section><h2>Registros</h2>' + (shown.map(itemHtml).join("") || '<p class="muted">Nenhum lançamento gravado neste lote.</p>') +
      (state.editingCover ? coverForm(batch) : "") +
      '</section><aside class="ledger-side"><h2>Lote completo</h2>' + IsaLotes.moneyLines(batch.totals, moneyText, "Gastos do lote") +
      (batch.referenceGap ? '<p>Valor informado na capa: ' + moneyText(batch.referenceGap.expected, batch.referenceGap.currency) + ". Gastos registrados: " + moneyText(batch.referenceGap.registered, batch.referenceGap.currency) + ". Diferença: " + moneyText(batch.referenceGap.delta, batch.referenceGap.currency) + ". A capa não virou um lançamento.</p>" : "") +
      (batch.totals && batch.totals.archived ? '<p class="muted">' + batch.totals.archived + " registro arquivado fica fora do total vigente. Arquivar não é estorno.</p>" : "") +
      "<h2>Gastos por categoria</h2>" + (comp ? IsaLotes.bars(comp, moneyText) : '<p class="muted">Ainda não há gastos pagos para agrupar.</p>') +
      "</aside></div>"
    );
  }

  function coverForm(batch) {
    const criteria = [["evento", "Evento"], ["periodo", "Período"], ["documento", "Documento"], ["outro", "Outro"]];
    return '<form id="cover-form" class="stack"><h2>Capa</h2>' +
      '<label>Nome<input name="name" value="' + esc(batch.name) + '"></label>' +
      '<label>Critério<select name="criterion">' + criteria.map(function (item) { return '<option value="' + item[0] + '"' + (batch.criterion === item[0] ? " selected" : "") + ">" + item[1] + "</option>"; }).join("") + "</select></label>" +
      '<label>Início<input name="periodStart" type="date" value="' + esc(batch.periodStart) + '"></label>' +
      '<label>Fim<input name="periodEnd" type="date" value="' + esc(batch.periodEnd) + '"></label>' +
      '<label>Referência do documento<input name="documentRef" value="' + esc(batch.documentRef) + '"></label>' +
      '<label>Fornecedor principal da capa<input name="supplier" value="' + esc(batch.supplier) + '"></label>' +
      '<p class="muted">O fornecedor da capa não é copiado para as compras.</p>' +
      '<label>Observação<input name="note" value="' + esc(batch.note) + '"></label>' +
      '<label>Valor de referência para conferir<input name="reference" value="' + (batch.referenceMinor == null ? "" : esc(moneyInput(batch.referenceMinor))) + '" placeholder="250,00"></label>' +
      '<label>Moeda desse valor<select name="referenceCurrency"><option value="">Sem valor de referência</option><option value="BRL"' + (batch.referenceCurrency === "BRL" ? " selected" : "") + '>Real</option><option value="USD"' + (batch.referenceCurrency === "USD" ? " selected" : "") + '>Dólar</option><option value="EUR"' + (batch.referenceCurrency === "EUR" ? " selected" : "") + ">Euro</option></select></label>" +
      '<button class="primary" type="submit">Salvar capa</button></form>';
  }

  function moneyInput(minor) {
    const abs = Math.abs(Number(minor) || 0);
    return Math.floor(abs / 100) + "," + String(abs % 100).padStart(2, "0");
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
    const dupStamp = [draft.merchant, draft.noteDate, money.amountMinor || 0, draft.documentId || "", draft.fingerprint || ""].join("|");
    if (!draft.allowDuplicate && draft.dupStamp !== dupStamp && !draft.dupBusy) {
      draft.dupBusy = true;
      draft.dupStamp = dupStamp;
      api("POST", "/api/entries/duplicate-check", { entry: {
        id: draft.id,
        merchant: draft.merchant,
        noteDate: draft.noteDate,
        amountMinor: money.amountMinor || 0,
        documentId: draft.documentId,
        fingerprint: draft.fingerprint,
      } }).then(function (result) {
        draft.dupBusy = false;
        if (draft.dupStamp !== dupStamp) return;
        draft.serverDup = result.ok ? result.data : null;
        if (result.ok && result.data && result.data.kind) {
          draft.duplicateOf = result.data.entry && result.data.entry.id;
          draft.duplicateKind = result.data.kind;
        }
        render();
      });
    }
    const serverDup = draft.allowDuplicate ? null : (draft.serverDup || null);
    const dup = serverDup && serverDup.kind ? serverDup.entry : null;
    const soft = !!(serverDup && serverDup.soft);
    const statuses = draft.direction === "ganho"
      ? [["a_receber", "A receber"], ["recebido", "Recebido"]]
      : [["a_pagar", "A pagar"], ["pago", "Pago"]];
    const settled = draft.status === "pago" || draft.status === "recebido";
    const whenLabel = draft.direction === "ganho" ? "Quando recebeu?" : "Quando pagou?";
    const lot = draft.solo ? null : (batchById(draft.workBatchId) || activeBatch());
    return shell(
      draft.id ? "Corrigir lançamento" : "Conferir antes de gravar",
      (draft.simulated ? '<p class="oknote">Leitura simulada. Confira os campos. A data do documento não quita o lançamento.</p>' : "") +
      (draft.read === "parcial" ? '<p class="note">Leitura parcial: o que ficou vazio precisa de você. Não há percentual de confiança.</p>' : "") +
      (state.notice ? '<p class="note">' + esc(state.notice) + "</p>" : "") +
      (dup ? '<p class="note">Possível duplicata pelo ' + esc(draft.duplicateKind) + ". " + esc(dup.merchant) + " · " + brl(dup.amountMinor) + '.</p><div class="split"><button type="button" class="secondary" id="open-dup">Abrir o existente</button><button type="button" class="secondary" id="keep-dup">É outro lançamento</button></div>' : "") +
      (soft ? '<p class="muted">Há outro lançamento com o mesmo valor e a mesma data. Isso sozinho não bloqueia. Confira se é outro.</p>' : "") +
      (lot ? '<p class="lot-strip"><strong>Lote em andamento · ' + esc(lot.name) + "</strong> · " + lot.count + " gravado" + (lot.count === 1 ? "" : "s") + '.</p><div class="split"><button type="button" class="secondary" id="see-lot">Ver registros</button></div>' : "") +
      (draft.source === "digitado" ? "" : '<div class="thumb">' + (draft.imageDataUrl ? '<img alt="Comprovante neste aparelho" src="' + draft.imageDataUrl + '">' : esc(draft.imageLabel || "Sem imagem.")) + "</div>") +
      '<div class="review-grid"><div><form id="review-form" class="stack">' +
      field("Estabelecimento ou descrição", "merchant", draft.merchant, "text", suspect("estabelecimento"), "Nome do lugar") +
      field("Data do documento", "noteDate", draft.noteDate, "date", "", "") +
      accountChoices(draft) +
      field("Valor, como 42,80", "amountText", draft.amountText, "text", suspect("valor") || suspect("moeda"), "") +
      '<p class="muted">Moeda deste lançamento: ' + esc(draft.currency || "BRL") + ". A ISA não converte entre moedas.</p>" +
      (money.review ? '<p class="note">Este formato precisa de revisão. Use 42,80.</p>' : "") +
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
      '<input type="hidden" name="currency" value="' + esc(draft.currency || "BRL") + '">' +
      (draft.saving ? '<p class="note">Salvando…</p>' : "") +
      (lot ? '<button class="primary" type="submit" id="save">Salvar e lançar outro</button><button class="secondary" type="button" id="save-close">Salvar e concluir</button>' : '<button class="primary" type="submit" id="save">Confirmar lançamento</button>') +
      (lot ? '<button class="quiet" type="button" id="save-solo">Registrar só este, fora do lote</button>' : "") +
      '<button class="secondary" type="button" id="cancel">Cancelar</button>' +
      "</form></div>" +
      (lot ? '<aside class="ledger-side"><h2>' + esc(lot.name) + "</h2><p>" + esc(lotHeadline(lot)) + '</p><details class="lot-recent"><summary>Registros do lote (' + lot.count + ")</summary>" + recentLot(lot) + "</details></aside>" : "") +
      "</div>"
    );
  }

  function accountChoices(draft) {
    const accounts = (state.accounts || []).filter(function (account) { return account.status !== "inactive"; });
    if (!accounts.length) return '<p class="muted">Sem conta escolhida. O lançamento pode ficar sem conta.</p>';
    return '<div class="field"><label for="accountId">Conta</label><select id="accountId" name="accountId"><option value="">Sem conta neste lançamento</option>' +
      accounts.map(function (account) {
        return '<option value="' + esc(account.id) + '"' + (account.id === draft.accountId ? " selected" : "") + ">" + esc(account.name) + " · " + esc(account.currency) + "</option>";
      }).join("") + "</select></div>";
  }

  function recentLot(batch) {
    const rows = mine().filter(function (entry) { return (batch.memberIds || []).indexOf(entry.id) >= 0; }).slice(-5).reverse();
    return rows.map(function (entry) {
      return "<p><strong>" + esc(entry.merchant) + "</strong> " + moneyText(entry.amountMinor, entry.currency) + " · " + esc(statusLabel(entry.status)) + ((state.justSaved || []).indexOf(entry.id) >= 0 ? " · Registrado agora" : "") + "</p>";
    }).join("") || '<p class="muted">Nada gravado ainda. O valor digitado só entra depois da confirmação.</p>';
  }

  function field(label, name, value, type, suspect, placeholder) {
    return '<div class="field' + suspect + '"><label for="' + name + '">' + label + '</label><input id="' + name + '" name="' + name + '" type="' + type + '" value="' + esc(value) + '"' + (placeholder ? ' placeholder="' + esc(placeholder) + '"' : "") + "></div>";
  }

  function viewDetail(id) {
    const entry = mine().find(function (item) { return item.id === id; }) || (state.detailEntry && state.detailEntry.id === id ? state.detailEntry : null);
    if (!entry) {
      if (state.detailLoading !== id) {
        state.detailLoading = id;
        api("GET", "/api/entries/" + encodeURIComponent(id)).then(function (result) {
          state.detailLoading = "";
          if (result.ok && result.data && result.data.id) state.detailEntry = result.data;
          else state.detailMissing = id;
          render();
        });
      }
      if (state.detailMissing === id) return shell("Lançamento", '<p>Este lançamento não está na sua conta.</p>');
      return shell("Lançamento", "<p>Carregando…</p>");
    }
    return shell(
      entry.merchant,
      (state.notice ? '<p class="oknote">' + esc(state.notice) + "</p>" : "") +
      '<p><span class="tag ' + (entry.direction === "ganho" ? "ganho" : "") + (entry.status.indexOf("a_") === 0 ? " aberto" : "") + '">' +
      esc(movementKind(entry)) + " · " + esc(statusLabel(entry.status)) + "</span></p>" +
      '<div class="detail-block" style="padding:12px"><p><strong>' + moneyText(entry.amountMinor, entry.currency) + "</strong></p>" +
      "<p>Categoria: " + esc(entry.category || "A categorizar") + (entry.aiReason ? "" : "") + "</p>" +
      "<p>Lote: " + esc((batchById(entry.workBatchId || "") || {}).name || "Sem lote") + "</p>" +
      "<p>Conta: " + esc(((state.accounts || []).find(function (account) { return account.id === entry.accountId; }) || {}).name || "Sem conta") + "</p>" +
      "<p>Data da movimentação: " + esc(entry.statusDate || entry.dueDate || "não informada") + ". Data do registro: " + esc((entry.updatedAt || "").slice(0, 10) || "não informada") + ".</p>" +
      (entry.aiReason ? '<p class="ai-reason">' + esc(entry.aiReason) + '</p>' : "") +
      "<p>Natureza: " + esc(natureLabel(entry.nature)) + "</p>" +
      "<p>Data do documento: " + esc(entry.noteDate || "não informada") + "</p>" +
      "<p>" + (entry.status === "pago" || entry.status === "recebido" ? "Quando pagou ou recebeu: " + esc(entry.statusDate || "não informada") : "Vence quando: " + esc(entry.dueDate || "não informado")) + "</p>" +
      (isStatementEntry(entry)
        ? "<p>Origem: Extrato BB, " + (!window.isaPublic && entry.source === "exemplo-sintetico" ? "exemplo sintético" : "arquivo enviado") + ". A descrição acima é a do banco.</p><p>Classificação: " + esc(classLabel(entry.categorizationStatus)) + ". Nenhuma IA foi consultada.</p>"
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
    if (window.isaPublic) {
      state.importNotice = "Escolha o arquivo do extrato.";
      render();
      return;
    }
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
    if (parsed && parsed.ok) parsed.origin = "exemplo-sintetico";
    state.importPreview = parsed;
    ensureAccount();
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

  function knownImportOrigin(value) {
    if (value === "extrato-bb-arquivo") return value;
    if (!window.isaPublic && value === "exemplo-sintetico") return value;
    return "";
  }

  function statementSource() {
    const preview = state.importPreview || {};
    return knownImportOrigin(preview.origin) || knownImportOrigin(state.importOrigin);
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
    if (!statementSource()) {
      state.importNotice = "Escolha o arquivo de novo. A origem desta leitura não foi encontrada.";
      state.importPreview = null;
      persist();
      render();
      return;
    }
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
    const failed = !!state.accountsError && !accounts.length;
    const waiting = !state.accountsReady && !state.accountsError;
    const empty = state.accountsReady && !state.accountsError && !accounts.length;
    const side = '<aside class="panel rail"><div class="pad"><p class="eyebrow">Nesta lista</p><p><strong>' + accounts.length + "</strong> " + (accounts.length === 1 ? "conta" : "contas") + "</p><p>Moedas: " + esc(currencies.join(", ") || "nenhuma ainda") + ".</p>" +
      (currencies.length > 1 ? "<p>Valores de moedas diferentes ficam separados. Não há um total convertido.</p>" : "") +
      "<p>Para trazer movimentos, abra a conta e importe um arquivo. A conexão automática com o banco ainda não está disponível.</p></div></aside>";
    const listHead = accounts.length ? '<div class="listhead"><h2>Contas cadastradas</h2><span class="pill">' + accounts.length + (accounts.length === 1 ? " conta" : " contas") + "</span></div>" : "";
    const inner = failed
      ? '<div class="pad"><h2>Não foi possível carregar as contas</h2><p>A lista não chegou. Isso não significa que você tenha zero contas.</p><button type="button" class="btn secondary" id="retry-accounts">Tentar de novo</button></div>'
      : (waiting
        ? '<div class="pad"><h2>Carregando suas contas</h2><p class="meta">A lista aparece quando os dados chegarem.</p></div>'
        : (accounts.length ? rows : '<div class="pad"><h2>Adicione sua primeira conta</h2><p>Banco, número da conta e tipo bastam para começar.</p><p><a class="btn primary" href="#contas/nova">Adicionar conta</a></p></div>'));
    const body = (state.notice ? '<div class="notice success" role="status">' + esc(state.notice) + "</div>" : "") +
      (state.accountsError && accounts.length ? '<div class="notice error" role="alert">' + esc(state.accountsError) + ' <button type="button" class="btn secondary" id="retry-accounts">Tentar de novo</button></div>' : "") +
      (viewing ? '<p class="meta">A lista mostra todas as contas cadastradas. Início, lançamentos e planejamento seguem a conta escolhida em Visualizando.</p>' : "") +
      '<div class="accounts-layout"><section class="panel">' + listHead + inner + "</section>" + (accounts.length ? side : "") + "</div>";
    const action = empty || failed || waiting ? "" : '<p class="page-action"><a class="btn primary" href="#contas/nova" id="add-account">Adicionar conta</a></p>';
    return shell("Suas contas", '<p class="lede">Bancos, poupanças e investimentos em um só lugar.</p>' + action + body);
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
    const bankShown = account.bankCode && account.institution ? account.bankCode + " — " + account.institution : (account.institution || "Não informado");
    const data = '<section class="pad"><h2>Dados da conta</h2><dl class="facts"><div><dt>Banco</dt><dd>' + esc(bankShown) + "</dd></div><div><dt>Número</dt><dd>" + esc(account.accountNumber || "Não informado") + "</dd></div><div><dt>Tipo</dt><dd>" + esc(account.kindLabel) + "</dd></div><div><dt>Moeda</dt><dd>" + esc(moneyName(account)) + "</dd></div>" +
      (account.agency ? "<div><dt>Código da agência</dt><dd>" + esc(account.agency) + "</dd></div>" : "") +
      (account.agencyName ? "<div><dt>Nome da agência</dt><dd>" + esc(account.agencyName) + "</dd></div>" : "") +
      "<div><dt>Saldo</dt><dd>" + esc(balance) + "</dd></div></dl>" +
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
    const bankCleared = !!account.bankCleared;
    const bankName = bankCleared ? "" : (account.bankName || account.institution || "");
    const bankCode = bankCleared ? "" : (account.bankCode || "");
    const bankIspb = bankCleared ? "" : (account.bankIspb || "");
    const catalogHit = (state.banks || []).some(function (item) { return item.name === bankName && ((item.code && item.code === bankCode) || (!item.code && item.ispb === bankIspb)); });
    const bankLegacy = !bankCleared && !catalogHit && !!(bankName || bankCode || bankIspb);
    const bankQuery = account.bankQuery != null ? account.bankQuery : (bankCode && bankName ? bankCode + " — " + bankName : (bankName || bankCode));
    const bankAttrs = bankName && !bankCleared
      ? ' data-bank-name="' + esc(bankName) + '" data-bank-code="' + esc(bankCode) + '" data-bank-ispb="' + esc(bankIspb) + '"' + (bankLegacy ? ' data-bank-legacy="1"' : "")
      : "";
    const contacts = (account.contacts || []).length ? account.contacts : [{ name: "", role: "", email: "", phone: "", extension: "", scope: "conta", primary: false, roleNote: "", note: "" }];
    const contactBox = function (item, index) {
      const role = item.role || "";
      const title = index === 0 ? "Pessoa de contato" : "Pessoa de contato " + (index + 1);
      return '<fieldset class="contact-card" data-contact="' + index + '" data-id="' + esc(item.id || "") + '"><h3>' + title + "</h3>" +
        fieldBox("contact-name-" + index, "Nome", item.name, "Nome da pessoa") +
        '<label class="field">Função<select id="contact-role-' + index + '"><option value="">Escolha, se quiser</option>' +
        [["gerente_conta", "Gerente da conta"], ["gerente_agencia", "Gerente da agência"], ["atendimento", "Atendimento"], ["outro", "Outro"]].map(function (pair) {
          return '<option value="' + pair[0] + '"' + (role === pair[0] ? " selected" : "") + ">" + pair[1] + "</option>";
        }).join("") + "</select></label>" +
        '<label class="field" id="contact-note-wrap-' + index + '"' + (role === "outro" ? "" : " hidden") + '>Descrição da função<input id="contact-role-note-' + index + '" type="text" autocomplete="off" value="' + esc(item.roleNote || "") + '" placeholder="Só se escolher Outro"></label>' +
        fieldBox("contact-email-" + index, "E-mail", item.email, "nome@banco.exemplo") +
        fieldBox("contact-phone-" + index, "Telefone", item.phone, "") +
        '<input type="hidden" id="contact-extension-' + index + '" value="' + esc(item.extension || "") + '">' +
        '<input type="hidden" id="contact-scope-' + index + '" value="' + esc(item.scope || "conta") + '">' +
        '<input type="hidden" id="contact-primary-' + index + '" value="' + (item.primary ? "1" : "0") + '">' +
        '<input type="hidden" id="contact-note-' + index + '" value="' + esc(item.note || "") + '">' +
        (index > 0 || item.id ? '<button type="button" class="btn quiet remove-contact" data-remove="' + index + '">Remover deste formulário</button>' : "") +
        "</fieldset>";
    };
    const kept = [];
    if (account.nickname) kept.push("Apelido: " + account.nickname);
    if (account.country) kept.push("País: " + account.country);
    if (account.accountDigit) kept.push("Dígito da conta: " + account.accountDigit);
    if (account.agencyEmail) kept.push("E-mail da agência: " + account.agencyEmail);
    const keptBlock = kept.length ? '<div class="kept"><h3>Já registrados nesta conta</h3><p class="meta">Estes dados continuam gravados. Esta tela não pede de novo.</p><ul>' + kept.map(function (line) { return "<li>" + esc(line) + "</li>"; }).join("") + "</ul></div>" : "";
    const form = '<form id="account-form" class="panel" novalidate data-draft="' + esc(draftId) + '"><div class="pad"><h2>Dados da conta</h2>' +
      '<div id="saveerror" class="notice error" role="alert" hidden></div><div class="fieldgrid">' +
      '<label class="field full">Banco ou instituição<span class="bank-anchor"><input id="acc-institution" name="acc-institution" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="bank-listbox" aria-label="Banco ou instituição" autocomplete="off" placeholder="Busque pelo nome ou código do banco" value="' + esc(bankQuery) + '"' + bankAttrs + '><ul id="bank-listbox" class="bank-list" role="listbox" hidden></ul></span><p id="bank-state" class="meta" role="status"></p></label>' +
      fieldBox("acc-number", "Número da conta", account.accountNumber, "Ex.: 0012345-6") +
      '<label class="field">Tipo de conta<select id="acc-kind"><option value="">Escolha o tipo</option><option value="corrente"' + (account.kind === "corrente" ? " selected" : "") + '>Conta corrente</option><option value="poupanca"' + (account.kind === "poupanca" ? " selected" : "") + '>Poupança</option><option value="investimento"' + (account.kind === "investimento" ? " selected" : "") + ">Investimento</option></select></label></div>" +
      '<div id="liquid-wrap"' + (account.kind === "investimento" ? "" : " hidden") + '><label class="checkline"><input id="acc-liquid" type="checkbox"' + (account.liquid ? " checked" : "") + "> Este investimento está disponível para pagar compromissos</label><p class=\"meta\">Sem esta marca, o valor fica fora da margem disponível. Ele não vira renda.</p></div>" +
      '<label class="field">Moeda<select id="acc-currency"' + (account.currencyLocked ? " disabled" : "") + ">" + currencies.map(function (item) {
        return '<option value="' + item[0] + '"' + (item[0] === currency ? " selected" : "") + ">" + item[0] + " — " + item[1] + "</option>";
      }).join("") + "</select></label>" +
      (account.currencyLocked ? '<p class="meta">Esta conta já tem movimentação. A moeda permanece ' + esc(currency + " — " + (currencies.filter(function (item) { return item[0] === currency; })[0] || ["", currency])[1]) + ".</p>" : "") +
      '<div class="fieldgrid">' +
      fieldBox("acc-agency", "Código da agência", account.agency, "Ex.: 0123-4") +
      fieldBox("acc-agency-name", "Nome da agência", account.agencyName, "Opcional") +
      "</div>" + keptBlock +
      '<section class="contact-section" id="contact-section"><h2>Contatos do Banco</h2><p class="meta">Preencha somente o que souber. Você pode completar depois.</p><div class="fieldgrid">' +
      fieldBox("acc-bank-email", "E-mail institucional", account.bankEmail, "Opcional") +
      fieldBox("acc-agency-phone", "Telefone de atendimento", account.agencyPhone, "Opcional") +
      '</div><div id="contact-list">' + contacts.map(contactBox).join("") + '</div><button type="button" class="btn secondary" id="add-contact">Adicionar outro contato</button></section>' +
      (account.id ? '<label class="checkline"><input id="acc-inactive" type="checkbox"' + (account.status === "inactive" ? " checked" : "") + "> Inativar, preservando o histórico</label>" : "") +
      '<div class="form-actions"><button class="btn primary" type="submit" id="account-save">Salvar conta</button><button class="btn secondary" type="button" id="account-cancel">Cancelar</button></div></div></form>';
    const rail = '<aside class="panel rail"><div class="pad"><p class="eyebrow">Assim sua conta aparece</p><h2 id="previewname">' + esc(account.name || account.institution || "Sua nova conta") + '</h2><p id="previewnumber">' + esc(account.numberMasked || "Número ainda não informado") + '</p><dl class="facts"><div><dt>Tipo</dt><dd id="previewkind">' + esc(account.kindLabel || "A escolher") + '</dd></div><div><dt>Moeda</dt><dd id="previewcurrency">' + esc(moneyName(Object.assign({ currency: currency }, account))) + '</dd></div><div><dt>Saldo</dt><dd>Não informado</dd></div></dl><p class="meta">O saldo aparece depois que você o informar ou receber dados compatíveis do banco.</p><h2>Depois de salvar</h2><p>A conta fica na lista. Em seguida você pode importar um arquivo ou ver que a conexão automática ainda não está disponível.</p></div></aside>';
    return shell(
      creating ? "Adicionar conta" : "Editar conta",
      '<p class="lede">Banco, número e tipo bastam para começar.</p><p><a class="textbtn" href="#contas">Voltar às contas</a></p><div class="accounts-layout">' + form + rail + "</div>"
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

  function refreshSlice() {
    if (!state.personId || state.sliceBusy) return;
    var key = sliceSpec();
    if (state.loadedSlice === key) return;
    state.sliceBusy = true;
    api("GET", "/api/workspace?" + key).then(function (result) {
      state.sliceBusy = false;
      if (sliceSpec() !== key) {
        render();
        return;
      }
      if (result.ok) {
        applyWorkspace(result.data);
        if (result.data.context) window.isaAccountContext = result.data.context.accountId || "all";
        state.ledgerError = "";
        persist();
      } else {
        state.loadedSlice = key;
        state.ledgerError = (result.data && result.data.error) || "Não foi possível carregar os lançamentos.";
        if (!state.accountsReady) state.accountsError = "Não foi possível carregar as contas.";
      }
      render();
    }).catch(function () {
      state.sliceBusy = false;
      state.loadedSlice = key;
      state.ledgerError = "Não foi possível carregar os lançamentos.";
      if (!state.accountsReady) state.accountsError = "Não foi possível carregar as contas.";
      render();
    });
  }

  function reloadLedger() {
    state.loadedSlice = "";
    state.sliceBusy = false;
    refreshSlice();
  }

  function startBatch() {
    const today = todayKey();
    api("POST", "/api/work-batches", {
      name: "Registros de hoje",
      criterion: "periodo",
      periodStart: today,
      periodEnd: today,
      activate: true,
    }).then(function (result) {
      if (!result.ok || !result.data.workspace) {
        state.notice = (result.data && result.data.error) || "Não foi possível abrir o lote.";
        render();
        return;
      }
      applyWorkspace(result.data.workspace);
      state.notice = "Lote aberto. Você pode lançar a primeira compra.";
      state.draft = blankDraft("gasto", "digitado");
      const batch = result.data.batch;
      if (batch && batch.defaultAccountId) state.draft.accountId = batch.defaultAccountId;
      state.draft.workBatchId = batch ? batch.id : "";
      persist();
      go("#conferir");
    }).catch(function () {
      state.notice = "Não foi possível abrir o lote.";
      render();
    });
  }

  function bindLedger(on) {
    const q = document.getElementById("q");
    if (q && document.getElementById("ledger")) {
      q.oninput = function () {
        state.filters.q = q.value;
        state.filters.page = 1;
        persist();
        render();
        const again = document.getElementById("q");
        if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); }
      };
    }
    on("toggle-filters", function () { state.filters.open = !state.filters.open; persist(); render(); });
    on("clear-filters", function () { const view = state.filters.view; useFilters({ view: view }); persist(); render(); });
    on("clear-batch-filter", function () { state.filters.batchId = ""; state.filters.category = ""; state.filters.page = 1; persist(); render(); });
    on("clear-lot-cat", function () { state.lotCategory = ""; render(); });
    on("view-entries", function () { state.filters.view = "lancamentos"; persist(); go("#lancamentos"); });
    on("view-lots", function () { state.filters.view = "lotes"; persist(); go("#lotes"); });
    on("current-month", function () { state.month = currentMonthKey(); state.filters.mode = ""; state.filters.page = 1; persist(); render(); });
    on("all-months", function () {
      state.filters.mode = state.filters.mode === "todos-meses" ? "" : "todos-meses";
      state.filters.page = 1;
      persist();
      render();
    });
    on("new-lot", startBatch);
    on("see-lot", function () { const batch = activeBatch(); if (batch) go("#lote/" + batch.id); });
    on("launch-lot", function () {
      const route = location.hash || "";
      const fromPage = route.indexOf("#lote/") === 0 ? batchById(route.slice(6)) : null;
      const batch = fromPage || activeBatch();
      if (!batch) { startBatch(); return; }
      api("POST", "/api/work-preference", { activeBatchId: batch.id }).then(function (result) {
        if (result.ok) state.workBatches.activeWorkBatchId = batch.id;
      });
      state.draft = blankDraft("gasto", "digitado");
      state.draft.workBatchId = batch.id;
      if (batch.defaultAccountId) state.draft.accountId = batch.defaultAccountId;
      state.draft.solo = false;
      go("#conferir");
    });
    on("retry-ledger", reloadLedger);
    on("edit-cover", function () { state.editingCover = !state.editingCover; render(); });
    on("close-lot", function () {
      const id = (location.hash || "").slice(6);
      api("POST", "/api/work-batches/" + id + "/conclude", {}).then(function (result) {
        if (!result.ok) { state.notice = (result.data && result.data.error) || "Não foi possível concluir."; render(); return; }
        applyWorkspace(result.data.workspace);
        state.notice = "Organização concluída. Nada foi pago nem apagado.";
        persist();
        render();
      });
    });
    on("reopen-lot", function () {
      const id = (location.hash || "").slice(6);
      api("POST", "/api/work-batches/" + id + "/reopen", {}).then(function (result) {
        if (!result.ok) { state.notice = (result.data && result.data.error) || "Não foi possível reabrir."; render(); return; }
        applyWorkspace(result.data.workspace);
        state.notice = "Lote reaberto.";
        persist();
        render();
      });
    });
    on("page-prev", function () { state.filters.page = Math.max(1, (state.filters.page || 1) - 1); persist(); render(); });
    on("page-next", function () { state.filters.page = (state.filters.page || 1) + 1; persist(); render(); });
    on("save-close", function () { state.saveIntent = "conclude"; const form = document.getElementById("review-form"); if (form) form.requestSubmit(); });
    on("save-solo", function () { if (state.draft) state.draft.solo = true; state.saveIntent = "close"; const form = document.getElementById("review-form"); if (form) form.requestSubmit(); });
    const accountPick = document.getElementById("accountId");
    if (accountPick) accountPick.onchange = function () {
      const chosen = (state.accounts || []).find(function (item) { return item.id === accountPick.value; });
      if (state.draft) {
        state.draft.accountId = accountPick.value;
        if (chosen) state.draft.currency = chosen.currency;
      }
      draftFromForm();
      render();
    };
    document.querySelectorAll("[data-quick]").forEach(function (node) {
      node.onclick = function () {
        state.filters.quick = node.getAttribute("data-quick") || "";
        state.filters.page = 1;
        persist();
        render();
      };
    });
    document.querySelectorAll("[data-open-batch]").forEach(function (node) {
      node.onclick = function (event) {
        event.stopPropagation();
        state.openedFromSearch = node.getAttribute("data-full") === "1" && !!(state.filters.q || state.filters.quick || state.filters.category);
        state.lotCategory = "";
        go("#lote/" + node.getAttribute("data-open-batch"));
      };
    });
    document.querySelectorAll("[data-lot-cat]").forEach(function (node) {
      node.onclick = function () {
        const route = location.hash || "";
        if (route.indexOf("#lote/") === 0) {
          state.lotCategory = node.getAttribute("data-lot-cat") || "";
          render();
          return;
        }
        state.filters.category = node.getAttribute("data-lot-cat") || "";
        state.filters.quick = "";
        state.filters.page = 1;
        persist();
        render();
      };
    });
    ["f-dir", "f-cat", "f-status", "f-currency", "f-from", "f-to", "f-arch"].forEach(function (id) {
      const node = document.getElementById(id);
      if (!node || !document.getElementById("ledger")) return;
      node.onchange = function () {
        state.filters.direction = (document.getElementById("f-dir") || {}).value || "";
        state.filters.category = (document.getElementById("f-cat") || {}).value || "";
        state.filters.status = (document.getElementById("f-status") || {}).value || "";
        state.filters.currency = (document.getElementById("f-currency") || {}).value || "";
        state.filters.dateFrom = (document.getElementById("f-from") || {}).value || "";
        state.filters.dateTo = (document.getElementById("f-to") || {}).value || "";
        state.filters.archived = !!((document.getElementById("f-arch") || {}).checked);
        state.filters.page = 1;
        persist();
        render();
      };
    });
    const cover = document.getElementById("cover-form");
    if (cover) cover.onsubmit = function (event) {
      event.preventDefault();
      const id = (location.hash || "").slice(6);
      const batch = batchById(id);
      const data = new FormData(cover);
      const raw = String(data.get("reference") || "");
      const parsed = raw ? parseMoney(raw) : { amountMinor: null };
      if (raw && parsed.review) { state.notice = "O valor de referência precisa estar como 250,00."; render(); return; }
      api("POST", "/api/work-batches/" + id, {
        version: batch ? batch.version : 0,
        name: data.get("name"),
        criterion: data.get("criterion"),
        periodStart: data.get("periodStart"),
        periodEnd: data.get("periodEnd"),
        documentRef: data.get("documentRef"),
        supplier: data.get("supplier"),
        note: data.get("note"),
        referenceMinor: raw ? parsed.amountMinor : null,
        referenceCurrency: data.get("referenceCurrency") || "",
      }).then(function (result) {
        if (!result.ok) { state.notice = (result.data && result.data.error) || "Não foi possível salvar a capa."; render(); return; }
        applyWorkspace(result.data.workspace);
        state.editingCover = false;
        state.notice = "Capa salva.";
        persist();
        render();
      });
    };
  }

  function foldText(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function banksMatching(query) {
    const raw = foldText(query).trim();
    const banks = state.banks || [];
    if (!raw) return banks.slice(0, 40);
    const padded = /^\d+$/.test(raw) ? raw.padStart(3, "0").slice(-3) : "";
    const found = banks.filter(function (item) {
      const code = String(item.code || "");
      const shortName = foldText(item.shortName || "");
      if (foldText(item.name).indexOf(raw) >= 0) return true;
      if (shortName && shortName.indexOf(raw) >= 0) return true;
      if (foldText(code).indexOf(raw) >= 0) return true;
      return !!(padded && code === padded);
    });
    found.sort(function (left, right) {
      const leftExact = padded && left.code === padded ? 0 : 1;
      const rightExact = padded && right.code === padded ? 0 : 1;
      if (leftExact !== rightExact) return leftExact - rightExact;
      return foldText(left.name).localeCompare(foldText(right.name)) || String(left.ispb || "").localeCompare(String(right.ispb || ""));
    });
    return found.slice(0, 40);
  }

  function bankOptionLabel(item) {
    return item.code ? item.code + " — " + item.name : "Sem número-código — " + item.name;
  }

  function reloadAccounts() {
    api("GET", "/api/workspace").then(function (result) {
      if (result.ok) applyWorkspace(result.data);
      else if (result.status !== 401) state.accountsError = "Não foi possível carregar as contas.";
      render();
    }).catch(function () {
      state.accountsError = "Não foi possível carregar as contas.";
      render();
    });
  }

  function setupBankCombobox() {
    const input = document.getElementById("acc-institution");
    const list = document.getElementById("bank-listbox");
    if (!input || !list) return;
    let cursor = 0;
    let committed = null;
    if (input.getAttribute("data-bank-name") || input.getAttribute("data-bank-legacy")) {
      committed = {
        name: input.getAttribute("data-bank-name") || "",
        code: input.getAttribute("data-bank-code") || "",
        ispb: input.getAttribute("data-bank-ispb") || "",
        label: input.value,
        legacy: input.getAttribute("data-bank-legacy") === "1",
      };
    }
    function applyPick(item) {
      input.value = item.label;
      input.setAttribute("data-bank-name", item.name || "");
      input.setAttribute("data-bank-code", item.code || "");
      input.setAttribute("data-bank-ispb", item.ispb || "");
      if (item.legacy) input.setAttribute("data-bank-legacy", "1");
      else input.removeAttribute("data-bank-legacy");
      committed = item;
    }
    function clearPick() {
      input.removeAttribute("data-bank-name");
      input.removeAttribute("data-bank-code");
      input.removeAttribute("data-bank-ispb");
      input.removeAttribute("data-bank-legacy");
    }
    function closeList() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function writeStatus() {
      const note = document.getElementById("bank-state");
      if (!note) return;
      if (!state.banks) {
        note.textContent = state.accountsError ? "O catálogo de bancos não carregou. Seu preenchimento continua aqui." : "Carregando o catálogo de bancos.";
        return;
      }
      if (!state.banks.length) {
        note.textContent = "O catálogo de bancos está indisponível. Uma conta já cadastrada continua válida.";
        return;
      }
      if (input.getAttribute("data-bank-legacy") === "1") {
        note.textContent = "Esta instituição já está na conta e não faz parte do catálogo atual. Escolha uma correspondência da lista se quiser trocar.";
        return;
      }
      if (input.getAttribute("data-bank-name")) {
        note.textContent = "Banco selecionado.";
        return;
      }
      note.textContent = "";
    }
    function showMatches() {
      if (!state.banks || !state.banks.length) {
        closeList();
        writeStatus();
        return;
      }
      const items = banksMatching(input.value);
      if (!items.length) {
        list.hidden = false;
        input.setAttribute("aria-expanded", "true");
        input.removeAttribute("aria-activedescendant");
        list.innerHTML = '<li role="presentation"><p class="meta">Não encontramos esta instituição na lista.</p><button type="button" class="btn secondary" id="ask-catalog">Registrar a necessidade de atualização</button></li>';
        const ask = document.getElementById("ask-catalog");
        if (ask) ask.onpointerdown = function (event) { event.preventDefault(); };
        if (ask) ask.onclick = function (event) {
          event.preventDefault();
          const query = input.value.trim();
          if (!query) return;
          ask.disabled = true;
          api("POST", "/api/catalog-requests", { query: query }).then(function (result) {
            ask.disabled = false;
            const note = document.getElementById("bank-state");
            if (!result.ok) {
              if (note) note.textContent = (result.data && result.data.error) || "Não foi possível registrar a busca. O rascunho continua aqui.";
              return;
            }
            if (note) note.textContent = "Busca registrada. O rascunho desta conta continua aqui. Isso não cria uma conta nem consulta o banco.";
            closeList();
          }).catch(function () {
            ask.disabled = false;
            const note = document.getElementById("bank-state");
            if (note) note.textContent = "Não foi possível registrar a busca. O rascunho continua aqui.";
          });
        };
        return;
      }
      if (cursor < 0) cursor = items.length - 1;
      if (cursor >= items.length) cursor = 0;
      list.innerHTML = items.map(function (item, index) {
        const id = "bank-opt-" + index;
        return '<li role="presentation"><button type="button" role="option" id="' + id + '" aria-selected="' + (index === cursor) + '"' + (index === cursor ? ' class="is-active"' : "") + ">" + esc(bankOptionLabel(item)) + "</button></li>";
      }).join("");
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      input.setAttribute("aria-activedescendant", "bank-opt-" + cursor);
      list.querySelectorAll("[role=option]").forEach(function (button, index) {
        button.onpointerdown = function (event) {
          event.preventDefault();
          const found = items[index];
          if (!found) return;
          applyPick({ name: found.name, code: found.code || "", ispb: found.ispb || "", label: bankOptionLabel(found), legacy: false });
          closeList();
          writeStatus();
          refreshPreview();
        };
      });
    }
    input.addEventListener("focus", showMatches);
    input.addEventListener("input", function () {
      if (committed && input.value === committed.label) applyPick(committed);
      else clearPick();
      cursor = 0;
      showMatches();
      writeStatus();
    });
    input.addEventListener("keydown", function (event) {
      const open = !list.hidden;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const items = banksMatching(input.value);
        if (!items.length) {
          showMatches();
          return;
        }
        cursor += event.key === "ArrowDown" ? 1 : -1;
        showMatches();
        return;
      }
      if (event.key === "Enter" && open) {
        const items = banksMatching(input.value);
        if (!items.length) return;
        event.preventDefault();
        const found = items[cursor] || items[0];
        applyPick({ name: found.name, code: found.code || "", ispb: found.ispb || "", label: bankOptionLabel(found), legacy: false });
        closeList();
        writeStatus();
        refreshPreview();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        if (committed) applyPick(committed);
        closeList();
        writeStatus();
      }
    });
    input.addEventListener("blur", function () {
      setTimeout(closeList, 180);
    });
    writeStatus();
  }

  function bind() {
    const on = function (id, fn) {
      const node = document.getElementById(id);
      if (node) node.onclick = fn;
    };
    Array.prototype.forEach.call(document.querySelectorAll(".brand-link"), function (link) {
      link.onclick = function () {
        Array.prototype.forEach.call(document.querySelectorAll(".brand-link"), function (item) {
          const on = item === link;
          item.classList.toggle("is-current", on);
          if (on) item.setAttribute("aria-current", "page");
          else item.removeAttribute("aria-current");
        });
      };
    });
    const switcher = document.getElementById("account-switch");
    if (switcher) switcher.onchange = function () {
      window.isaAccountContext = switcher.value || "all";
      var picked = (state.accounts || []).find(function (item) { return item.id === window.isaAccountContext; });
      window.isaHomeCurrency = picked ? (picked.currency || "") : "";
      api("POST", "/api/accounts/select", { context: window.isaAccountContext }).finally(function () { render(); });
    };
    on("brand-leave", function () { leavePerson(); });
    const accountFormNode = document.getElementById("account-form");
    if (accountFormNode) {
      accountFormNode.onsubmit = saveAccount;
      accountFormNode.addEventListener("input", refreshPreview);
      accountFormNode.addEventListener("change", refreshPreview);
      setupBankCombobox();
    }
    on("retry-accounts", reloadAccounts);
    on("retry-banks", reloadAccounts);
    document.querySelectorAll("[data-contact] select").forEach(function (select) {
      if (select.id.indexOf("contact-role-") !== 0) return;
      select.addEventListener("change", function () {
        const wrap = document.getElementById("contact-note-wrap-" + select.id.replace("contact-role-", ""));
        if (wrap) wrap.hidden = select.value !== "outro";
      });
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
    on("back-list", function () { state.notice = ""; resume(); });
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
      state.importOrigin = "extrato-bb-arquivo";
      state.importFileName = file.name;
      render();
      const reader = new FileReader();
      reader.onload = function () {
        const bytes = new Uint8Array(reader.result);
        const parsed = IsaStatement.readStatement(bytes);
        if (parsed && parsed.ok) parsed.origin = "extrato-bb-arquivo";
        state.importPreview = parsed;
        state.importReading = false;
        ensureAccount();
        if (window.isaPublic && parsed && parsed.ok) api("PUT", "/api/drafts/import", parsed);
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
    bindLedger(on);
    if (!document.getElementById("ledger")) ["q", "f-dir", "f-cat", "f-status", "f-arch"].forEach(function (id) {
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
    window.isaOwnerId = "";
    window.isaHomeCurrency = "";
    if (window.IsaHome) window.IsaHome.reset();
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
    const read = function (id) {
      const node = document.getElementById(id);
      return node ? node.value.trim() : "";
    };
    const contacts = [];
    document.querySelectorAll("[data-contact]").forEach(function (node) {
      const index = node.getAttribute("data-contact");
      const item = {
        index: index,
        id: node.getAttribute("data-id") || "",
        name: read("contact-name-" + index),
        role: read("contact-role-" + index),
        roleNote: read("contact-role-note-" + index),
        email: read("contact-email-" + index),
        phone: read("contact-phone-" + index),
        extension: read("contact-extension-" + index),
        scope: read("contact-scope-" + index) || "conta",
        primary: read("contact-primary-" + index) === "1",
        note: read("contact-note-" + index),
      };
      contacts.push(item);
    });
    const currency = document.getElementById("acc-currency");
    const bank = document.getElementById("acc-institution");
    const bankName = bank ? (bank.getAttribute("data-bank-name") || "") : "";
    const inactive = document.getElementById("acc-inactive");
    const payload = {
      id: form ? form.getAttribute("data-draft") : "",
      institution: bankName,
      bankName: bankName,
      bankCode: bank ? (bank.getAttribute("data-bank-code") || "") : "",
      bankIspb: bank ? (bank.getAttribute("data-bank-ispb") || "") : "",
      bankQuery: bank ? bank.value : "",
      bankCleared: !bankName,
      accountNumber: read("acc-number"),
      kind: read("acc-kind"),
      currency: currency ? currency.value : "BRL",
      agency: read("acc-agency"),
      agencyName: read("acc-agency-name"),
      bankEmail: read("acc-bank-email"),
      agencyPhone: read("acc-agency-phone"),
      liquid: !!(document.getElementById("acc-liquid") && document.getElementById("acc-liquid").checked),
      contacts: contacts,
    };
    if (inactive) payload.status = inactive.checked ? "inactive" : "active";
    return payload;
  }

  function refreshPreview() {
    const bank = document.getElementById("acc-institution");
    if (!bank || !document.getElementById("previewname")) return;
    const number = document.getElementById("acc-number").value.trim();
    const bankName = bank.getAttribute("data-bank-name") || "";
    const shown = bankName && number ? bankName + " · " + maskNumber(number) : (bankName || "Sua nova conta");
    document.getElementById("previewname").textContent = shown;
    document.getElementById("previewnumber").textContent = number ? maskNumber(number) : "Número ainda não informado";
    const labels = { corrente: "Conta corrente", poupanca: "Poupança", investimento: "Investimento" };
    document.getElementById("previewkind").textContent = labels[document.getElementById("acc-kind").value] || "A escolher";
    const currency = document.getElementById("acc-currency");
    const names = { BRL: "Real", USD: "Dólar americano", EUR: "Euro" };
    const code = currency ? currency.value : "BRL";
    document.getElementById("previewcurrency").textContent = code + " — " + (names[code] || "");
    state.accountDirty = true;
  }

  function saveAccount(event) {
    event.preventDefault();
    const button = document.getElementById("account-save");
    if (state.accountSaving) return;
    ["acc-institution", "acc-number", "acc-kind", "acc-bank-email"].forEach(function (id) { setFieldError(id, ""); });
    const body = collectAccount();
    let first = "";
    function fail(id, message) {
      setFieldError(id, message);
      if (!first) first = id;
    }
    if (!body.institution) fail("acc-institution", "Escolha um banco da lista.");
    if (!body.accountNumber) fail("acc-number", "Informe o número da conta.");
    if (!body.kind) fail("acc-kind", "Escolha o tipo da conta.");
    if (!emailOk(body.bankEmail)) fail("acc-bank-email", "O e-mail do banco precisa ter o formato de um e-mail.");
    body.contacts.forEach(function (item) {
      if (!emailOk(item.email)) fail("contact-email-" + item.index, "O e-mail do contato precisa ter o formato de um e-mail.");
      if (item.role === "outro" && !item.roleNote && (item.name || item.email || item.phone)) {
        const wrap = document.getElementById("contact-note-wrap-" + item.index);
        if (wrap) wrap.hidden = false;
        fail("contact-role-note-" + item.index, "Descreva a função quando escolher Outro.");
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
    state.accountSaving = true;
    const editing = location.hash.indexOf("/editar") >= 0;
    const path = editing ? "/api/accounts/" + body.id : "/api/accounts";
    const sent = Object.assign({}, body, { registration: true });
    delete sent.bankQuery;
    delete sent.bankCleared;
    delete sent.bankName;
    delete sent.index;
    sent.contacts = sent.contacts.filter(function (item) {
      return item.name || item.role || item.email || item.phone || item.extension || item.roleNote || item.note;
    }).map(function (item) {
      const copy = Object.assign({}, item);
      delete copy.index;
      if (!copy.id) delete copy.id;
      return copy;
    });
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
        state.accountSaving = false;
        return;
      }
      if (result.data.workspace) applyWorkspace(result.data.workspace);
      else if (result.data.account) state.accounts = (state.accounts || []).filter(function (item) { return item.id !== result.data.account.id; }).concat([result.data.account]);
      state.notice = "Conta salva. Agora você pode escolher como trazer os dados.";
      state.savedAccountId = result.data.account ? result.data.account.id : "";
      state.accountSaving = false;
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
      state.accountSaving = false;
    });
  }

  function refreshAccounts(done) {
    const previous = window.isaAccountContext;
    window.isaAccountContext = "";
    api("GET", "/api/accounts").then(function (result) {
      window.isaAccountContext = previous;
      if (result.ok) {
        state.accounts = result.data.accounts || [];
        state.accountsReady = true;
        state.accountsError = "";
        const ctx = result.data.context || {};
        window.isaAccountContext = ctx.accountId || "all";
        if (result.data.profile) state.profile = Object.assign({ ready: true }, result.data.profile);
        if (result.data.banks) state.banks = result.data.banks;
      } else {
        state.accountsError = "Não foi possível carregar as contas.";
      }
      if (done) done();
    }).catch(function () {
      window.isaAccountContext = previous || "all";
      state.accountsError = "Não foi possível carregar as contas.";
      if (done) done();
    });
  }

  function enter(key) {
    state.personId = PEOPLE[key].id;
    window.isaLabPerson = key;
    window.isaOwnerId = "";
    window.isaHomeCurrency = "";
    if (window.IsaHome) window.IsaHome.reset();
    state.recovery = "";
    state.draft = null;
    state.profile = { displayName: "", accessLabel: "", ready: false };
    window.isaAccountContext = "";
    persist();
    api("GET", "/api/workspace").then(function (result) {
      if (result.ok) applyWorkspace(result.data);
      refreshAccounts(function () { go("#inicio"); });
    }).catch(function () { refreshAccounts(function () { go("#inicio"); }); });
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
      window.isaLabPerson = state.personId === "pessoa-paulo" ? "paulo" : state.personId === "pessoa-marina" ? "marina" : state.personId === "pessoa-eveline-demo" ? "eveline" : "";
      if (!state.personId) { booted = false; boot(); return; }
      booted = false;
      boot();
      api("GET", "/api/workspace").then(function (result) {
        if (result.ok) applyWorkspace(result.data);
        else {
          state.ledgerError = "Não foi possível carregar os lançamentos.";
          state.accountsError = "Não foi possível carregar as contas.";
        }
        booted = false;
        boot();
      }).catch(function () {
        state.ledgerError = "Não foi possível carregar os lançamentos.";
        state.accountsError = "Não foi possível carregar as contas.";
        booted = false;
        boot();
      });
      return;
    }
    window.isaPublic = true;
    booted = false;
    boot();
    api("GET", "/api/workspace").then(function (result) {
      if (result.ok) {
        applyWorkspace(result.data);
        if (result.data.context) window.isaAccountContext = result.data.context.accountId || "all";
      } else if (result.status !== 401) {
        state.ledgerError = (result.data && result.data.error) || "Não foi possível carregar os lançamentos.";
        state.accountsError = "Não foi possível carregar as contas.";
      }
      booted = false;
      if (state.personId && (!location.hash || location.hash === "#entrar")) location.hash = "#inicio";
      boot();
      api("GET", "/api/drafts/import").then(function (draft) {
        if (draft && draft.ok && draft.data && draft.data.body && draft.data.body.movements) {
          state.importPreview = draft.data.body;
          state.importOrigin = draft.data.body.origin || "";
          if (location.hash === "#importar") render();
        }
      });
      return null;
    }).then(function () {
      return null;
    }).catch(function () {
      if (!state.accountsReady) state.accountsError = "Não foi possível carregar as contas.";
      booted = false;
      boot();
    });
  }).catch(boot);
})();
