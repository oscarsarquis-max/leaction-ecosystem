/* Lotes de trabalho. O total é a soma inteira dos lançamentos, nunca um valor digitado na capa. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.IsaLotes = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const STATEMENT = { "exemplo-sintetico": 1, "arquivo-teste": 1, "extrato-sintetico": 1, "extrato-bb-arquivo": 1 };

  function fold(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  }

  function bucket(entry) {
    const nature = entry.nature || "";
    const statement = !!STATEMENT[entry.source || ""];
    if (nature === "bb_rende_facil") return "rende";
    if (nature === "aplicacao") return "aplicacoes";
    if (nature === "transferencia" || nature === "reembolso" || nature === "emprestimo") return "transferencias";
    if (nature === "a_conferir" || (statement && !nature) || (nature !== "consumo" && nature !== "")) return "conferir";
    if (entry.direction === "gasto" && entry.status === "pago") return "gastosPagos";
    if (entry.direction === "gasto" && entry.status === "a_pagar") return "gastosAPagar";
    if (entry.direction === "ganho" && entry.status === "recebido") return "ganhosRecebidos";
    if (entry.direction === "ganho" && entry.status === "a_receber") return "ganhosAReceber";
    return "conferir";
  }

  function slot() {
    return { gastosPagos: 0, gastosAPagar: 0, ganhosRecebidos: 0, ganhosAReceber: 0, transferencias: 0, aplicacoes: 0, rende: 0, conferir: 0 };
  }

  function summarize(entries) {
    const currencies = {};
    let archived = 0;
    (entries || []).forEach(function (entry) {
      if (!entry) return;
      if (entry.archived) { archived += 1; return; }
      const code = entry.currency || "BRL";
      const kind = bucket(entry);
      const target = currencies[code] || (currencies[code] = slot());
      target[kind] += Number(entry.amountMinor) || 0;
    });
    return { byCurrency: currencies, archived: archived };
  }

  function composition(entries, currency, base) {
    const groups = {};
    (entries || []).forEach(function (entry) {
      if (!entry || entry.archived || (entry.currency || "BRL") !== currency) return;
      const kind = bucket(entry);
      if (base === "pagos" && kind !== "gastosPagos") return;
      if (base === "a_pagar" && kind !== "gastosAPagar") return;
      if (base === "registrados" && kind !== "gastosPagos" && kind !== "gastosAPagar") return;
      const label = (entry.category || "").trim() || "A categorizar";
      const item = groups[label] || (groups[label] = { category: label, amount: 0, count: 0 });
      item.amount += Number(entry.amountMinor) || 0;
      item.count += 1;
    });
    const items = Object.keys(groups).map(function (key) { return groups[key]; }).sort(function (a, b) {
      return b.amount - a.amount || a.category.localeCompare(b.category, "pt-BR");
    });
    return { currency: currency, base: base, items: items, total: items.reduce(function (sum, item) { return sum + item.amount; }, 0) };
  }

  function whenOf(entry) {
    return entry.statusDate || entry.dueDate || entry.noteDate || "";
  }

  function monthOf(entry) {
    return whenOf(entry).slice(0, 7);
  }

  const LABELS = {
    gastosPagos: "Gastos pagos",
    gastosAPagar: "Gastos a pagar",
    ganhosRecebidos: "Ganhos recebidos",
    ganhosAReceber: "Ganhos a receber",
    transferencias: "Transferências, reembolsos e empréstimos",
    aplicacoes: "Aplicações",
    rende: "BB Rende Fácil",
    conferir: "Valor a conferir",
  };

  function moneyLines(totals, money, headlineLabel) {
    const codes = Object.keys((totals && totals.byCurrency) || {});
    if (!codes.length) return "<p class=\"muted\">Nenhum valor gravado nesta base.</p>";
    const title = headlineLabel || "Gastos";
    return codes.map(function (code) {
      const slot = totals.byCurrency[code];
      const rows = Object.keys(LABELS).filter(function (key) { return slot[key]; }).map(function (key) {
        return "<p><span>" + LABELS[key] + "</span> <strong>" + money(slot[key], code) + "</strong></p>";
      }).join("");
      const paid = slot.gastosPagos || 0;
      const open = slot.gastosAPagar || 0;
      const headline = (paid || open) ? "<p class=\"lot-headline\"><span>" + escAttr(title) + "</span> <strong>" + money(paid + open, code) + "</strong></p><p class=\"muted\">Pagos " + money(paid, code) + " · ainda falta pagar " + money(open, code) + ". Não é saldo disponível.</p>" : "";
      return "<div class=\"lot-currency\"><h3>" + code + "</h3>" + headline + rows + "</div>";
    }).join("");
  }

  function escAttr(value) {
    return String(value || "").replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function bars(comp, money) {
    if (!comp || !comp.items.length) return "<p class=\"muted\">Nenhum gasto pago nesta moeda.</p>";
    const max = comp.items.reduce(function (acc, item) { return Math.max(acc, item.amount); }, 0) || 1;
    return comp.items.map(function (item) {
      const width = Math.max(8, Math.round((item.amount / max) * 100));
      const pct = comp.total ? Math.round((item.amount / comp.total) * 100) : 0;
      return "<button type=\"button\" class=\"bar\" data-lot-cat=\"" + escAttr(item.category) + "\" data-lot-currency=\"" + escAttr(comp.currency) + "\"><span>" + escAttr(item.category) + "</span><span class=\"track\"><i style=\"width:" + width + "%\"></i></span><span>" + money(item.amount, comp.currency) + " · " + item.count + " · " + pct + "%</span></button>";
    }).join("") + "<p class=\"muted\">Soma das categorias: " + money(comp.total, comp.currency) + ". Base: gastos pagos em " + comp.currency + ".</p>";
  }

  return {
    fold: fold,
    bucket: bucket,
    summarize: summarize,
    composition: composition,
    whenOf: whenOf,
    monthOf: monthOf,
    moneyLines: moneyLines,
    bars: bars,
    labels: LABELS,
  };
});
