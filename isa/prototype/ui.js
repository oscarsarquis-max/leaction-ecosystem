(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.IsaUi = factory();
})(typeof window !== "undefined" ? window : this, function () {
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function initials(name) {
    var parts = String(name || "").trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return "•";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function reais(cents) {
    var n = Math.abs(Math.round(Number(cents) || 0));
    var whole = Math.floor(n / 100);
    var frac = String(n % 100).padStart(2, "0");
    var grouped = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return "R$ " + grouped + "," + frac;
  }

  function amount(cents, direction, options) {
    options = options || {};
    var entrada = direction === "entrada";
    var text = reais(cents);
    var shown = entrada ? "↑ " + text : "↓ − " + text;
    var label = (entrada ? "Entrada de " : "Saída de ") + text;
    return '<span class="amt num ' + (entrada ? "in" : "out") + '" data-direction="' + (entrada ? "entrada" : "saida") + '" aria-label="' + esc(label) + '">' + esc(shown) + "</span>";
  }

  function referenceNow(when) {
    if (when) return new Date(when);
    if (typeof window !== "undefined" && window.isaReferenceDate) return new Date(window.isaReferenceDate + "T12:00:00-03:00");
    return new Date();
  }

  function todayMonth(when) {
    return new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit" }).format(referenceNow(when));
  }

  function todayLine(when, updated) {
    var parts = new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", weekday: "long", day: "numeric" }).formatToParts(referenceNow(when));
    var weekday = "";
    var day = "";
    parts.forEach(function (part) {
      if (part.type === "weekday") weekday = part.value.replace("-feira", "");
      if (part.type === "day") day = part.value;
    });
    var line = "Hoje, " + weekday + " " + day;
    if (updated) line += " · atualizado às " + updated;
    return line;
  }

  function monthControl(options) {
    options = options || {};
    var ids = options.ids || { prev: "prev-month", next: "next-month", current: "current-month" };
    var back = options.current ? "" : '<button type="button" class="secondary" id="' + esc(ids.current) + '">Mês atual</button>';
    var stamp = options.today ? '<span class="lbl month-stamp">' + esc(options.today) + "</span>" : "";
    var hint = options.hint ? '<span class="periodhint">' + esc(options.hint) + "</span>" : "";
    return '<div class="month monthbar" role="group" aria-label="Período"><div class="monthbar-main"><button type="button" class="ib" id="' + esc(ids.prev) + '" aria-label="Mês anterior">‹</button><strong class="month-title">' + esc(options.title || "") + '</strong><button type="button" class="ib" id="' + esc(ids.next) + '" aria-label="Próximo mês">›</button>' + back + "</div>" + stamp + hint + "</div>";
  }

  var WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

  function calendar(options) {
    options = options || {};
    var month = String(options.month || "");
    var parts = month.split("-").map(Number);
    if (parts.length < 2 || !parts[0] || !parts[1]) return "";
    var byDate = {};
    (options.days || []).forEach(function (day) { if (day && day.date) byDate[day.date] = day; });
    var first = new Date(Date.UTC(parts[0], parts[1] - 1, 1));
    var total = new Date(Date.UTC(parts[0], parts[1], 0)).getUTCDate();
    var lead = first.getUTCDay();
    var cells = WEEKDAYS.map(function (name) { return '<span class="wd">' + name + "</span>"; }).join("");
    var blank;
    for (blank = 0; blank < lead; blank += 1) cells += '<span class="cal-empty"></span>';
    var day;
    for (day = 1; day <= total; day += 1) {
      var iso = month + "-" + String(day).padStart(2, "0");
      var info = byDate[iso] || {};
      var attention = !!info.attention;
      var entrada = !!info.entrada;
      var saida = !!info.saida;
      var mark = "";
      if (attention) mark = '<span class="mk attention" aria-hidden="true">▲</span>';
      else if (entrada && saida) mark = '<span class="mk" aria-hidden="true"><span class="in">●</span><span class="out">■</span></span>';
      else if (saida) mark = '<span class="mk out" aria-hidden="true">■</span>';
      else if (entrada) mark = '<span class="mk in" aria-hidden="true">●</span>';
      var described = info.label || "Nada informado";
      var classes = "d cal-day day" + (iso === options.today ? " is-today" : "") + (iso === options.selected ? " is-selected" : "") + (attention ? " is-attention" : "");
      cells += '<button type="button" class="' + classes + '" data-day="' + iso + '" aria-pressed="' + (iso === options.selected ? "true" : "false") + '" aria-label="' + esc(day + ". " + described) + '"><span>' + day + "</span>" + mark + "</button>";
    }
    var legend = '<div class="legend cal-legend"><span><i class="mk in" aria-hidden="true">●</i> entrada</span><span><i class="mk out" aria-hidden="true">■</i> saída</span><span><i class="mk attention" aria-hidden="true">▲</i> atenção</span></div>';
    return '<div class="cal cal-grid" role="grid" aria-label="Calendário de compromissos">' + cells + "</div>" + legend;
  }

  function limitBar(options) {
    options = options || {};
    var used = Number(options.used) || 0;
    var total = Number(options.total) || 0;
    var pace = Number(options.pace);
    if (!Number.isFinite(pace)) pace = 1;
    var ratio = total > 0 ? used / total : 0;
    var width = Math.max(0, Math.min(100, ratio * 100));
    var tone = ratio > 1 ? "over" : (ratio > pace ? "above" : "brand");
    var paceLeft = Math.max(0, Math.min(100, pace * 100));
    return '<div class="limitbar" role="img" aria-label="' + esc(options.label || "Limite") + '"><div class="bar"><span class="fill ' + tone + '" style="width:' + width.toFixed(1) + '%"></span><span class="pace" style="left:' + paceLeft.toFixed(1) + '%"></span></div></div>';
  }

  function glyph(name) {
    var paths = {
      home: '<path d="M4 11.5 12 4.5 20 11.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z"/>',
      list: '<path d="M8 7h12M8 12h12M8 17h8"/><path d="M4 7h.01M4 12h.01M4 17h.01"/>',
      plan: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l2.5 2"/>',
      account: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/>',
    };
    return '<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (paths[name] || "") + "</svg>";
  }

  function dock(options) {
    options = options || {};
    var route = options.route || "";
    var current = function (hash) {
      if (hash === "#planejar") return route === "#planejar" || route.indexOf("#planejar/") === 0;
      if (hash === "#contas") return route === "#contas" || route.indexOf("#contas/") === 0;
      if (hash === "#lancamentos") return route === "#lancamentos" || route === "#lotes" || route.indexOf("#lote/") === 0;
      return route === hash;
    };
    var item = function (id, hash, label, icon) {
      return '<button type="button" id="' + id + '"' + (current(hash) ? ' aria-current="page"' : "") + ">" + glyph(icon) + "<span>" + label + "</span></button>";
    };
    var plus = options.hideRegistrar ? "" : '<button type="button" class="plus" id="nav-registrar" aria-label="Registrar"><span class="plus-mark"><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg></span></button>';
    return '<div class="dock"><nav class="nav" aria-label="Principal">' +
      item("nav-inicio", "#inicio", "Início", "home") +
      item("nav-lista", "#lancamentos", "Lançamentos", "list") +
      plus +
      item("nav-planejar", "#planejar", "Planejar", "plan") +
      item("nav-contas", "#contas", "Contas", "account") +
      "</nav></div>";
  }

  function shell(options) {
    options = options || {};
    var signed = !!options.signedIn;
    var route = options.route || "";
    var name = options.name || "";
    var mark = initials(options.initials || name);
    var current = function (hash) {
      if (hash === "#planejar") return route === "#planejar" || route.indexOf("#planejar/") === 0;
      if (hash === "#contas") return route === "#contas" || route.indexOf("#contas/") === 0;
      if (hash === "#lancamentos") return route === "#lancamentos" || route === "#lotes" || route.indexOf("#lote/") === 0;
      return route === hash;
    };
    var link = function (hash, label, id) {
      var on = current(hash);
      return '<a class="brand-link' + (on ? " is-current" : "") + '" href="' + hash + '" id="' + id + '"' + (on ? ' aria-current="page"' : "") + ">" + label + "</a>";
    };
    var account = signed && options.showAccount !== false ? '<div class="account-slot">' + (options.accountHtml || "") + "</div>" : "";
    var identity = signed
      ? '<div class="identity"><a class="brand-who" href="#perfil" id="brand-person">' + esc(name || "Seu perfil") + '</a><button type="button" class="brand-leave" id="brand-leave">Sair</button></div>'
      : "";
    var tools = signed ? '<div class="brand-tools">' + account + identity + "</div>" : "";
    var initialsLink = signed ? '<a class="brand-initials" href="#perfil" aria-label="Abrir perfil"><span>' + esc(mark) + "</span></a>" : "";
    var register = signed && !options.hideRegistrar ? '<a class="brand-go" href="#registrar" id="desk-registrar">+ Registrar</a>' : "";
    var nav = signed
      ? '<nav class="brand-nav" aria-label="Áreas"><div class="brand-nav-inner">' +
        link("#inicio", "Início", "desk-inicio") +
        link("#lancamentos", "Lançamentos", "desk-lista") +
        link("#planejar", "Planejar", "desk-planejar") +
        link("#contas", "Contas", "desk-contas") +
        link("#perfil", "Perfil", "desk-perfil") +
        register + "</div></nav>"
      : "";
    var task = options.task
      ? '<header class="taskbar"><a class="task-back" href="' + esc(options.taskBack || "#inicio") + '">' + esc(options.taskLabel || "Voltar") + "</a><strong>" + esc(options.taskTitle || options.title || "") + "</strong></header>"
      : "";
    var bar = '<header class="shell"><div class="brand-bar"><div class="brand-top"><a class="brand-mark" href="' + (signed ? "#inicio" : "#entrar") + '" aria-label="Action Finance — ISA Personal Finance"><img src="marca-faixa.png" srcset="marca-faixa.png 1x, marca-faixa@2x.png 2x" alt="Action Finance — ISA Personal Finance" width="195" height="32"></a>' +
      initialsLink + tools + "</div></div>" + nav + "</header>";
    return bar + task + '<div class="page">' + (options.title ? "<h1>" + esc(options.title) + "</h1>" : "") + (options.body || "") + "</div>" + (signed ? dock(options) : "");
  }

  return {
    esc: esc,
    initials: initials,
    amount: amount,
    monthControl: monthControl,
    calendar: calendar,
    limitBar: limitBar,
    shell: shell,
    dock: dock,
    todayLine: todayLine,
    todayMonth: todayMonth,
  };
});
