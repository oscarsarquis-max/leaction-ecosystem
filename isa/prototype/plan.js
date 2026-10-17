(function () {
  var saveTimer = null;

  function person() {
    return window.isaLabPerson || "";
  }

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

  function status(node, text, ok) {
    if (!node) return;
    node.className = ok ? "oknote" : "note";
    node.textContent = text;
  }

  function remember(body) {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      api("PUT", "/api/drafts/planejar", body).catch(function () {
        var node = document.getElementById("save-state");
        status(node, "Não foi possível salvar. O que você digitou continua nesta tela.", false);
      });
    }, 250);
  }

  function homeHtml(data) {
    var projection = data.projection || {};
    if (!projection.complete) {
      var question = (projection.missing && projection.missing[0]) || "Quanto você tem disponível e em qual data?";
      return '<section class="decision"><p>Para saber se o dinheiro chega, falta uma informação.</p><button class="primary" type="button" id="plan-start">' + question + '</button></section>';
    }
    var upcoming = (data.commitments || []).filter(function (item) { return item.due_on >= projection.reference; }).slice(0, 3);
    var income = projection.next_inflow;
    return '<section class="decision"><h2>O próximo ponto</h2><p>Em ' + showDate(projection.minimum.date) + " o disponível chega a <strong>" + brl(projection.minimum.cents) + "</strong>.</p>" +
      (income ? "<p>Próxima entrada confirmada: " + brl(income.cents) + " em " + showDate(income.on) + ".</p>" : "<p>Não há entrada confirmada no horizonte.</p>") +
      (upcoming.length ? "<p>Compromissos próximos: " + upcoming.map(function (item) { return item.label + " " + brl(item.remaining_cents) + " em " + showDate(item.due_on); }).join("; ") + ".</p>" : "") +
      (projection.floor_gap_cents ? "<p>Para preservar a reserva, faltam " + brl(projection.floor_gap_cents) + " no ponto mais baixo.</p>" : "") +
      '<button class="primary" type="button" id="plan-start">Ver o que muda se um compromisso mudar de data</button>' +
      (data.chosenPlan ? '<p class="oknote">Plano escolhido. O vencimento original dos compromissos não mudou.</p>' : "") +
      '<p class="muted">' + (data.explanation && data.explanation.text ? data.explanation.text : "") + "</p></section>";
  }

  function fillHome() {
    var slot = document.getElementById("plan-home");
    if (!slot || (!window.isaPublic && !person())) return;
    api("GET", "/api/home").then(function (data) {
      if (!document.getElementById("plan-home")) return;
      document.getElementById("plan-home").innerHTML = homeHtml(data);
      var button = document.getElementById("plan-start");
      if (button) button.onclick = function () { location.hash = "#planejar"; };
    }).catch(function () {
      if (document.getElementById("plan-home")) document.getElementById("plan-home").innerHTML = "";
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
      return "<li>" + (event.kind === "entrada" ? "Entrada" : "Saída") + ": " + event.label + " " + brl(event.cents) + "</li>";
    }).join("") : "<li>Sem movimento neste dia.</li>";
    var order = item.order_dependency ? "<p>Há entrada e saída no mesmo dia. Sem horário, a ordem pode mudar se o saldo aguenta.</p>" : "";
    return "<h3>" + showDate(iso) + "</h3><p>Disponível no fim do dia: " + brl(item.cents) + (item.below_zero ? ". Falta dinheiro." : item.below_floor ? ". A reserva protegida foi invadida." : ".") + "</p><ul>" + events + "</ul>" + order;
  }

  function board(data) {
    var projection = data.projection;
    var month = "2026-10";
    var selected = projection.first_insufficiency || projection.minimum.date;
    var preferred = (data.commitments || []).filter(function (item) { return item.remaining_cents === 50000; })[0];
    var options = (data.commitments || []).map(function (item) {
      return '<option value="' + item.id + '"' + (preferred && item.id === preferred.id ? " selected" : "") + ">" + item.label + " · " + showDate(item.due_on) + "</option>";
    }).join("");
    return '<p id="save-state" class="oknote">Salvo neste computador.</p>' +
      '<div class="import-layout"><div><h2>Outubro</h2><p class="legend"><span class="swatch short"></span> Falta <span class="swatch in"></span> Entra <span class="swatch out"></span> Sai</p>' +
      calendar(projection.days, month) + '<div id="day-detail">' + dayDetail(projection.days, selected) + "</div>" +
      '<h2>Novembro</h2>' + calendar(projection.days, "2026-11") + "</div><div class=\"decision\">" +
      "<h2>Comparar uma alternativa</h2><p>Isto não paga, não pede crédito e não muda o vencimento.</p>" +
      '<form id="alt-form" class="stack"><label>Qual compromisso?<select id="alt-commitment">' + options + '</select></label>' +
      '<label>Nova data<input id="alt-date" type="date" value="2026-10-26"></label>' +
      '<button class="primary" type="submit">Comparar</button></form><div id="alt-result"></div>' +
      '<form id="spend-form" class="stack"><h2>Posso gastar?</h2><label>Valor<input id="spend-amount" placeholder="50,00"></label>' +
      '<label>Categoria, se quiser<input id="spend-category" placeholder="Lazer"></label>' +
      '<label>Data<input id="spend-date" type="date" value="2026-10-16"></label><button class="secondary" type="submit">Ver o efeito</button></form><div id="spend-result"></div>' +
      '<form id="more-form" class="stack"><h2>Outro compromisso</h2><label>O que é?<input id="more-label"></label><label>Quanto?<input id="more-amount" placeholder="200,00"></label><label>Vence quando?<input id="more-date" type="date"></label><button class="secondary" type="submit">Guardar</button></form>' +
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
      var node = document.getElementById("save-state");
      status(node, "Salvando", true);
      api("POST", "/api/scenarios", {
        name: "Alternativa",
        reference: "2026-10-16",
        changes: [{ commitmentId: document.getElementById("alt-commitment").value, dueOn: document.getElementById("alt-date").value }],
        label: "somente a data escolhida mudar",
      }).then(function (scenario) {
        status(node, "Salvo neste computador.", true);
        var result = JSON.parse(scenario.result_json);
        var box = document.getElementById("alt-result");
        box.innerHTML = "<p>Agora o ponto mais baixo é " + brl(data.projection.minimum.cents) + " em " + showDate(data.projection.minimum.date) + ".</p><p>Na alternativa, o ponto mais baixo fica " + brl(result.minimum.cents) + " e outubro termina em " + brl(result.october_end_cents) + ".</p><p>" + scenario.note + "</p>" +
          '<button class="primary" type="button" id="choose-plan">Guardar como plano escolhido</button>';
        document.getElementById("choose-plan").onclick = function () {
          status(node, "Salvando", true);
          api("POST", "/api/scenarios/" + scenario.id + "/choose", {}).then(function () {
            status(node, "Salvo neste computador. Plano escolhido. Nada foi pago.", true);
          }).catch(function () { status(node, "Não foi possível salvar. Tente de novo.", false); });
        };
      }).catch(function () { status(node, "Não foi possível salvar. Tente de novo.", false); });
    };
    var spend = document.getElementById("spend-form");
    if (spend) spend.onsubmit = function (event) {
      event.preventDefault();
      var amount = cents(document.getElementById("spend-amount").value);
      var node = document.getElementById("save-state");
      if (amount === null) {
        status(node, "Falta o valor. Isso não vira zero.", false);
        return;
      }
      api("POST", "/api/spend", {
        amountCents: amount,
        on: document.getElementById("spend-date").value,
        category: document.getElementById("spend-category").value,
        reference: "2026-10-16",
      }).then(function (payload) {
        document.getElementById("spend-result").textContent = payload.explanation.text;
      }).catch(function (error) { status(node, error.message || "Não foi possível salvar.", false); });
    };
    var more = document.getElementById("more-form");
    if (more) more.onsubmit = function (event) {
      event.preventDefault();
      var amount = cents(document.getElementById("more-amount").value);
      if (!document.getElementById("more-label").value.trim() || amount === null) return;
      api("POST", "/api/commitments", { label: document.getElementById("more-label").value, totalCents: amount, dueOn: document.getElementById("more-date").value, origin: "declarada" }).then(open);
    };
    var demo = document.getElementById("load-october");
    if (demo) demo.onclick = function () {
      api("POST", "/api/fixtures/october", {}).then(open).catch(function () {
        status(document.getElementById("save-state"), "Não foi possível salvar. Tente de novo.", false);
      });
    };
  }

  function question(title, body) {
    return '<p id="save-state" class="muted">Salvando</p><h2>' + title + '</h2>' + body;
  }

  function open() {
    var root = document.getElementById("plan-root");
    if (!root || (!window.isaPublic && !person())) return;
    api("GET", "/api/home").then(function (data) {
      return api("GET", "/api/drafts/planejar").then(function (draft) {
        return { data: data, draft: draft && draft.body }; 
      }).catch(function () { return { data: data, draft: null }; });
    }).then(function (loaded) {
      renderStep(loaded.data, loaded.draft);
    }).catch(function () {
      root.innerHTML = '<p class="note">Não foi possível salvar nem ler o planejamento neste computador. Tente de novo.</p>';
    });
  }

  function renderStep(data, draft) {
    var root = document.getElementById("plan-root");
    if (!root) return;
    var projection = data.projection || {};
    var missingBase = !projection.complete && (projection.missing || []).join(" ").indexOf("disponível") >= 0;
    var confirmed = (data.inflows || []).some(function (item) { return item.state === "confirmada"; });
    if (missingBase) {
      root.innerHTML = question("Quanto você tem disponível e em qual data?",
        '<form id="q1" class="stack"><label>Valor disponível<input id="q1-amount" placeholder="600,00" value="' + ((draft && draft.amount) || "") + '"></label>' +
        '<label>Data<input id="q1-date" type="date" value="' + ((draft && draft.date) || "2026-10-16") + '"></label>' +
        '<label>Quanto disso você quer proteger?<input id="q1-floor" placeholder="100,00" value="' + ((draft && draft.floor) || "") + '"></label>' +
        '<button class="primary" type="submit">Continuar</button><button class="secondary" type="button" id="q1-unknown">Ainda não sei</button></form>');
      document.getElementById("q1").onsubmit = function (event) {
        event.preventDefault();
        var amount = cents(document.getElementById("q1-amount").value);
        var floor = cents(document.getElementById("q1-floor").value);
        if (amount === null) {
          status(document.getElementById("save-state"), "Falta o valor. Isso não vira zero.", false);
          return;
        }
        status(document.getElementById("save-state"), "Salvando", true);
        api("PUT", "/api/availability", { amountCents: amount, asOf: document.getElementById("q1-date").value, protectedCents: floor || 0, source: "declarada" })
          .then(function () { status(document.getElementById("save-state"), "Salvo neste computador.", true); open(); })
          .catch(function (error) { status(document.getElementById("save-state"), error.message || "Não foi possível salvar.", false); });
      };
      ["q1-amount", "q1-date", "q1-floor"].forEach(function (id) {
        document.getElementById(id).oninput = function () {
          remember({ amount: document.getElementById("q1-amount").value, date: document.getElementById("q1-date").value, floor: document.getElementById("q1-floor").value });
        };
      });
      document.getElementById("q1-unknown").onclick = function () {
        remember({ unknown: true });
        status(document.getElementById("save-state"), "Salvo como pendência. Sem esse valor a projeção fica parcial.", true);
      };
      return;
    }
    if (!confirmed) {
      root.innerHTML = question("Quando espera receber novamente e quanto?",
        '<form id="q2" class="stack"><label>O que é?<input id="q2-label" placeholder="Pagamento"></label><label>Quanto?<input id="q2-amount" placeholder="1.200,00"></label><label>Quando?<input id="q2-date" type="date" value="2026-10-25"></label>' +
        '<button class="primary" type="submit">Continuar</button><button class="secondary" type="button" id="q2-unknown">Ainda não sei</button></form>');
      document.getElementById("q2").onsubmit = function (event) {
        event.preventDefault();
        var amount = cents(document.getElementById("q2-amount").value);
        if (amount === null) {
          status(document.getElementById("save-state"), "Falta o valor. Isso não vira zero.", false);
          return;
        }
        api("POST", "/api/inflows", { label: document.getElementById("q2-label").value || "Entrada", amountCents: amount, dueOn: document.getElementById("q2-date").value, state: "confirmada", origin: "declarada" }).then(open);
      };
      document.getElementById("q2-unknown").onclick = function () {
        api("POST", "/api/inflows", { label: "Entrada ainda sem data", amountCents: null, dueOn: null, state: "incerta", origin: "declarada" }).then(open);
      };
      return;
    }
    if (!data.commitments.length) {
      root.innerHTML = question("O que precisa pagar até lá?",
        '<form id="q3" class="stack"><label>O que é?<input id="q3-label" placeholder="Aluguel"></label><label>Quanto?<input id="q3-amount" placeholder="500,00"></label><label>Vence quando?<input id="q3-date" type="date" value="2026-10-20"></label>' +
        '<button class="primary" type="submit">Guardar este compromisso</button><button class="secondary" type="button" id="q3-unknown">Ainda não sei o valor</button></form>');
      document.getElementById("q3").onsubmit = function (event) {
        event.preventDefault();
        var amount = cents(document.getElementById("q3-amount").value);
        if (!document.getElementById("q3-label").value.trim() || amount === null) {
          status(document.getElementById("save-state"), "Falta o nome ou o valor. Isso não vira zero.", false);
          return;
        }
        api("POST", "/api/commitments", { label: document.getElementById("q3-label").value, totalCents: amount, dueOn: document.getElementById("q3-date").value, origin: "declarada" }).then(open);
      };
      document.getElementById("q3-unknown").onclick = function () {
        var label = document.getElementById("q3-label").value.trim() || "Compromisso";
        api("POST", "/api/commitments", { label: label, totalCents: null, dueOn: document.getElementById("q3-date").value || null, origin: "declarada" }).then(open);
      };
      return;
    }
    if (!projection.complete) {
      root.innerHTML = '<p class="note">' + projection.missing[0] + '</p><button class="secondary" type="button" id="plan-reload">Atualizar</button>';
      document.getElementById("plan-reload").onclick = open;
      return;
    }
    root.innerHTML = board(data);
    bindBoard(data);
  }

  window.IsaPlan = { fillHome: fillHome, open: open };
})();
