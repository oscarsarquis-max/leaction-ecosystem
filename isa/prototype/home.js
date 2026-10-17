(function () {
  var last = null;
  var loadToken = 0;
  var cursorMonth = "";
  function dayKey() { return "isa-home-day-" + (window.isaLabPerson || "conta"); }
  var selected = "";

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function brl(cents) {
    if (cents == null || cents === "") return "";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(cents) / 100);
  }

  function showDate(iso) {
    if (!iso) return "";
    var parts = String(iso).split("-");
    if (parts.length !== 3) return String(iso);
    return parts[2] + "/" + parts[1] + "/" + parts[0];
  }

  function api(method, path, body) {
    var headers = { "Content-Type": "application/json" };
    if (!window.isaPublic && window.isaLabPerson) headers["X-ISA-Lab-Person"] = window.isaLabPerson;
    return fetch(path, {
      method: method,
      credentials: "include",
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = text ? JSON.parse(text) : {};
        if (!response.ok) throw new Error(data.error || "Não foi possível consultar agora.");
        return data;
      });
    });
  }

  function gapHref(gap) {
    if (gap === "inflow") return "#planejar/entrada/voltar";
    if (gap === "commitments" || gap === "commitment-values") return "#planejar/contas/voltar";
    return "#planejar/disponivel/voltar";
  }

  function gapName(gap) {
    return {
      availability: "quanto você tem disponível",
      inflow: "quando você recebe",
      commitments: "as contas a pagar",
      "commitment-values": "valor ou vencimento de alguma conta",
    }[gap] || "uma informação";
  }

  function periodText(period) {
    if (!period) return "";
    if (period.basis === "ate-entrada") return "Até a próxima entrada, em " + showDate(period.until) + ".";
    if (period.basis === "ate-horizonte") return "Até " + showDate(period.until) + ". A próxima entrada, em " + showDate(period.inflowOn) + ", fica depois deste cálculo.";
    return "Próximos 30 dias, até " + showDate(period.until) + ". Sem entrada confirmada neste horizonte.";
  }

  function situationText(overview) {
    var state = overview.situation || {};
    if (state.kind === "shortfall") {
      var extra = state.minimum ? " O menor valor no período é " + brl(state.minimum.cents) + " em " + showDate(state.minimum.on) + "." : "";
      return "Faltam " + brl(state.cents) + " em " + showDate(state.on) + " (" + state.when + ") para os compromissos informados." + extra;
    }
    if (state.kind === "reserve") return "As contas cabem, mas você precisará usar " + brl(state.cents) + " da parte protegida em " + showDate(state.on) + " (" + state.when + ").";
    if (state.kind === "covers") return "Os compromissos informados cabem até " + showDate(state.until) + ".";
    var gap = (state.gaps || [])[0];
    return gap ? "Ainda falta " + gapName(gap) + " para calcular." : "Ainda falta informação para calcular.";
  }

  function situationAction(overview) {
    var state = overview.situation || {};
    if (state.kind === "shortfall") return ["Comparar alternativas", "#planejar/resumo"];
    if (state.kind === "reserve") return ["Conferir contas", "#planejar/contas/voltar"];
    if (state.kind === "covers") return ["Avaliar um gasto", "#planejar/resumo"];
    return ["Completar informação", gapHref((state.gaps || [])[0])];
  }

  function moneyCard(title, value, detail, action, href) {
    return '<article class="money-card"><h2>' + esc(title) + "</h2><p class=\"money-value\">" + value + "</p><p>" + detail + '</p><a class="secondary" href="' + href + '">' + esc(action) + "</a></article>";
  }

  function availableCard(overview) {
    var informed = overview.informed;
    if (!informed) return moneyCard("Quanto tenho?", "Informe quanto tem disponível", "O valor informado fica com a data e a origem. A parte protegida entra dentro dele.", "Informe quanto tem disponível", "#planejar/disponivel/voltar");
    var protectedText = informed.protectedCents ? " Inclui " + brl(informed.protectedCents) + " que você pediu para não gastar." : " Nenhuma parte protegida dentro desse valor.";
    var projected = overview.projected ? "<p>Projeção para " + showDate(overview.projected.on) + ": " + brl(overview.projected.cents) + ". Não é o valor informado.</p>" : "";
    return '<article class="money-card"><h2>Quanto tenho?</h2><p class="money-value">' + brl(informed.cents) + "</p><p>Disponível informado em " + showDate(informed.on) + "." + protectedText + "</p>" + projected + '<a class="secondary" href="#planejar/disponivel/voltar">Conferir o valor</a></article>';
  }

  function payableCard(overview) {
    var payable = overview.payables || {};
    var detail = periodText(overview.period) + " " + esc(payable.coverage || "Compromissos do planejamento") + ".";
    if (!payable.count && !payable.pendingCount) return moneyCard("Quanto falta pagar?", "Nenhuma conta informada", detail, "Informar contas", "#planejar/contas/voltar");
    if (!payable.count) return moneyCard("Quanto falta pagar?", payable.pendingCount + " sem valor ou data", detail + " A soma fica de fora enquanto o valor não existe.", "Completar", "#planejar/contas/voltar");
    var overdue = payable.overdueCount ? " " + payable.overdueCount + " vencida" + (payable.overdueCount > 1 ? "s" : "") + ", já incluída" + (payable.overdueCount > 1 ? "s" : "") + " nesse total (" + brl(payable.overdueCents) + ")." : "";
    var pending = payable.pendingCount ? " Há " + payable.pendingCount + " sem valor ou data, fora desta soma." : "";
    return moneyCard("Quanto falta pagar?", brl(payable.cents), detail + " " + payable.count + " com valor." + overdue + pending, payable.pendingCount ? "Completar" : "Conferir contas", "#planejar/contas/voltar");
  }

  function inflowCard(overview) {
    var next = overview.nextInflow;
    var uncertain = overview.uncertainInflow;
    if (next) {
      var extra = uncertain ? " Há também uma entrada incerta, que não sustenta esta conclusão." : "";
      return moneyCard("Quando recebo?", brl(next.cents), esc(next.label) + " em " + showDate(next.on) + " (" + esc(next.when) + "). Confirmada." + extra, "Conferir a entrada", "#planejar/entrada/voltar");
    }
    if (uncertain) return moneyCard("Quando recebo?", uncertain.cents == null ? "Entrada incerta" : brl(uncertain.cents), esc(uncertain.label) + (uncertain.on ? " em " + showDate(uncertain.on) + " (" + esc(uncertain.when) + ")" : "") + ". Incerta: não entra como dinheiro garantido.", "Informe sua próxima entrada", "#planejar/entrada/voltar");
    return moneyCard("Quando recebo?", "Informe sua próxima entrada", "Sem uma entrada confirmada, o período usado é o horizonte explícito.", "Informe sua próxima entrada", "#planejar/entrada/voltar");
  }

  function marginText(overview) {
    var margin = overview.margin || {};
    if (!margin.complete || margin.cents == null) return "Quanto cabe gastar: ainda não calculado.";
    if (margin.cents <= 0) return "Quanto cabe gastar: não há margem livre de " + showDate(margin.from) + " até " + showDate(margin.until) + ", depois dos compromissos e da reserva.";
    return "Quanto cabe gastar: " + brl(margin.cents) + " de " + showDate(margin.from) + " até " + showDate(margin.until) + ", depois dos compromissos e da reserva.";
  }

  function chart(overview) {
    var series = overview.series;
    if (!series || !series.length) return '<section class="money-chart"><h2>Evolução</h2><p>Ainda não há trajetória calculada. O gráfico aparece quando o disponível e os compromissos tiverem valor e data.</p></section>';
    var values = series.map(function (item) { return item.cents; });
    var floor = overview.protectedCents || 0;
    var min = Math.min.apply(null, values.concat([0, floor]));
    var max = Math.max.apply(null, values.concat([0, floor]));
    var span = max - min || 1;
    var width = 640;
    var height = 180;
    var pad = 18;
    function y(cents) { return pad + ((max - cents) * (height - pad * 2)) / span; }
    var points = series.map(function (item, index) {
      var x = pad + (index * (width - pad * 2)) / Math.max(series.length - 1, 1);
      return x.toFixed(1) + "," + y(item.cents).toFixed(1);
    }).join(" ");
    var critical = series.filter(function (item) { return item.below_zero; })[0];
    var dot = "";
    if (critical) {
      var index = series.indexOf(critical);
      var x = pad + (index * (width - pad * 2)) / Math.max(series.length - 1, 1);
      dot = '<circle cx="' + x.toFixed(1) + '" cy="' + y(critical.cents).toFixed(1) + '" r="5" fill="#68460f"><title>Primeiro ponto em que falta dinheiro, ' + esc(showDate(critical.date)) + "</title></circle>";
    }
    var lowest = series.slice().sort(function (a, b) { return a.cents - b.cents || a.date.localeCompare(b.date); })[0];
    return '<section class="money-chart"><h2>Evolução</h2><p class="muted">Projeção diária. A linha tracejada é zero. A linha da reserva mostra a parte protegida.</p>' +
      '<svg viewBox="0 0 ' + width + " " + height + '" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">Trajetória do disponível</title><desc id="chart-desc">De ' + esc(brl(series[0].cents)) + " em " + esc(showDate(series[0].date)) + " até " + esc(brl(series[series.length - 1].cents)) + " em " + esc(showDate(series[series.length - 1].date)) + ". Menor valor " + esc(brl(lowest.cents)) + " em " + esc(showDate(lowest.date)) + ".</desc>" +
      '<line x1="' + pad + '" y1="' + y(0).toFixed(1) + '" x2="' + (width - pad) + '" y2="' + y(0).toFixed(1) + '" stroke="#514c5c" stroke-dasharray="4 4"/>' +
      (floor ? '<line x1="' + pad + '" y1="' + y(floor).toFixed(1) + '" x2="' + (width - pad) + '" y2="' + y(floor).toFixed(1) + '" stroke="#3a3168" stroke-dasharray="2 3"/>' : "") +
      '<polyline fill="none" stroke="#173e64" stroke-width="2" points="' + points + '"/>' + dot + "</svg>" +
      "<p>Leitura: começa em " + brl(series[0].cents) + " em " + showDate(series[0].date) + " e termina em " + brl(series[series.length - 1].cents) + " em " + showDate(series[series.length - 1].date) + ". O menor valor é " + brl(lowest.cents) + " em " + showDate(lowest.date) + "." +
      (critical ? " O primeiro ponto sem dinheiro é " + showDate(critical.date) + ", com " + brl(critical.cents) + "." : "") + "</p></section>";
  }

  function events(data) {
    var list = [];
    (data.commitments || []).forEach(function (item) {
      if (!item.remaining_cents) return;
      list.push({ id: item.id, on: item.due_on, kind: "saida", label: item.label, cents: item.remaining_cents, state: item.due_on ? "conta" : "sem data", href: "#planejar/contas/voltar" });
    });
    (data.inflows || []).forEach(function (item) {
      list.push({ id: item.id, on: item.due_on, kind: "entrada", label: item.label, cents: item.amount_cents, state: item.state === "confirmada" ? "confirmada" : "incerta", href: "#planejar/entrada/voltar" });
    });
    return list;
  }

  function monthShift(month, delta) {
    var parts = month.split("-").map(Number);
    var date = new Date(Date.UTC(parts[0], parts[1] - 1 + delta, 1));
    return date.getUTCFullYear() + "-" + String(date.getUTCMonth() + 1).padStart(2, "0");
  }

  function calendar(data, overview) {
    var reference = overview.reference;
    if (!cursorMonth) cursorMonth = reference.slice(0, 7);
    var all = events(data);
    var dated = all.filter(function (item) { return item.on; });
    var undated = all.filter(function (item) { return !item.on; });
    var parts = cursorMonth.split("-").map(Number);
    var first = new Date(Date.UTC(parts[0], parts[1] - 1, 1));
    var days = new Date(Date.UTC(parts[0], parts[1], 0)).getUTCDate();
    var lead = first.getUTCDay();
    var cells = "";
    var index;
    for (index = 0; index < lead; index += 1) cells += '<span class="cal-empty"></span>';
    for (index = 1; index <= days; index += 1) {
      var iso = cursorMonth + "-" + String(index).padStart(2, "0");
      var dayEvents = dated.filter(function (item) { return item.on === iso; });
      var inn = dayEvents.filter(function (item) { return item.kind === "entrada"; });
      var out = dayEvents.filter(function (item) { return item.kind === "saida"; });
      var uncertain = dayEvents.some(function (item) { return item.state === "incerta"; });
      var overdue = iso < reference && out.length;
      var marks = "";
      if (inn.length) marks += '<span class="mark in">Entra ' + inn.length + "</span>";
      if (out.length) marks += '<span class="mark out">Sai ' + out.length + "</span>";
      if (uncertain || overdue) marks += '<span class="mark attention">Alerta</span>';
      var described = dayEvents.map(function (item) { return item.label + " " + (item.cents == null ? "sem valor" : brl(item.cents)); }).join(", ");
      cells += '<button type="button" class="cal-day' + (iso === reference ? " is-today" : "") + (iso === selected ? " is-selected" : "") + '" data-day="' + iso + '" aria-pressed="' + (iso === selected ? "true" : "false") + '" aria-label="' + esc(index + (described ? ". " + described : ". Nada informado")) + '"><strong>' + index + "</strong>" + marks + "</button>";
    }
    var outside = dated.filter(function (item) { return item.on < reference && item.on.slice(0, 7) !== cursorMonth && item.kind === "saida"; });
    var chosen = dated.filter(function (item) { return item.on === selected; });
    var names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
    return '<section class="money-calendar"><h2>Próximos dias</h2><div class="cal-nav"><button type="button" id="cal-prev">Mês anterior</button><strong>' + names[parts[1] - 1] + " de " + parts[0] + '</strong><button type="button" id="cal-next">Próximo mês</button></div>' +
      '<div class="legend"><span class="mark in">Entra</span><span class="mark out">Sai</span><span class="mark attention">Alerta</span></div>' +
      '<div class="cal-grid" role="grid" aria-label="Calendário de compromissos"><span>D</span><span>S</span><span>T</span><span>Q</span><span>Q</span><span>S</span><span>S</span>' + cells + "</div>" +
      '<div id="day-list">' + (selected ? dayList(chosen, selected) : '<p class="muted">Escolha um dia para ver o que acontece nele.</p>') + "</div>" +
      (undated.length ? "<h3>Sem data</h3><ul>" + undated.map(itemLine).join("") + "</ul>" : "") +
      (outside.length ? "<h3>Vencidos fora deste mês</h3><ul>" + outside.map(itemLine).join("") + "</ul>" : "") +
      "</section>";
  }

  function itemLine(item) {
    var value = item.cents == null ? "Valor ainda não informado" : brl(item.cents);
    return "<li><a href=\"" + item.href + "\">" + esc(item.label) + "</a> · " + value + " · " + esc(item.state) + (item.on ? " · " + showDate(item.on) : "") + "</li>";
  }

  function dayList(items, iso) {
    if (!items.length) return "<p>Nada informado em " + showDate(iso) + ".</p>";
    return "<h3>" + showDate(iso) + "</h3><ul>" + items.map(itemLine).join("") + "</ul>";
  }

  function insightCard(item, compact) {
    var title = item.title;
    var money = "";
    if (item.estimate && item.estimate.status === "unknown") money = "<p>" + esc(item.estimate.text) + "</p>";
    else if (item.estimate && item.estimate.status === "estimated") {
      var parts = (item.estimate.components || []).map(function (part) { return esc(part.name) + " " + brl(part.cents); }).join(", ");
      title = "Se pagar " + (item.label || "este compromisso") + " em " + showDate(item.on) + ", os encargos estimados serão " + brl(item.cents) + "; total estimado " + brl(item.totalCents) + ".";
      money = "<p>" + (parts ? parts + ". " : "") + esc(item.estimate.text) + "</p>";
    } else if (item.estimate && item.estimate.status === "partial") money = "<p>Estimativa parcial: " + brl(item.cents) + ". Ainda não é o total dos encargos. " + esc(item.estimate.text) + "</p>";
    else if (item.cents != null) money = "<p>" + brl(item.cents) + (item.on ? " · " + showDate(item.on) : "") + "</p>";
    else if (item.count) money = "<p>" + item.count + " pendência" + (item.count > 1 ? "s" : "") + "</p>";
    return '<article class="insight ' + esc(item.tone || "attention") + (compact ? " compact" : "") + '"><h3>' + esc(title) + "</h3>" + money +
      '<a class="secondary" href="' + esc(item.href || "#inicio") + '">' + esc(item.action || "Ver") + '</a><button type="button" class="quiet" data-dismiss="' + esc(item.id) + '">Dispensar por hoje</button></article>';
  }

  function reading(overview) {
    var saved = overview.reading;
    var note = "";
    if (saved && saved.explanation) {
      note = '<p class="muted">Leitura de ' + showDate(saved.day) + (saved.stale ? ", desatualizada para os dados de agora" : "") + ": " + esc(saved.explanation) + "</p>";
    }
    return '<section class="money-help"><h2>Ajuda da ISA</h2>' + note +
      '<button type="button" class="secondary" id="ask-reading">Pedir a leitura de hoje</button><p id="reading-note" class="muted"></p>' +
      '<a class="secondary" href="#planejar/resumo">Avaliar um gasto</a></section>';
  }

  function draw(data, warning) {
    var slot = document.getElementById("money-home");
    if (!slot) return;
    var overview = data.overview || {};
    var action = situationAction(overview);
    var items = overview.insights || [];
    var first = items[0];
    var rest = items.slice(1);
    slot.innerHTML =
      (warning ? '<p class="note" role="alert">' + esc(warning) + '</p><button type="button" class="secondary" id="money-retry">Tentar de novo</button>' : "") +
      '<p class="muted">Data de referência ' + showDate(overview.reference) + ". " + periodText(overview.period) + "</p>" +
      '<div class="money-layout"><div class="money-main">' +
      '<div class="money-cards">' + availableCard(overview) + payableCard(overview) + inflowCard(overview) + "</div>" +
      '<section class="money-situation"><h2>O dinheiro chega?</h2><p class="situation-line">' + situationText(overview) + "</p><p>" + marginText(overview) + '</p><a class="primary" href="' + action[1] + '">' + esc(action[0]) + "</a>" +
      (first ? insightCard(first, false) : '<p class="muted">Nada de urgente hoje.</p>') +
      "</section>" + chart(overview) + "</div><aside class=\"money-side\">" +
      calendar(data, overview) +
      (rest.length ? rest.map(function (item) { return insightCard(item, true); }).join("") : "") +
      reading(overview) + "</aside></div>";
    bind(data);
  }

  function bind(data) {
    var retry = document.getElementById("money-retry");
    if (retry) retry.onclick = open;
    var previous = document.getElementById("cal-prev");
    var next = document.getElementById("cal-next");
    if (previous) previous.onclick = function () { cursorMonth = monthShift(cursorMonth, -1); draw(data, ""); };
    if (next) next.onclick = function () { cursorMonth = monthShift(cursorMonth, 1); draw(data, ""); };
    Array.prototype.forEach.call(document.querySelectorAll(".cal-day"), function (button) {
      button.onclick = function () {
        selected = button.getAttribute("data-day");
        sessionStorage.setItem(dayKey(), selected);
        draw(data, "");
      };
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-dismiss]"), function (button) {
      button.onclick = function () {
        button.disabled = true;
        api("POST", "/api/insights/dismiss", { id: button.getAttribute("data-dismiss") }).then(open).catch(function () {
          button.disabled = false;
        });
      };
    });
    var ask = document.getElementById("ask-reading");
    if (ask) ask.onclick = function () {
      ask.disabled = true;
      api("POST", "/api/insights/today", {}).then(function (job) {
        var note = document.getElementById("reading-note");
        if (note) note.textContent = job.message || (job.status === "unavailable" ? "A leitura por IA está indisponível. Os números continuam os calculados pela ISA." : "A leitura foi registrada. Os números desta tela não dependem dela.");
        ask.disabled = false;
      }).catch(function (error) {
        var note = document.getElementById("reading-note");
        if (note) note.textContent = error.message || "Não foi possível pedir a leitura.";
        ask.disabled = false;
      });
    };
  }

  function open() {
    var slot = document.getElementById("money-home");
    if (!slot) return;
    var token = ++loadToken;
    selected = sessionStorage.getItem(dayKey()) || "";
    if (!last) slot.innerHTML = '<p class="muted">Carregando suas informações…</p>';
    api("GET", "/api/home").then(function (data) {
      if (token !== loadToken || !document.getElementById("money-home")) return;
      last = data;
      draw(data, "");
    }).catch(function () {
      if (token !== loadToken || !document.getElementById("money-home")) return;
      if (last) draw(last, "Estas informações não foram atualizadas.");
      else {
        document.getElementById("money-home").innerHTML = '<p class="note">Não foi possível carregar suas informações. Nenhum valor foi gravado.</p><button type="button" class="secondary" id="money-retry">Tentar de novo</button>';
        document.getElementById("money-retry").onclick = open;
      }
    });
  }

  window.IsaHome = { open: open };
})();
