(function () {
  var saveTimer = null;
  var loadToken = 0;
  var loadedDraft = null;
  var busy = false;

  function today() { return new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date()); }
  function esc(value) { return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function monthName(value) { return new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(value + "-01T12:00:00Z")); }
  function person() { return window.isaLabPerson || ""; }

  function api(method, path, body) {
    var headers = { "Content-Type": "application/json" };
    if (!window.isaPublic && person()) headers["X-ISA-Lab-Person"] = person();
    return fetch(path, {
      method: method,
      credentials: "include",
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          var error = new Error(data.error || "Não foi possível salvar");
          error.status = response.status;
          throw error;
        }
        return data;
      });
    });
  }

  function brl(cents) {
    var sign = cents < 0 ? "-" : "";
    var value = Math.abs(Number(cents) || 0);
    var whole = Math.floor(value / 100).toLocaleString("pt-BR");
    var frac = String(value % 100).padStart(2, "0");
    return sign + "R$ " + whole + "," + frac;
  }

  function moneyText(cents) {
    if (cents == null || cents === "") return "";
    var sign = cents < 0 ? "-" : "";
    var value = Math.abs(Number(cents));
    var whole = Math.floor(value / 100).toLocaleString("pt-BR");
    return sign + whole + "," + String(value % 100).padStart(2, "0");
  }

  function showDate(iso) {
    var parts = String(iso || "").split("-");
    if (parts.length !== 3) return "";
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function cents(text) {
    var raw = String(text || "").trim();
    if (!raw) return null;
    if (!/^-?\d{1,3}(\.\d{3})*,\d{2}$/.test(raw) && !/^-?\d+,\d{2}$/.test(raw)) return null;
    var negative = raw.charAt(0) === "-";
    var digits = raw.replace("-", "").replace(/\./g, "").replace(",", "");
    var value = Number(digits);
    if (!Number.isFinite(value)) return null;
    return negative ? -value : value;
  }

  function status(node, text, kind) {
    if (!node) return;
    node.className = kind === "ok" ? "oknote" : kind === "saving" ? "muted" : "note";
    node.textContent = text;
  }

  function mergeDraft(extra) {
    var next = {};
    Object.keys(loadedDraft || {}).forEach(function (key) { next[key] = loadedDraft[key]; });
    Object.keys(extra || {}).forEach(function (key) {
      if (extra[key] === undefined) delete next[key];
      else next[key] = extra[key];
    });
    return next;
  }

  function persistDraft(extra) {
    var body = mergeDraft(extra);
    return api("PUT", "/api/drafts/planejar", body).then(function () {
      loadedDraft = body;
      return body;
    });
  }

  function remember(extra) {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      persistDraft(extra).catch(function () {
        status(document.getElementById("save-state"), "Não foi possível guardar o rascunho. O que você digitou continua nesta tela.", "error");
      });
    }, 250);
  }

  function requestedStep() {
    var hash = location.hash || "";
    if (hash.indexOf("disponivel") >= 0) return "availability";
    if (hash.indexOf("entrada") >= 0) return "inflow";
    if (hash.indexOf("contas") >= 0) return "commitments";
    if (hash.indexOf("resumo") >= 0) return "summary";
    return "";
  }

  function goPlan(hash) {
    if (location.hash === hash) open();
    else location.hash = hash;
  }

  function reveal(node) {
    if (!node) return;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (node.focus) node.focus({ preventScroll: true });
    if (node.scrollIntoView) node.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
  }

  function guideOf(data) {
    return data.guide || { step: "availability", gaps: ["availability"], availabilityKnown: false, commitmentCount: (data.commitments || []).length };
  }

  function homeHtml(data) {
    var guide = guideOf(data);
    var gap = (guide.gaps || [])[0];
    var actions = {
      availability: ["Para saber se o dinheiro chega, falta o valor que você pode usar agora.", "Informar dinheiro disponível", "#planejar/disponivel"],
      inflow: ["Falta dizer quando você espera receber.", "Informar a próxima entrada", "#planejar/entrada"],
      commitments: ["Falta informar as contas a pagar.", "Informar contas a pagar", "#planejar/contas"],
      "commitment-values": ["Há conta a pagar sem valor ou vencimento.", "Completar contas a pagar", "#planejar/contas"],
    };
    if (actions[gap]) {
      return '<section class="decision"><p>' + actions[gap][0] + '</p><button class="primary" type="button" id="plan-start" data-plan-target="' + actions[gap][2] + '">' + actions[gap][1] + "</button></section>";
    }
    var projection = data.projection || {};
    var upcoming = (data.commitments || []).filter(function (item) { return item.due_on >= projection.reference; }).slice(0, 3);
    var income = projection.next_inflow;
    return '<section class="decision"><h2>O próximo ponto</h2><p>Em ' + showDate(projection.minimum.date) + " o disponível chega a <strong>" + brl(projection.minimum.cents) + "</strong>.</p>" +
      (income ? "<p>Próxima entrada confirmada: " + brl(income.cents) + " em " + showDate(income.on) + ".</p>" : "<p>Não há entrada confirmada no horizonte.</p>") +
      (upcoming.length ? "<p>Compromissos próximos: " + upcoming.map(function (item) { return esc(item.label) + " " + brl(item.remaining_cents) + " em " + showDate(item.due_on); }).join("; ") + ".</p>" : "") +
      (projection.floor_gap_cents ? "<p>Para preservar a reserva, faltam " + brl(projection.floor_gap_cents) + " no ponto mais baixo.</p>" : "") +
      '<button class="primary" type="button" id="plan-start" data-plan-target="#planejar/resumo">Ver o que muda se um compromisso mudar de data</button>' +
      (data.chosenPlan ? '<p class="oknote">Plano escolhido. O vencimento original dos compromissos não mudou.</p>' : "") +
      '<p class="muted">' + esc(data.explanation && data.explanation.text ? data.explanation.text : "") + "</p></section>";
  }

  function fillHome() {
    var slot = document.getElementById("plan-home");
    if (!slot || (!window.isaPublic && !person())) return;
    api("GET", "/api/home").then(function (data) {
      if (!document.getElementById("plan-home")) return;
      document.getElementById("plan-home").innerHTML = homeHtml(data);
      var button = document.getElementById("plan-start");
      if (button) button.onclick = function () { goPlan(button.getAttribute("data-plan-target") || "#planejar/disponivel"); };
    }).catch(function () {
      var node = document.getElementById("plan-home");
      if (!node) return;
      node.innerHTML = '<p class="note">Não foi possível carregar suas informações.</p><button class="secondary" type="button" id="plan-home-retry">Tentar de novo</button>';
      document.getElementById("plan-home-retry").onclick = fillHome;
    });
  }

  function weekday(iso) {
    var parts = iso.split("-").map(Number);
    return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2])).getUTCDay();
  }

  function calendar(days, month) {
    var inMonth = days.filter(function (item) { return item.date.slice(0, 7) === month; });
    if (!inMonth.length) return "<p>Não há dias deste mês na projeção.</p>";
    var blanks = weekday(month + "-01");
    var cells = "";
    var names = ["D", "S", "T", "Q", "Q", "S", "S"];
    for (var i = 0; i < 7; i += 1) cells += '<span class="dow">' + names[i] + "</span>";
    for (var blank = 0; blank < blanks; blank += 1) cells += "<span></span>";
    inMonth.forEach(function (item) {
      var mark = item.below_zero ? "Falta" : item.in_cents ? "Entra" : item.out_cents ? "Sai" : "";
      cells += '<button type="button" class="day' + (item.below_zero ? " short" : "") + '" data-day="' + item.date + '"><strong>' + Number(item.date.slice(8)) + '</strong><span>' + mark + "</span></button>";
    });
    return '<div class="cal" aria-label="Dias do mês">' + cells + "</div>";
  }

  function dayDetail(days, iso) {
    var item = days.filter(function (day) { return day.date === iso; })[0];
    if (!item) return "";
    var events = item.events.length ? item.events.map(function (event) {
      return "<li>" + (event.kind === "entrada" ? "Entrada" : "Saída") + ": " + esc(event.label) + " " + brl(event.cents) + "</li>";
    }).join("") : "<li>Sem movimento neste dia.</li>";
    var order = item.order_dependency ? "<p>Há entrada e saída no mesmo dia. Sem horário, a ordem pode mudar se o saldo aguenta.</p>" : "";
    return "<h3>" + showDate(iso) + "</h3><p>Disponível no fim do dia: " + brl(item.cents) + (item.below_zero ? ". Falta dinheiro." : item.below_floor ? ". A reserva protegida foi invadida." : ".") + "</p><ul>" + events + "</ul>" + order;
  }

  function board(data) {
    var projection = data.projection;
    var month = projection.reference.slice(0, 7);
    var nextMonth = projection.horizon_end.slice(0, 7);
    var selected = projection.first_insufficiency || projection.minimum.date;
    var preferred = (data.commitments || []).filter(function (item) { return item.due_on >= projection.reference; })[0];
    var options = (data.commitments || []).map(function (item) {
      return '<option value="' + item.id + '"' + (preferred && item.id === preferred.id ? " selected" : "") + ">" + esc(item.label) + " · " + showDate(item.due_on) + "</option>";
    }).join("");
    return '<p id="save-state" class="oknote">Salvo na sua conta.</p>' +
      '<div class="import-layout"><div><h2>' + monthName(month) + '</h2><p class="legend"><span class="swatch short"></span> Falta <span class="swatch in"></span> Entra <span class="swatch out"></span> Sai</p>' +
      calendar(projection.days, month) + '<div id="day-detail">' + dayDetail(projection.days, selected) + "</div>" +
      '<h2>' + monthName(nextMonth) + '</h2>' + calendar(projection.days, nextMonth) + "</div><div class=\"decision\">" +
      "<h2>Comparar uma alternativa</h2><p>Isto não paga, não pede crédito e não muda o vencimento.</p>" +
      '<form id="alt-form" class="stack"><label>Qual compromisso?<select id="alt-commitment">' + options + '</select></label>' +
      '<label>Nova data<input id="alt-date" type="date" value="' + today() + '"></label>' +
      '<button class="primary" type="submit">Comparar</button></form><div id="alt-result"></div>' +
      '<form id="spend-form" class="stack"><h2>Posso gastar?</h2><label>Valor<input id="spend-amount" inputmode="decimal" placeholder="Informe o valor"></label>' +
      '<label>Categoria, se quiser<input id="spend-category" placeholder="Se quiser"></label>' +
      '<label>Data<input id="spend-date" type="date" value="' + today() + '"></label><button class="secondary" type="submit">Ver o efeito</button></form><div id="spend-result"></div>' +
      '<form id="more-form" class="stack"><h2>Outro compromisso</h2><label>O que é?<input id="more-label"></label><label>Quanto?<input id="more-amount" inputmode="decimal" placeholder="Informe o valor"></label><label>Vence quando?<input id="more-date" type="date"></label><button class="secondary" type="submit">Guardar</button></form>' +
      (data.chosenPlan ? '<p class="oknote">Plano escolhido guardado. O compromisso original continua na data combinada.</p>' : "") +
      (window.isaPublic ? "" : '<div class="demo-box"><p><strong>Demonstração</strong></p><p class="muted">O exemplo de outubro é fictício. Não lê o que está só neste navegador.</p><button class="secondary" type="button" id="load-october">Carregar o exemplo de outubro</button></div>') + "</div></div>";
  }

  function bindBoard(data) {
    document.querySelectorAll("[data-day]").forEach(function (node) {
      node.onclick = function () {
        var detail = document.getElementById("day-detail");
        if (detail) detail.innerHTML = dayDetail(data.projection.days, node.getAttribute("data-day"));
      };
    });
    var form = document.getElementById("alt-form");
    if (form) form.onsubmit = function (event) {
      event.preventDefault();
      if (busy) return;
      var node = document.getElementById("save-state");
      status(node, "Salvando…", "saving");
      busy = true;
      api("POST", "/api/scenarios", {
        name: "Alternativa",
        reference: today(),
        changes: [{ commitmentId: document.getElementById("alt-commitment").value, dueOn: document.getElementById("alt-date").value }],
        label: "somente a data escolhida mudar",
      }).then(function (scenario) {
        busy = false;
        status(node, "Salvo na sua conta.", "ok");
        var result = JSON.parse(scenario.result_json);
        var box = document.getElementById("alt-result");
        box.innerHTML = "<p>Agora o ponto mais baixo é " + brl(data.projection.minimum.cents) + " em " + showDate(data.projection.minimum.date) + ".</p><p>Na alternativa, o ponto mais baixo fica " + brl(result.minimum.cents) + " e o mês termina em " + brl(result.october_end_cents) + ".</p><p>" + esc(scenario.note) + "</p>" +
          '<button class="primary" type="button" id="choose-plan">Guardar como plano escolhido</button>';
        document.getElementById("choose-plan").onclick = function () {
          if (busy) return;
          busy = true;
          status(node, "Salvando…", "saving");
          api("POST", "/api/scenarios/" + scenario.id + "/choose", {}).then(function () {
            busy = false;
            status(node, "Salvo na sua conta. Plano escolhido. Nada foi pago.", "ok");
          }).catch(function () { busy = false; status(node, "Não foi possível salvar. Tente de novo.", "error"); });
        };
      }).catch(function () { busy = false; status(node, "Não foi possível salvar. Tente de novo.", "error"); });
    };
    var spend = document.getElementById("spend-form");
    if (spend) spend.onsubmit = function (event) {
      event.preventDefault();
      var amount = cents(document.getElementById("spend-amount").value);
      var node = document.getElementById("save-state");
      if (amount === null) {
        status(node, "Informe o valor. Em branco não é zero.", "error");
        return;
      }
      api("POST", "/api/spend", {
        amountCents: amount,
        on: document.getElementById("spend-date").value,
        category: document.getElementById("spend-category").value,
        reference: today(),
      }).then(function (payload) {
        document.getElementById("spend-result").textContent = payload.explanation.text;
      }).catch(function (error) { status(node, error.message || "Não foi possível consultar.", "error"); });
    };
    var more = document.getElementById("more-form");
    if (more) more.onsubmit = function (event) {
      event.preventDefault();
      if (busy) return;
      var amount = cents(document.getElementById("more-amount").value);
      var label = document.getElementById("more-label").value.trim();
      var due = document.getElementById("more-date").value;
      var node = document.getElementById("save-state");
      if (!label || amount === null) {
        status(node, "Falta o nome ou o valor. Isso não vira zero.", "error");
        return;
      }
      if ((data.commitments || []).some(function (item) { return item.label === label && item.total_cents === amount && item.due_on === due; })) {
        status(node, "Este compromisso já está na lista.", "error");
        return;
      }
      busy = true;
      status(node, "Salvando…", "saving");
      api("POST", "/api/commitments", { label: label, totalCents: amount, dueOn: due, origin: "declarada" }).then(function () {
        busy = false;
        goPlan("#planejar/contas");
      }).catch(function (error) { busy = false; status(node, error.message || "Não foi possível salvar. Tente de novo.", "error"); });
    };
    var demo = document.getElementById("load-october");
    if (demo) demo.onclick = function () {
      api("POST", "/api/fixtures/october", {}).then(open).catch(function () {
        status(document.getElementById("save-state"), "Não foi possível carregar o exemplo.", "error");
      });
    };
  }

  function progress(current) {
    var steps = [["availability", "Seu dinheiro"], ["inflow", "Próxima entrada"], ["commitments", "Contas a pagar"]];
    return '<nav aria-label="Progresso"><ol class="plan-progress">' + steps.map(function (item) {
      return '<li' + (item[0] === current ? ' aria-current="step"' : "") + ">" + item[1] + "</li>";
    }).join("") + "</ol></nav>";
  }

  function sideHtml(data) {
    var guide = guideOf(data);
    var parts = [];
    if (guide.availability) parts.push("<p>Disponível salvo: " + brl(guide.availability.amountCents) + " em " + showDate(guide.availability.asOf) + ".</p>");
    if (guide.availability && guide.availability.protectedCents) parts.push("<p>Reserva incluída nesse valor: " + brl(guide.availability.protectedCents) + ".</p>");
    var confirmed = (data.inflows || []).filter(function (item) { return item.state === "confirmada" && item.amount_cents != null; });
    if (confirmed.length) parts.push("<p>Entrada: " + esc(confirmed[0].label) + " " + brl(confirmed[0].amount_cents) + ".</p>");
    if ((data.commitments || []).length) parts.push("<p>" + data.commitments.length + (data.commitments.length === 1 ? " conta informada." : " contas informadas.") + "</p>");
    if (!parts.length) return "";
    return '<aside class="plan-side"><h2>Já informado</h2>' + parts.join("") + "</aside>";
  }

  function frame(step, title, explanation, body, data, gap) {
    var side = sideHtml(data);
    return '<div class="plan-journey" id="plan-stage"><a class="quiet plan-back" href="#inicio">Voltar</a>' + progress(step) +
      '<div class="plan-layout' + (side ? " with-side" : "") + '"><div class="plan-card"><h2 id="plan-title" tabindex="-1">' + title + "</h2><p>" + explanation + '</p><p id="save-state" class="muted" aria-live="polite"></p>' + body +
      '<button class="quiet" type="button" id="plan-help">Preciso de ajuda para responder</button><div id="plan-help-slot" hidden><p>Os campos acima são o lugar para responder. Você não precisa escrever o valor em uma pergunta livre.</p></div></div>' +
      side + '</div><div id="plan-ai-slot" data-gap="' + esc(gap || "") + '"></div></div>';
  }

  function moneyField(id, label, value) {
    return '<div class="field"><label for="' + id + '">' + label + '</label><div class="money"><span aria-hidden="true">R$</span><input id="' + id + '" inputmode="decimal" autocomplete="off" placeholder="Informe o valor" aria-describedby="' + id + '-error" value="' + esc(value) + '"></div><p id="' + id + '-error" class="field-error" role="alert"></p></div>';
  }

  function markError(id, message) {
    var node = document.getElementById(id + "-error");
    if (node) node.textContent = message || "";
    var input = document.getElementById(id);
    if (input) input.setAttribute("aria-invalid", message ? "true" : "false");
  }

  function moneyMessage(raw) {
    if (!String(raw || "").trim()) return "Informe o valor. Em branco não é zero.";
    if (cents(raw) === null) return "Use o valor em reais, como 1.200,50.";
    return "";
  }

  function choiceButtons(name, options, selected) {
    return '<div class="plan-choice" role="group" aria-label="' + esc(name) + '">' + options.map(function (item) {
      return '<button type="button" data-choice="' + item[0] + '" aria-pressed="' + (selected === item[0] ? "true" : "false") + '">' + item[1] + "</button>";
    }).join("") + "</div>";
  }

  function bindChoices(selector, after) {
    document.querySelectorAll(selector).forEach(function (button) {
      button.onclick = function () {
        document.querySelectorAll(selector).forEach(function (item) { item.setAttribute("aria-pressed", "false"); });
        button.setAttribute("aria-pressed", "true");
        if (after) after(button.getAttribute("data-choice"));
      };
    });
  }

  function chosen(selector) {
    var button = document.querySelector(selector + '[aria-pressed="true"]');
    return button ? button.getAttribute("data-choice") : "";
  }

  function lock(form, locked) {
    busy = locked;
    if (!form) return;
    form.querySelectorAll("button, input, select, textarea").forEach(function (node) {
      if (node.type === "submit") node.disabled = locked;
    });
    var submit = form.querySelector('[type="submit"]');
    if (submit) submit.textContent = locked ? "Salvando…" : submit.getAttribute("data-label");
  }

  function finish(node) {
    reveal(node || document.getElementById("plan-title"));
    var help = document.getElementById("plan-help");
    if (help) help.onclick = function () {
      var slot = document.getElementById("plan-help-slot");
      if (slot) slot.hidden = false;
      if (window.IsaAssistant) window.IsaAssistant.place("help");
    };
    if (window.IsaAssistant) window.IsaAssistant.place("quiet");
  }

  function availabilityValues(data) {
    var saved = guideOf(data).availability;
    if (saved) {
      return {
        amount: moneyText(saved.amountCents),
        date: saved.asOf || today(),
        floor: saved.protectedCents ? moneyText(saved.protectedCents) : "",
        reserve: saved.protectedCents ? "sim" : "nao",
        note: "Valor já salvo. Abrir esta tela não altera nada.",
      };
    }
    var draft = loadedDraft || {};
    return {
      amount: draft.amount || "",
      date: draft.date || today(),
      floor: draft.floor || "",
      reserve: draft.reserveChoice || "",
      note: draft.amount || draft.floor || draft.reserveChoice ? "Rascunho nesta tela, ainda não confirmado." : "",
    };
  }

  function renderAvailability(data) {
    var values = availabilityValues(data);
    var root = document.getElementById("plan-root");
    root.innerHTML = frame("availability", "Quanto você tem disponível?", "Informe o dinheiro que você pode usar agora. Não inclua limite do cartão ou cheque especial.",
      (values.note ? '<p class="muted">' + esc(values.note) + "</p>" : "") +
      '<form id="q1" class="stack">' + moneyField("q1-amount", "Dinheiro disponível", values.amount) +
      '<div class="field"><label for="q1-date">Esse valor é de qual dia?</label><input id="q1-date" type="date" value="' + esc(values.date) + '" aria-describedby="q1-date-error"><p id="q1-date-error" class="field-error" role="alert"></p></div>' +
      '<fieldset class="field"><legend>Quer separar uma parte para não gastar?</legend><p>Esse valor já está incluído no dinheiro disponível.</p>' +
      choiceButtons("Reserva", [["nao", "Não"], ["sim", "Sim"]], values.reserve) +
      '<div id="q1-floor-field"' + (values.reserve === "sim" ? "" : " hidden") + ">" + moneyField("q1-floor", "Valor para não gastar", values.floor) + "</div></fieldset>" +
      '<button class="primary" type="submit" data-label="Salvar e continuar">Salvar e continuar</button><button class="secondary" type="button" id="q1-unknown">Ainda não sei</button></form>',
      data, "availability");
    bindChoices("#q1 .plan-choice button", function (choice) {
      document.getElementById("q1-floor-field").hidden = choice !== "sim";
      remember(currentAvailabilityDraft());
    });
    ["q1-amount", "q1-date", "q1-floor"].forEach(function (id) {
      var input = document.getElementById(id);
      if (input) input.oninput = function () { remember(currentAvailabilityDraft()); };
    });
    document.getElementById("q1").onsubmit = saveAvailability;
    document.getElementById("q1-unknown").onclick = function () {
      if (busy) return;
      status(document.getElementById("save-state"), "Salvando…", "saving");
      lock(document.getElementById("q1"), true);
      persistDraft(Object.assign(currentAvailabilityDraft(), { availabilityUnknown: true, continuePastAvailability: false })).then(function () {
        lock(document.getElementById("q1"), false);
        goPlan("#planejar");
      }).catch(function () {
        lock(document.getElementById("q1"), false);
        status(document.getElementById("save-state"), "Não foi possível guardar a pendência. Tente de novo.", "error");
      });
    };
    finish();
  }

  function currentAvailabilityDraft() {
    return {
      amount: document.getElementById("q1-amount").value,
      date: document.getElementById("q1-date").value,
      floor: document.getElementById("q1-floor") ? document.getElementById("q1-floor").value : "",
      reserveChoice: chosen("#q1 .plan-choice button"),
    };
  }

  function saveAvailability(event) {
    event.preventDefault();
    if (busy) return;
    var amountRaw = document.getElementById("q1-amount").value;
    var amountError = moneyMessage(amountRaw);
    markError("q1-amount", amountError);
    var date = document.getElementById("q1-date").value;
    markError("q1-date", date ? "" : "Informe a data.");
    var reserve = chosen("#q1 .plan-choice button");
    var floorRaw = document.getElementById("q1-floor") ? document.getElementById("q1-floor").value : "";
    var floorError = "";
    if (!reserve) floorError = "Diga se quer separar uma parte. Se não quiser, escolha Não.";
    else if (reserve === "sim") floorError = moneyMessage(floorRaw);
    var floorNode = document.getElementById("q1-floor-error");
    if (floorNode) floorNode.textContent = floorError;
    if (amountError || !date || floorError) return;
    var amount = cents(amountRaw);
    var floor = reserve === "sim" ? cents(floorRaw) : 0;
    if (reserve === "sim" && floor < 0) {
      if (floorNode) floorNode.textContent = "A parte separada não pode ser negativa.";
      return;
    }
    if (amount >= 0 && floor > amount) {
      if (floorNode) floorNode.textContent = "A reserva já está dentro do dinheiro disponível e não pode ser maior.";
      return;
    }
    var sent = amountRaw + "|" + date + "|" + reserve + "|" + floorRaw;
    lock(document.getElementById("q1"), true);
    status(document.getElementById("save-state"), "Salvando…", "saving");
    api("PUT", "/api/availability", { amountCents: amount, asOf: date, protectedCents: floor, source: "declarada" }).then(function () {
      var current = document.getElementById("q1-amount").value + "|" + document.getElementById("q1-date").value + "|" + chosen("#q1 .plan-choice button") + "|" + (document.getElementById("q1-floor") ? document.getElementById("q1-floor").value : "");
      if (current !== sent) {
        lock(document.getElementById("q1"), false);
        status(document.getElementById("save-state"), "A gravação anterior foi confirmada, mas você alterou os campos. Salve de novo para guardar esta versão.", "error");
        return persistDraft(currentAvailabilityDraft());
      }
      return persistDraft({ amount: undefined, date: undefined, floor: undefined, reserveChoice: undefined, availabilityUnknown: false, continuePastAvailability: false }).then(function () {
        lock(document.getElementById("q1"), false);
        goPlan("#planejar");
      });
    }).catch(function (error) {
      lock(document.getElementById("q1"), false);
      status(document.getElementById("save-state"), error.message || "Não foi possível salvar. Tente de novo.", "error");
    });
  }

  function renderPending(title, text, actions) {
    var root = document.getElementById("plan-root");
    root.innerHTML = frame(actions.step, title, text,
      '<div class="stack"><button class="primary" type="button" id="plan-fill" data-label="' + esc(actions.fill[1]) + '">' + esc(actions.fill[1]) + '</button>' +
      '<button class="secondary" type="button" id="plan-skip">' + esc(actions.skip[1]) + '</button>' +
      '<a class="quiet plan-back" href="#inicio">Voltar ao início</a></div>', { guide: {} }, actions.gap);
    document.getElementById("plan-fill").onclick = function () { goPlan(actions.fill[0]); };
    document.getElementById("plan-skip").onclick = function () {
      if (busy) return;
      busy = true;
      status(document.getElementById("save-state"), "Salvando…", "saving");
      persistDraft(actions.skip[2]).then(function () {
        busy = false;
        goPlan("#planejar");
      }).catch(function () {
        busy = false;
        status(document.getElementById("save-state"), "Não foi possível guardar a pendência. Tente de novo.", "error");
      });
    };
    finish();
  }

  function renderInflow(data) {
    var existing = (data.inflows || []).filter(function (item) { return item.state === "confirmada" && item.amount_cents != null && item.due_on; })[0];
    var draft = loadedDraft || {};
    var root = document.getElementById("plan-root");
    root.innerHTML = frame("inflow", "Quando você espera receber?", "Informe a próxima entrada. Se ela ainda não estiver certa, marque isso. A categoria não é necessária.",
      (existing ? '<p class="muted">Entrada já salva. Abrir esta tela não cria outra.</p>' : (draft.inflowLabel || draft.inflowAmount ? '<p class="muted">Rascunho nesta tela, ainda não confirmado.</p>' : "")) +
      '<form id="q2" class="stack"><div class="field"><label for="q2-label">O que é?</label><input id="q2-label" value="' + esc(existing ? existing.label : (draft.inflowLabel || "")) + '" aria-describedby="q2-label-error"><p id="q2-label-error" class="field-error" role="alert"></p></div>' +
      moneyField("q2-amount", "Valor", existing ? moneyText(existing.amount_cents) : (draft.inflowAmount || "")) +
      '<div class="field"><label for="q2-date">Data</label><input id="q2-date" type="date" value="' + esc(existing ? existing.due_on : (draft.inflowDate || today())) + '" aria-describedby="q2-date-error"><p id="q2-date-error" class="field-error" role="alert"></p></div>' +
      choiceButtons("Confirmação", [["confirmada", "Já está confirmada"], ["incerta", "Ainda não tenho certeza"]], existing ? existing.state : (draft.inflowState || "confirmada")) +
      '<button class="primary" type="submit" data-label="Salvar e continuar">Salvar e continuar</button><button class="secondary" type="button" id="q2-unknown">Ainda não sei</button></form>',
      data, "inflow");
    ["q2-label", "q2-amount", "q2-date"].forEach(function (id) {
      document.getElementById(id).oninput = function () {
        remember({ inflowLabel: document.getElementById("q2-label").value, inflowAmount: document.getElementById("q2-amount").value, inflowDate: document.getElementById("q2-date").value, inflowState: chosen("#q2 .plan-choice button") });
      };
    });
    bindChoices("#q2 .plan-choice button");
    document.getElementById("q2").onsubmit = function (event) {
      event.preventDefault();
      if (busy) return;
      var label = document.getElementById("q2-label").value.trim();
      var amountRaw = document.getElementById("q2-amount").value;
      var amountError = moneyMessage(amountRaw);
      var date = document.getElementById("q2-date").value;
      markError("q2-label", label ? "" : "Diga o que você espera receber.");
      markError("q2-amount", amountError);
      markError("q2-date", date ? "" : "Informe a data.");
      var state = chosen("#q2 .plan-choice button") || "confirmada";
      if (!label || amountError || !date) return;
      var amount = cents(amountRaw);
      var same = (data.inflows || []).some(function (item) {
        return item.label === label && item.amount_cents === amount && item.due_on === date && item.state === state && (!existing || item.id !== existing.id);
      });
      if (same || (existing && existing.label === label && existing.amount_cents === amount && existing.due_on === date && existing.state === state)) {
        goPlan("#planejar/contas");
        return;
      }
      lock(document.getElementById("q2"), true);
      status(document.getElementById("save-state"), "Salvando…", "saving");
      var payload = { label: label, amountCents: amount, dueOn: date, state: state, origin: "declarada" };
      var request = existing ? api("POST", "/api/inflows/" + existing.id, payload) : api("POST", "/api/inflows", payload);
      request.then(function () {
        return persistDraft({ inflowLabel: undefined, inflowAmount: undefined, inflowDate: undefined, inflowState: undefined, continuePastInflow: true });
      }).then(function () {
        lock(document.getElementById("q2"), false);
        goPlan("#planejar/contas");
      }).catch(function (error) {
        lock(document.getElementById("q2"), false);
        status(document.getElementById("save-state"), error.message || "Não foi possível salvar. Tente de novo.", "error");
      });
    };
    document.getElementById("q2-unknown").onclick = function () {
      if (busy) return;
      if (guideOf(data).inflowUncertain) {
        goPlan("#planejar");
        return;
      }
      lock(document.getElementById("q2"), true);
      status(document.getElementById("save-state"), "Salvando…", "saving");
      var label = document.getElementById("q2-label").value.trim() || "Entrada ainda sem data";
      api("POST", "/api/inflows", { label: label, amountCents: null, dueOn: null, state: "incerta", origin: "declarada" }).then(function () {
        lock(document.getElementById("q2"), false);
        goPlan("#planejar");
      }).catch(function (error) {
        lock(document.getElementById("q2"), false);
        status(document.getElementById("save-state"), error.message || "Não foi possível guardar a pendência. Tente de novo.", "error");
      });
    };
    finish();
  }

  function commitmentList(data) {
    var items = data.commitments || [];
    if (!items.length) return "";
    return '<ul class="plan-list">' + items.map(function (item) {
      var value = item.remaining_cents == null ? "Valor ainda não informado" : brl(item.remaining_cents);
      var when = item.due_on ? showDate(item.due_on) : "Vencimento ainda não informado";
      return "<li><strong>" + esc(item.label) + "</strong> · " + value + " · " + when + "</li>";
    }).join("") + "</ul>";
  }

  function renderCommitments(data) {
    var draft = loadedDraft || {};
    var root = document.getElementById("plan-root");
    root.innerHTML = frame("commitments", "O que precisa pagar?", "Informe cada conta com valor e vencimento. A lista abaixo mostra todas as que já foram guardadas, não só a primeira.",
      commitmentList(data) +
      (draft.commitmentLabel || draft.commitmentAmount ? '<p class="muted">Rascunho nesta tela, ainda não confirmado.</p>' : "") +
      '<form id="q3" class="stack"><div class="field"><label for="q3-label">O que é?</label><input id="q3-label" value="' + esc(draft.commitmentLabel || "") + '" aria-describedby="q3-label-error"><p id="q3-label-error" class="field-error" role="alert"></p></div>' +
      moneyField("q3-amount", "Valor", draft.commitmentAmount || "") +
      '<div class="field"><label for="q3-date">Vencimento</label><input id="q3-date" type="date" value="' + esc(draft.commitmentDate || today()) + '"></div>' +
      '<button class="primary" type="submit" data-label="Guardar esta conta">Guardar esta conta</button>' +
      '<button class="secondary" type="button" id="q3-unknown">Ainda não sei o valor</button>' +
      ((data.commitments || []).length ? "" : '<button class="secondary" type="button" id="q3-none">Não tenho conta a pagar conhecida</button>') +
      ((data.commitments || []).length ? '<button class="secondary" type="button" id="q3-next">Seguir para o planejamento</button>' : "") +
      "</form>", data, "commitments");
    ["q3-label", "q3-amount", "q3-date"].forEach(function (id) {
      document.getElementById(id).oninput = function () {
        remember({ commitmentLabel: document.getElementById("q3-label").value, commitmentAmount: document.getElementById("q3-amount").value, commitmentDate: document.getElementById("q3-date").value });
      };
    });
    document.getElementById("q3").onsubmit = function (event) {
      event.preventDefault();
      if (busy) return;
      var label = document.getElementById("q3-label").value.trim();
      var amountRaw = document.getElementById("q3-amount").value;
      var amountError = moneyMessage(amountRaw);
      var due = document.getElementById("q3-date").value;
      markError("q3-label", label ? "" : "Diga qual é a conta.");
      markError("q3-amount", amountError);
      if (!label || amountError || !due) {
        if (!due) status(document.getElementById("save-state"), "Informe o vencimento.", "error");
        return;
      }
      var amount = cents(amountRaw);
      if ((data.commitments || []).some(function (item) { return item.label === label && item.total_cents === amount && item.due_on === due; })) {
        status(document.getElementById("save-state"), "Esta conta já está na lista.", "error");
        return;
      }
      lock(document.getElementById("q3"), true);
      status(document.getElementById("save-state"), "Salvando…", "saving");
      api("POST", "/api/commitments", { label: label, totalCents: amount, dueOn: due, origin: "declarada" }).then(function () {
        return persistDraft({ commitmentLabel: undefined, commitmentAmount: undefined, commitmentDate: undefined, commitmentUnknown: false, commitmentsDeclaredNone: false });
      }).then(function () {
        lock(document.getElementById("q3"), false);
        goPlan("#planejar/contas");
      }).catch(function (error) {
        lock(document.getElementById("q3"), false);
        status(document.getElementById("save-state"), error.message || "Não foi possível salvar. Tente de novo.", "error");
      });
    };
    document.getElementById("q3-unknown").onclick = function () {
      if (busy) return;
      var label = document.getElementById("q3-label").value.trim();
      if (!label) {
        lock(document.getElementById("q3"), true);
        status(document.getElementById("save-state"), "Salvando…", "saving");
        persistDraft({ commitmentUnknown: true, continuePastCommitments: false }).then(function () {
          lock(document.getElementById("q3"), false);
          goPlan("#planejar");
        }).catch(function () {
          lock(document.getElementById("q3"), false);
          status(document.getElementById("save-state"), "Não foi possível guardar a pendência. Tente de novo.", "error");
        });
        return;
      }
      var due = document.getElementById("q3-date").value || null;
      if ((data.commitments || []).some(function (item) { return item.label === label && item.total_cents == null && item.due_on === due; })) {
        status(document.getElementById("save-state"), "Esta conta já está na lista, ainda sem valor.", "error");
        return;
      }
      lock(document.getElementById("q3"), true);
      status(document.getElementById("save-state"), "Salvando…", "saving");
      api("POST", "/api/commitments", { label: label, totalCents: null, dueOn: due, origin: "declarada" }).then(function () {
        lock(document.getElementById("q3"), false);
        goPlan("#planejar/contas");
      }).catch(function (error) {
        lock(document.getElementById("q3"), false);
        status(document.getElementById("save-state"), error.message || "Não foi possível guardar a pendência. Tente de novo.", "error");
      });
    };
    var none = document.getElementById("q3-none");
    if (none) none.onclick = function () {
      if (busy || (data.commitments || []).length) return;
      lock(document.getElementById("q3"), true);
      status(document.getElementById("save-state"), "Salvando…", "saving");
      persistDraft({ commitmentsDeclaredNone: true, commitmentUnknown: false, continuePastCommitments: true }).then(function () {
        lock(document.getElementById("q3"), false);
        goPlan("#planejar/resumo");
      }).catch(function () {
        lock(document.getElementById("q3"), false);
        status(document.getElementById("save-state"), "Não foi possível guardar a declaração. Tente de novo.", "error");
      });
    };
    var next = document.getElementById("q3-next");
    if (next) next.onclick = function () { goPlan("#planejar/resumo"); };
    finish();
  }

  function summaryRows(data) {
    var guide = guideOf(data);
    var rows = [];
    if (guide.availability) {
      rows.push(["Dinheiro disponível", brl(guide.availability.amountCents) + " em " + showDate(guide.availability.asOf), "#planejar/disponivel"]);
      rows.push(["Reserva incluída nesse valor", guide.availability.protectedCents ? brl(guide.availability.protectedCents) : "Nenhuma", "#planejar/disponivel"]);
    } else rows.push(["Dinheiro disponível", "Ainda não informado", "#planejar/disponivel"]);
    (data.inflows || []).forEach(function (item) {
      var value = item.amount_cents == null ? "Valor ainda não informado" : brl(item.amount_cents);
      var when = item.due_on ? showDate(item.due_on) : "data ainda não informada";
      rows.push([(item.state === "confirmada" ? "Entrada confirmada" : "Entrada incerta") + ": " + item.label, value + " · " + when, "#planejar/entrada"]);
    });
    if (!(data.inflows || []).length) rows.push(["Próxima entrada", "Ainda não informada", "#planejar/entrada"]);
    (data.commitments || []).forEach(function (item) {
      var value = item.remaining_cents == null ? "Valor ainda não informado" : brl(item.remaining_cents);
      var when = item.due_on ? showDate(item.due_on) : "vencimento ainda não informado";
      rows.push([item.label, value + " · " + when, "#planejar/contas"]);
    });
    if (guide.commitmentsDeclaredNone) rows.push(["Contas a pagar", "Você informou que não há conta conhecida.", "#planejar/contas"]);
    else if (!(data.commitments || []).length) rows.push(["Contas a pagar", "Ainda não informadas", "#planejar/contas"]);
    return '<ul class="plan-list">' + rows.map(function (item, index) {
      return "<li><strong>" + esc(item[0]) + "</strong> · " + esc(item[1]) + ' <button type="button" class="quiet" data-edit="' + item[2] + '" id="edit-' + index + '">Editar</button></li>';
    }).join("") + "</ul>";
  }

  function renderSummary(data) {
    var guide = guideOf(data);
    var projection = data.projection || {};
    var incomplete = (guide.gaps || []).length || !projection.complete;
    var root = document.getElementById("plan-root");
    var note = incomplete ? '<p class="note">O planejamento está incompleto. A projeção não inventa o que ainda falta.</p>' : "";
    var calendarHtml = projection.complete ? board(data) : "";
    root.innerHTML = '<div class="plan-journey" id="plan-stage"><a class="quiet plan-back" href="#inicio">Voltar</a>' + progress("") +
      '<div class="plan-card"><h2 id="plan-title" tabindex="-1">O que você informou</h2>' + note + summaryRows(data) + "</div>" +
      '<div id="plan-ai-slot" data-gap="' + esc((guide.gaps || [])[0] || "") + '"></div>' + calendarHtml + "</div>";
    document.querySelectorAll("[data-edit]").forEach(function (button) {
      button.onclick = function () { goPlan(button.getAttribute("data-edit")); };
    });
    if (projection.complete) bindBoard(data);
    reveal(document.getElementById("plan-title"));
    if (window.IsaAssistant) window.IsaAssistant.place(guide.availabilityKnown || (data.commitments || []).length || guide.inflowConfirmed ? "ready" : "quiet", (guide.gaps || [])[0] || "");
  }

  function renderStep(data) {
    var root = document.getElementById("plan-root");
    if (!root) return;
    var guide = guideOf(data);
    var forced = requestedStep();
    var step = forced || guide.step || "availability";
    if (step === "availability-pending" && forced === "availability") step = "availability";
    if (step === "inflow-pending" && forced === "inflow") step = "inflow";
    if (step === "commitments-pending" && forced === "commitments") step = "commitments";
    if (step === "availability") return renderAvailability(data);
    if (step === "availability-pending") {
      return renderPending("O dinheiro disponível ainda não foi informado", "O planejamento fica incompleto sem esse valor. Nada foi transformado em zero.", {
        step: "availability", gap: "availability",
        fill: ["#planejar/disponivel", "Informar agora"],
        skip: ["seguir", { continuePastAvailability: true }],
      });
    }
    if (step === "inflow") return renderInflow(data);
    if (step === "inflow-pending") {
      return renderPending("A próxima entrada ainda não está definida", "Dá para continuar, e o planejamento segue incompleto nessa parte.", {
        step: "inflow", gap: "inflow",
        fill: ["#planejar/entrada", "Informar a entrada"],
        skip: ["seguir", { continuePastInflow: true }],
      });
    }
    if (step === "commitments") return renderCommitments(data);
    if (step === "commitments-pending") {
      return renderPending("As contas a pagar ainda não foram informadas", "Isso é diferente de declarar que não há conta conhecida. O planejamento segue incompleto.", {
        step: "commitments", gap: "commitments",
        fill: ["#planejar/contas", "Informar uma conta"],
        skip: ["seguir", { continuePastCommitments: true }],
      });
    }
    renderSummary(data);
  }

  function open() {
    var root = document.getElementById("plan-root");
    if (!root || (!window.isaPublic && !person())) return;
    var token = ++loadToken;
    if (!root.querySelector("#plan-title")) root.innerHTML = '<p class="muted">Carregando suas informações…</p>';
    api("GET", "/api/home").then(function (data) {
      return api("GET", "/api/drafts/planejar").then(function (draft) {
        return { data: data, draft: draft && draft.body };
      }).catch(function () { return { data: data, draft: null }; });
    }).then(function (loaded) {
      if (token !== loadToken || !document.getElementById("plan-root")) return;
      loadedDraft = loaded.draft && typeof loaded.draft === "object" ? loaded.draft : null;
      renderStep(loaded.data);
    }).catch(function () {
      if (token !== loadToken || !document.getElementById("plan-root")) return;
      root.innerHTML = '<p class="note">Não foi possível carregar suas informações.</p><button class="secondary" type="button" id="plan-retry">Tentar de novo</button>';
      document.getElementById("plan-retry").onclick = open;
    });
  }

  window.IsaPlan = { fillHome: fillHome, open: open };
})();
