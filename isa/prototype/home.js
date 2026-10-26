(function () {
  var lastByKey = {};
  var readingAsked = {};
  var loadToken = 0;
  var cursorMonth = "";
  function identity() { return window.isaOwnerId || ""; }
  function validMonth(value) {
    if (typeof value !== "string" || !/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) return false;
    var year = Number(value.slice(0, 4));
    return year >= 2000 && year <= 2100;
  }
  function currentMonth() { return validMonth(cursorMonth) ? cursorMonth : ""; }
  function cacheKeyFor(month) {
    return identity() + "|" + (window.isaAccountContext || "all") + "|" + (window.isaHomeCurrency || "") + "|" + (validMonth(month) ? month : "atual");
  }
  function dayKey() { return "isa-home-day-" + identity() + "-" + (window.isaAccountContext || "all"); }
  var selected = "";

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function money(cents, currency) {
    if (cents == null || cents === "") return "";
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: currency || "BRL" }).format(Number(cents) / 100);
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
    if (window.isaAccountContext) headers["X-ISA-Account"] = window.isaAccountContext;
    return fetch(path, {
      method: method,
      credentials: "include",
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        try { data = text ? JSON.parse(text) : {}; }
        catch (err) {
          var broken = new Error("A resposta não veio em um formato utilizável.");
          broken.status = response.status;
          broken.kind = "contract";
          throw broken;
        }
        if (!response.ok) {
          var error = new Error(data.error || "Não foi possível consultar agora.");
          error.status = response.status;
          throw error;
        }
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

  function shortWhen(iso) {
    if (!iso) return "";
    var parts = String(iso).split("-");
    var months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
    return Number(parts[2]) + " " + months[Number(parts[1]) - 1];
  }

  function periodLine(period) {
    if (!period) return "";
    var until = shortWhen(period.until);
    if (period.basis === "ate-entrada") return "Até a próxima entrada · " + until;
    if (period.basis === "ate-horizonte") return "Até " + until + " · a entrada seguinte fica fora deste cálculo";
    return "Próximos 30 dias · até " + until;
  }

  function how(text) {
    return '<details class="money-how"><summary>Como este valor é calculado</summary><p>' + text + "</p></details>";
  }

  function situationText(overview) {
    var state = overview.situation || {};
    if (state.kind === "shortfall") {
      var extra = state.minimum ? " O menor valor no período é " + brl(state.minimum.cents) + " em " + showDate(state.minimum.on) + "." : "";
      return "Faltam " + brl(state.cents) + " em " + showDate(state.on) + " (" + state.when + ") para os compromissos informados." + extra;
    }
    if (state.kind === "reserve") return "As contas cabem, mas você precisará usar " + brl(state.cents) + " da parte protegida em " + showDate(state.on) + " (" + state.when + ").";
    if (state.kind === "covers") return "Os compromissos informados cabem até " + showDate(state.until) + "." + (state.outsideText ? " " + state.outsideText : "");
    if (state.kind === "partial") return state.text || "Esta visão não cobre toda a vida financeira.";
    if ((state.gaps || [])[0] === "availability") return "Informe seu disponível para calcular se o dinheiro chega.";
    var gap = (state.gaps || [])[0];
    return gap ? "Ainda falta " + gapName(gap) + " para calcular." : "Ainda falta informação para calcular.";
  }

  function situationAction(overview) {
    var state = overview.situation || {};
    if (state.kind === "shortfall") return ["Comparar alternativas", "#planejar/resumo"];
    if (state.kind === "reserve") return ["Conferir contas", "#planejar/contas/voltar"];
    if (state.kind === "covers") return ["Avaliar um gasto", "#planejar/resumo"];
    var gap = (state.gaps || [])[0];
    if (gap === "inflow") return ["Informar entrada", gapHref(gap)];
    if (gap === "commitments" || gap === "commitment-values") return ["Informar contas", gapHref(gap)];
    return ["Informar valor", gapHref(gap)];
  }

  function moneyCard(title, value, detail, action, href, filled, note) {
    return '<article class="money-card"><h2>' + esc(title) + '</h2><p class="' + (filled ? "money-value" : "money-empty") + '">' + value + '</p><p class="money-context">' + detail + '</p><a class="secondary" href="' + href + '">' + esc(action) + "</a>" + (note || "") + "</article>";
  }

  function availableCard(overview) {
    if (overview.position && overview.position.amount_cents != null) {
      return moneyCard("Investido", money(overview.position.amount_cents, overview.position.currency), "Informado em " + shortWhen(overview.position.as_of) + ". Não entra na margem.", "Conferir valor", "#contas", true, "");
    }
    var informed = overview.informed;
    if (!informed) return moneyCard("Disponível", "Ainda não informado", "Informe o valor e a data.", "Informar valor", "#planejar/disponivel/voltar", false, "");
    var context = "Informado em " + shortWhen(informed.on) + (informed.protectedCents ? " · reserva " + brl(informed.protectedCents) : "");
    var projected = overview.projected ? " Projeção para " + shortWhen(overview.projected.on) + ": " + brl(overview.projected.cents) + ". Não é o valor informado." : "";
    return moneyCard("Disponível", brl(informed.cents), context, "Conferir valor", "#planejar/disponivel/voltar", true, how("Este é o disponível que você informou nessa data. A reserva já está dentro dele e não é somada de novo." + projected));
  }

  function payableCard(overview) {
    var payable = overview.payables || {};
    if (!payable.count && !payable.pendingCount) return moneyCard("A pagar", "Nenhuma conta informada", "Adicione os compromissos que conhece.", "Informar contas", "#planejar/contas/voltar", false, "");
    if (!payable.count) return moneyCard("A pagar", payable.pendingCount + " sem valor ou data", "A soma fica de fora enquanto o valor não existe.", "Completar", "#planejar/contas/voltar", false, "");
    var bits = [payable.count + (payable.count > 1 ? " contas" : " conta"), "Compromissos informados"];
    if (payable.overdueCount) bits.push(payable.overdueCount + (payable.overdueCount > 1 ? " vencidas" : " vencida"));
    if (payable.pendingCount) bits.push(payable.pendingCount + " sem valor");
    return moneyCard("A pagar", brl(payable.cents), bits.join(" · "), payable.pendingCount ? "Completar" : "Conferir contas", "#planejar/contas/voltar", true, how("A soma usa o que ainda falta nos compromissos informados. Vencidos entram uma vez. O extrato não é somado aqui. " + esc(payable.coverage || "Compromissos do planejamento") + "."));
  }

  function inflowCard(overview) {
    var next = overview.nextInflow;
    var uncertain = overview.uncertainInflow;
    if (next) {
      var context = esc(next.label) + " · " + shortWhen(next.on) + " · confirmada";
      if (uncertain) context += " · há outra entrada incerta";
      return moneyCard("Próxima entrada", brl(next.cents), context, "Conferir entrada", "#planejar/entrada/voltar", true, how("Só a entrada confirmada sustenta o período e a frase principal. A incerta fica na agenda."));
    }
    if (uncertain) return moneyCard("Próxima entrada", uncertain.cents == null ? "Entrada incerta" : brl(uncertain.cents), esc(uncertain.label) + (uncertain.on ? " · " + shortWhen(uncertain.on) : "") + " · não entra como garantida", "Informar entrada", "#planejar/entrada/voltar", uncertain.cents != null, "");
    return moneyCard("Próxima entrada", "Ainda não informada", "Quando você espera receber?", "Informar entrada", "#planejar/entrada/voltar", false, "");
  }

  function marginText(overview) {
    var margin = overview.margin || {};
    if (!margin.complete || margin.cents == null) return "Quanto cabe gastar: ainda não calculado.";
    if (margin.cents <= 0) return "Quanto cabe gastar: não há margem livre de " + showDate(margin.from) + " até " + showDate(margin.until) + ", depois dos compromissos e da reserva.";
    return "Quanto cabe gastar: " + brl(margin.cents) + " de " + showDate(margin.from) + " até " + showDate(margin.until) + ", depois dos compromissos e da reserva.";
  }

  function chart(overview) {
    var series = overview.series;
    if (!series || !series.length) return '<p class="small">A projeção aparece quando há saldo de referência e cobertura suficiente. Os registros conhecidos continuam na lista.</p>';
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
    return '<div class="chartwrap"><h3>Evolução</h3><p class="small">Projeção diária. A linha tracejada é zero. A linha da reserva mostra a parte protegida.</p>' +
      '<svg viewBox="0 0 ' + width + " " + height + '" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">Trajetória do disponível</title><desc id="chart-desc">De ' + esc(brl(series[0].cents)) + " em " + esc(showDate(series[0].date)) + " até " + esc(brl(series[series.length - 1].cents)) + " em " + esc(showDate(series[series.length - 1].date)) + ". Menor valor " + esc(brl(lowest.cents)) + " em " + esc(showDate(lowest.date)) + ".</desc>" +
      '<line x1="' + pad + '" y1="' + y(0).toFixed(1) + '" x2="' + (width - pad) + '" y2="' + y(0).toFixed(1) + '" stroke="#514c5c" stroke-dasharray="4 4"/>' +
      (floor ? '<line x1="' + pad + '" y1="' + y(floor).toFixed(1) + '" x2="' + (width - pad) + '" y2="' + y(floor).toFixed(1) + '" stroke="#3a3168" stroke-dasharray="2 3"/>' : "") +
      '<polyline fill="none" stroke="#173e64" stroke-width="2" points="' + points + '"/>' + dot + "</svg>" +
      "<p>Leitura: começa em " + brl(series[0].cents) + " em " + showDate(series[0].date) + " e termina em " + brl(series[series.length - 1].cents) + " em " + showDate(series[series.length - 1].date) + ". O menor valor é " + brl(lowest.cents) + " em " + showDate(lowest.date) + "." +
      (critical ? " O primeiro ponto sem dinheiro é " + showDate(critical.date) + ", com " + brl(critical.cents) + "." : "") + "</p></div>";
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

  function daysHint(iso, reference) {
    if (!iso || !reference) return "";
    var from = Date.parse(reference + "T00:00:00Z");
    var to = Date.parse(String(iso).slice(0, 10) + "T00:00:00Z");
    if (!Number.isFinite(from) || !Number.isFinite(to)) return "";
    var days = Math.round((to - from) / 86400000);
    if (days === 0) return "hoje";
    if (days === 1) return "em 1 dia";
    if (days > 1) return "em " + days + " dias";
    return "";
  }

  function monthShift(month, delta) {
    var parts = month.split("-").map(Number);
    var date = new Date(Date.UTC(parts[0], parts[1] - 1 + delta, 1));
    return date.getUTCFullYear() + "-" + String(date.getUTCMonth() + 1).padStart(2, "0");
  }

  function calendar(data, overview) {
    var reference = overview.reference || "";
    if (!reference) return '<section class="money-calendar"><h2>Agenda do mês</h2><p>A agenda aparece quando a consulta traz a data de referência.</p></section>';
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
      if (inn.length) marks += '<span class="cal-dot in">' + inn.length + " entra</span>";
      if (out.length) marks += '<span class="cal-dot out">' + out.length + " sai</span>";
      if (uncertain || overdue) marks += '<span class="cal-dot attention">Atenção</span>';
      var described = dayEvents.map(function (item) { return item.label + " " + (item.cents == null ? "sem valor" : brl(item.cents)); }).join(", ");
      cells += '<button type="button" class="cal-day' + (dayEvents.length ? " has-event" : "") + (iso === reference ? " is-today" : "") + (iso === selected ? " is-selected" : "") + '" data-day="' + iso + '" aria-pressed="' + (iso === selected ? "true" : "false") + '" aria-label="' + esc(index + (described ? ". " + described : ". Nada informado")) + '"><strong>' + index + "</strong>" + marks + "</button>";
    }
    var outside = dated.filter(function (item) { return item.on < reference && item.on.slice(0, 7) !== cursorMonth && item.kind === "saida"; });
    var chosen = dated.filter(function (item) { return item.on === selected; });
    var names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
    var emptyMonth = !all.length ? '<p class="calhelp">Nenhum compromisso neste calendário.</p>' : "";
    var next = overview.nextInflow;
    var nextBlock = "";
    if (next && next.cents != null) {
      nextBlock = '<div class="next"><h3>Próximo recebimento</h3><div class="nextline"><div>' + esc(next.label || "Entrada") + "<small>" + showDate(next.on) + (daysHint(next.on, reference) ? " · " + daysHint(next.on, reference) : "") + '</small></div><strong class="in">' + brl(next.cents) + '</strong></div><a class="link" href="#planejar/entrada/voltar">Conferir entrada</a></div>';
    }
    return '<section class="surface pad money-calendar"><div class="calendarhead"><h2>Agenda do mês</h2><span>' + names[parts[1] - 1] + " de " + parts[0] + '</span></div>' +
      '<div class="cal-legend"><span class="cal-key in"><i></i>Entrada</span><span class="cal-key out"><i></i>Saída</span><span class="cal-key attention"><i></i>Atenção</span></div>' +
      emptyMonth +
      '<div class="cal-grid" role="grid" aria-label="Calendário de compromissos"><span>D</span><span>S</span><span>T</span><span>Q</span><span>Q</span><span>S</span><span>S</span>' + cells + "</div>" +
      '<p class="calhelp">Toque em um dia para ver seus registros. O mês é o mesmo em toda a tela.</p>' +
      '<div id="day-list">' + (selected ? dayList(chosen, selected) : "") + "</div>" +
      (undated.length ? "<h3>Sem data</h3><ul>" + undated.map(itemLine).join("") + "</ul>" : "") +
      (outside.length ? "<h3>Vencidos fora deste mês</h3><ul>" + outside.map(itemLine).join("") + "</ul>" : "") +
      nextBlock +
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
    if (item.estimate && item.estimate.status === "unknown") money = "";
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
    } else if (saved && saved.status === "failed") {
      note = '<p class="muted">A interpretação de hoje não ficou pronta. Os números continuam os calculados pela ISA.</p>';
    }
    return '<section class="surface pad ai"><div class="eyebrow">Ajuda da ISA</div><h2>Leitura do contexto</h2>' + note +
      '<button type="button" class="link" id="ask-reading">Atualizar a leitura</button><p id="reading-note" class="muted"></p>' +
      '<a class="link" href="#planejar/resumo">Avaliar um gasto</a></section>';
  }

  function monthTitle(month) {
    var parts = String(month || "").split("-");
    var names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
    if (parts.length !== 2) return "";
    return names[Number(parts[1]) - 1] + " de " + parts[0];
  }

  function recordMoney(item) {
    var sign = item.direction === "entrada" ? "" : "−";
    return sign + brl(item.cents);
  }

  function recordLine(item) {
    var plan = item.state === "em aberto" || item.state === "previsto" || item.state === "vencido" || item.state === "incerta";
    var href = plan ? "#planejar/contas/voltar" : (item.id ? "#detalhe/" + item.id : "#lancamentos");
    var when = String(item.on || "");
    return '<div class="entry"><div class="date">' + esc(when ? when.slice(8, 10) : "") + '</div><a href="' + esc(href) + '"><strong>' + esc(item.label) + "</strong><small>" + esc(item.state) + (item.on ? " · " + showDate(item.on) : "") + '</small></a><div class="money ' + (item.direction === "entrada" ? "in" : "out") + '">' + recordMoney(item) + "</div></div>";
  }

  function draw(data, warning) {
    var slot = document.getElementById("money-home");
    if (!slot) return;
    var overview = data.overview || {};
    if (overview.kind === "moedas") {
      slot.innerHTML = '<p class="money-period">Valores separados por moeda. Sem câmbio registrado, não há um total em reais.</p>' +
        (overview.groups || []).map(function (group) {
          var item = group.overview || {};
          var payable = item.payables || {};
          var available = item.informed ? money(item.informed.cents, group.currency) : "Não informado";
          var due = payable.count ? money(payable.cents, group.currency) : "Nenhum compromisso nesta moeda";
          return '<article class="money-card"><h2>' + esc(group.name) + '</h2><p class="' + (item.informed ? "money-value" : "money-empty") + '">' + esc(available) + '</p><p class="money-context">Disponível nesta moeda.</p><p class="' + (payable.count ? "money-value" : "money-empty") + '">' + esc(due) + '</p><p class="money-context">A pagar neste recorte.</p></article>';
        }).join("") +
        ((data.context || {}).unassignedCommitments ? '<p class="note">Há compromissos sem conta definida. Eles continuam em Todas as contas.</p>' : "");
      return;
    }
    var balance = data.balance || {};
    var month = data.month || {};
    cursorMonth = month.month || (overview.reference || "").slice(0, 7);
    var records = month.records || [];
    var visible = selected ? records.filter(function (item) { return item.on === selected; }) : records;
    var phase = month.phase === "futuro" ? "Este mês é previsto. Ainda não é histórico realizado." : (month.phase === "passado" ? "Mês anterior. O realizado é o que já foi pago ou recebido. O que ficou em aberto não vira pagamento realizado." : "Mês corrente: realizado até hoje e previsto restante.");
    var presence = data.presence || {};
    var first = presence.emptyPerson === true;
    var origin = balance.lines && balance.lines.length && document.getElementById("show-origin") && document.getElementById("show-origin").getAttribute("aria-expanded") === "true";
    var knownNames = (balance.missing || []).map(function (item) { return item.name; }).filter(Boolean);
    var partial = !!(balance.partial || balance.missing && balance.missing.length);
    var moneyLabel = balance.cents == null ? "Sem saldo informado" : brl(balance.cents);
    var eyebrow = balance.asOf ? (balance.label || "Saldo") + " · " + showDate(balance.asOf) : (balance.label && balance.label !== "Ainda não informado" ? balance.label : "Saldo");
    var meta = [];
    if (balance.origin) meta.push(balance.origin);
    if (balance.protectedCents) meta.push("reserva " + brl(balance.protectedCents) + " incluída");
    if (partial && knownNames.length) meta.push("falta " + knownNames.join(", "));
    var inLabel = month.phase === "passado" ? "Entrou no mês" : "Ainda vai entrar";
    var outLabel = month.phase === "passado" ? "Saiu no mês" : "Ainda falta pagar";
    var inValue = month.phase === "passado" ? month.realizedIn : month.forecastIn;
    var outValue = month.phase === "passado" ? month.realizedOut : month.forecastOut;
    var decision = first ? "" : situationText(overview);
    var action = null;
    if (!first && partial) action = ["Conferir saldos", "#contas"];
    else if (!first && overview.situation && overview.situation.kind === "shortfall") action = ["Comparar alternativas", "#planejar/resumo"];
    else if (!first && balance.stale) action = ["Conferir referência", "#contas"];
    var margin = balance.usableToday ? marginText(overview) : "";
    if (!first && partial && /disponível|Informe|falta informação/i.test(decision)) {
      decision = knownNames.length ? "Falta o saldo de " + knownNames.join(", ") + "." : "Falta uma referência de saldo para calcular a margem.";
    }
    var monthEmpty = !records.length;
    slot.innerHTML =
      (warning ? '<p class="note" role="status">' + esc(warning) + '</p><button type="button" class="secondary" id="money-retry">Tentar novamente</button>' : "") +
      '<div class="month monthnav" role="group" aria-label="Período"><button type="button" class="secondary" id="home-prev" aria-label="Mês anterior">‹</button><strong>' + esc(monthTitle(cursorMonth)) + '</strong><button type="button" class="secondary" id="home-next" aria-label="Próximo mês">›</button><button type="button" class="secondary" id="home-current">Mês atual</button><span class="periodhint">' + esc(phase) + "</span></div>" +
      '<div class="money-layout"><div class="money-main">' +
      (first ? '<section class="surface empty"><h2>Sua visão financeira começa pelas contas</h2><p>Nenhuma conta ou movimentação foi encontrada para esta pessoa. Cadastre uma conta para organizar o dinheiro e acompanhar o que vem pela frente.</p><p><a class="btn primary" href="#contas">Cadastrar primeira conta</a></p></section><section class="surface pad"><h2>Seu mês, em um só lugar</h2><p class="muted">O que entrou, o que saiu e os próximos compromissos aparecem aqui, com data, valor e situação.</p></section>' : "") +
      (first ? "" : '<section class="surface"><div class="pad"><div class="summarytop"><div><div class="eyebrow">' + esc(eyebrow) + '</div><div class="amount">' + esc(moneyLabel) + '</div><p class="summarymeta">' + esc(meta.join(" · ")) + '</p></div><button type="button" class="link" id="show-origin" aria-expanded="' + (origin ? "true" : "false") + '">Ver contas e origem</button></div>' +
      (origin ? "<ul class=\"origin-list\">" + (balance.lines || []).map(function (line) { return "<li>" + esc(line.name) + " · " + (line.cents == null ? "sem valor" : money(line.cents, line.currency)) + " · " + (line.asOf ? showDate(line.asOf) : "sem data") + (line.excluded ? " · " + esc(line.excluded) : "") + "</li>"; }).join("") + "</ul>" : "") +
      '<div class="balances"><div><h3>' + inLabel + '</h3><div class="metric in">' + (inValue ? brl(inValue) : "—") + '</div></div><div><h3>' + outLabel + '</h3><div class="metric out">' + (outValue ? brl(outValue) : "—") + "</div></div></div></div>" +
      '<div class="insight"><h3>' + esc(decision || "A situação usa o que já está registrado.") + "</h3>" + (margin ? "<p class=\"limit\">" + esc(margin) + "</p>" : "") +
      (action ? '<div class="actions"><a class="link" href="' + esc(action[1]) + '">' + esc(action[0]) + "</a></div>" : "") +
      (presence.unassignedRecords ? "<p class=\"limit\">Há registros sem conta vinculada. Eles continuam consultáveis e não foram copiados.</p><a class=\"link\" href=\"#lancamentos\">Conferir vínculos</a>" : "") +
      "</div></section>") +
      (first ? "" : '<section class="surface pad"><div class="headingrow"><div><h2>Seu mês completo</h2><p class="small">' + esc(phase) + "</p></div></div>" +
      '<table class="monthledger"><thead><tr><th>Movimento</th><th>Realizado</th><th>' + (month.phase === "passado" ? "Em aberto" : "Previsto restante") + '</th></tr></thead><tbody><tr><td>Entradas</td><td>' + (month.realizedIn ? brl(month.realizedIn) : "—") + "</td><td>" + (month.forecastIn ? brl(month.forecastIn) : "—") + '</td></tr><tr><td>Saídas</td><td>' + (month.realizedOut ? brl(month.realizedOut) : "—") + "</td><td>" + (month.forecastOut ? brl(month.forecastOut) : "—") + "</td></tr></tbody></table>" +
      '<p class="small">Esse resultado do mês não é o saldo.</p>' +
      (month.emptyForecast ? "<p class=\"small\">Nenhum compromisso registrado neste mês. Isso não garante ausência de despesas.</p>" : "") +
      (selected ? '<p class="small">Os totais acima continuam do mês. A lista mostra só ' + showDate(selected) + '. <button type="button" class="link" id="clear-day">Ver mês</button></p>' : "") +
      (monthEmpty && presence.hasFinancialRecord ? '<p class="small">Nenhum lançamento neste mês.</p>' : "") +
      (visible.length ? '<div class="movements">' + visible.map(recordLine).join("") + "</div>" : (monthEmpty && !presence.hasFinancialRecord ? "" : "")) +
      chart(overview) + "</section>") +
      '</div><aside class="money-side">' +
      calendar(data, overview) + (first ? '<section class="surface pad"><h2>Quando houver dados</h2><p class="muted">A leitura da ISA começa depois e cita os registros usados. Esta orientação não é uma análise.</p></section>' : reading(overview)) + "</aside></div>";
    bind(data);
  }

  function bind(data) {
    var retry = document.getElementById("money-retry");
    if (retry) retry.onclick = function () { open(currentMonth()); };
    var previous = document.getElementById("home-prev");
    var next = document.getElementById("home-next");
    var current = document.getElementById("home-current");
    if (previous) previous.onclick = function () { open(monthShift(cursorMonth, -1)); };
    if (next) next.onclick = function () { open(monthShift(cursorMonth, 1)); };
    if (current) current.onclick = function () { selected = ""; open((data.overview || {}).reference ? data.overview.reference.slice(0, 7) : ""); };
    var clearDay = document.getElementById("clear-day");
    if (clearDay) clearDay.onclick = function () { selected = ""; sessionStorage.removeItem(dayKey()); draw(data, ""); };
    var originButton = document.getElementById("show-origin");
    if (originButton) originButton.onclick = function () {
      originButton.setAttribute("aria-expanded", originButton.getAttribute("aria-expanded") === "true" ? "false" : "true");
      draw(data, "");
    };
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
        api("POST", "/api/insights/dismiss", { id: button.getAttribute("data-dismiss") }).then(function () { open(currentMonth()); }).catch(function () {
          button.disabled = false;
        });
      };
    });
    var ask = document.getElementById("ask-reading");
    if (ask) ask.onclick = function () { requestReading(true); };
  }

  function needsReading(overview) {
    var facts = overview.insightHistory || [];
    if (!facts.length) return false;
    var saved = overview.reading;
    if (!saved || saved.stale || saved.day !== overview.reference) return true;
    return saved.status !== "done" && saved.status !== "queued" && saved.status !== "running" && saved.status !== "failed";
  }

  function requestReading(manual) {
    var note = document.getElementById("reading-note");
    var ask = document.getElementById("ask-reading");
    if (ask) ask.disabled = true;
    api("POST", "/api/insights/today", { manual: !!manual }).then(function (job) {
      if (note && (manual || job.status === "failed" || job.status === "limit")) {
        note.textContent = job.message || (job.status === "unavailable" ? "A leitura por IA está indisponível. Os números continuam os calculados pela ISA." : "A leitura de hoje está sendo preparada. Os números não dependem dela.");
      }
      if (ask) ask.disabled = false;
    }).catch(function (error) {
      if (note) note.textContent = error.message || "A interpretação não foi atualizada. Os números continuam os últimos calculados.";
      if (ask) ask.disabled = false;
    });
  }

  function showFailure(status) {
    var slot = document.getElementById("money-home");
    if (!slot) return;
    var expired = status === 401;
    slot.innerHTML = '<section class="surface"><h2>Não conseguimos atualizar suas informações agora</h2><p>' +
      (expired ? "A sessão expirou." : "A consulta não foi concluída.") + "</p>" +
      (expired ? '<p><a class="btn primary" href="/api/login/start">Entrar novamente</a></p>' : '<button type="button" class="secondary" id="money-retry">Tentar novamente</button>') +
      "</section>";
    var retry = document.getElementById("money-retry");
    if (retry) retry.onclick = function () { open(currentMonth()); };
  }

  function maybeRead(data) {
    var overview = data.overview || {};
    if (overview.kind === "moedas" || !needsReading(overview)) return;
    var key = (data.ownerId || identity()) + "|" + (window.isaAccountContext || "all") + "|" + (overview.reference || "") + "|" + (overview.fingerprint || "");
    if (readingAsked[key]) return;
    readingAsked[key] = true;
    requestReading(false);
  }

  function open(month) {
    var slot = document.getElementById("money-home");
    if (!slot) return;
    if (month != null && month !== "" && !validMonth(month)) month = currentMonth();
    if (validMonth(month)) cursorMonth = month;
    var token = ++loadToken;
    var key = cacheKeyFor(month);
    selected = sessionStorage.getItem(dayKey()) || "";
    var savedNow = lastByKey[key];
    if (savedNow && savedNow.data && savedNow.data.ownerId === identity()) {
      try { draw(savedNow.data, ""); } catch (err) { if (window.console) console.error(err); }
    } else if (!slot.querySelector(".money-layout") && !slot.querySelector(".home-empty")) {
      var titleNode = slot.querySelector(".month strong");
      if (titleNode && validMonth(month)) titleNode.textContent = monthTitle(month);
      if (!slot.querySelector(".surface")) slot.innerHTML = '<p class="muted" role="status">Carregando suas informações…</p>';
      else slot.setAttribute("aria-busy", "true");
    } else if (validMonth(month)) {
      var currentTitle = slot.querySelector(".month strong");
      if (currentTitle) currentTitle.textContent = monthTitle(month);
      slot.setAttribute("aria-busy", "true");
    }
    api("GET", "/api/home" + (validMonth(month) ? "?month=" + month : "")).then(function (data) {
      if (token !== loadToken || !document.getElementById("money-home")) return;
      if (!data || !data.overview || !data.month || !data.balance) {
        showFailure(0);
        return;
      }
      if (window.isaOwnerId && data.ownerId && data.ownerId !== window.isaOwnerId) return;
      if (data.ownerId) window.isaOwnerId = data.ownerId;
      var currency = ((data.context || {}).currency) || "";
      if (currency) window.isaHomeCurrency = currency;
      try {
        draw(data, "");
        slot.removeAttribute("aria-busy");
      } catch (err) {
        if (window.console) console.error(err);
        showFailure(0);
        return;
      }
      if (data.ownerId) lastByKey[cacheKeyFor(month)] = { data: data, at: new Date().toISOString(), currency: currency };
      maybeRead(data);
    }).catch(function (error) {
      if (token !== loadToken || !document.getElementById("money-home")) return;
      var saved = lastByKey[cacheKeyFor(month)];
      if (saved && saved.data && saved.data.ownerId === identity() && error.status !== 401) {
        try {
          var when = saved.at ? saved.at.slice(0, 16).replace("T", " ") : "";
          draw(saved.data, "Estas informações são da última consulta desta conta e deste período" + (when ? " (" + when + ")" : "") + ". A atualização ainda não foi concluída.");
        } catch (err) {
          if (window.console) console.error(err);
          showFailure(error.status);
        }
        return;
      }
      showFailure(error.status);
    });
  }

  function reset() {
    lastByKey = {};
    readingAsked = {};
    loadToken += 1;
    cursorMonth = "";
    selected = "";
  }

  window.IsaHome = { open: open, reset: reset };
})();
