/* Cálculo do mês da ISA. Resultado do período não é saldo bancário. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.IsaCalc = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function monthKey(iso) {
    if (!iso || String(iso).length < 7) return "";
    return String(iso).slice(0, 7);
  }

  function isOpen(status) {
    return status === "a_pagar" || status === "a_receber";
  }

  function isRealized(status) {
    return status === "pago" || status === "recebido";
  }

  function realizedWhen(entry) {
    return entry.statusDate || entry.noteDate || "";
  }

  function isStatement(entry) {
    return entry.source === "exemplo-sintetico" || entry.source === "arquivo-teste" || entry.source === "extrato-sintetico" || entry.source === "extrato-bb-arquivo";
  }

  function countsInConsumption(entry) {
    if (entry.nature === "consumo") return true;
    return !entry.nature && !isStatement(entry);
  }

  function summarize(entries, month) {
    const out = {
      received: 0,
      paid: 0,
      result: 0,
      toReceive: 0,
      toPay: 0,
      excluded: 0,
      aside: 0,
      unidentified: 0,
      bankIn: 0,
      bankOut: 0,
      rende: 0,
      paidByCategory: {},
    };
    (entries || []).forEach(function (entry) {
      if (!entry || entry.archived) return;
      if (entry.linkId) {
        const other = (entries || []).find(function (item) { return item.id === entry.linkId; });
        if (other && isStatement(entry) && !isStatement(other)) return;
        if (other && entry.source === other.source && entry.id > other.id) return;
      }
      const amount = Number(entry.amountMinor) || 0;
      if (entry.nature === "bb_rende_facil" && isRealized(entry.status) && monthKey(realizedWhen(entry)) === month) {
        out.rende += amount;
        return;
      }
      if ((entry.nature === "a_conferir" || (isStatement(entry) && !entry.nature)) && isRealized(entry.status) && monthKey(realizedWhen(entry)) === month) {
        out.unidentified += 1;
        if (entry.direction === "ganho") out.bankIn += amount;
        else out.bankOut += amount;
        return;
      }
      if (!countsInConsumption(entry)) {
        if (isRealized(entry.status) && monthKey(realizedWhen(entry)) === month) {
          if (entry.nature === "transferencia" || entry.nature === "reembolso" || entry.nature === "emprestimo") out.excluded += amount;
          else out.aside += amount;
        }
        return;
      }
      if (entry.direction === "ganho" && entry.status === "recebido" && monthKey(realizedWhen(entry)) === month) {
        out.received += amount;
      } else if (entry.direction === "gasto" && entry.status === "pago" && monthKey(realizedWhen(entry)) === month) {
        out.paid += amount;
        const cat = entry.category || "A categorizar";
        out.paidByCategory[cat] = (out.paidByCategory[cat] || 0) + amount;
      } else if (entry.direction === "ganho" && entry.status === "a_receber" && monthKey(entry.dueDate || entry.noteDate) === month) {
        out.toReceive += amount;
      } else if (entry.direction === "gasto" && entry.status === "a_pagar" && monthKey(entry.dueDate || entry.noteDate) === month) {
        out.toPay += amount;
      }
    });
    out.result = out.received - out.paid;
    return out;
  }

  function duplicateKind(candidate, existing) {
    if (!candidate || !existing || existing.archived) return "";
    if (candidate.id && existing.id === candidate.id) return "";
    if (candidate.documentId && existing.documentId && candidate.documentId === existing.documentId) {
      return "documento";
    }
    if (candidate.fingerprint && existing.fingerprint && candidate.fingerprint === existing.fingerprint) {
      return "imagem";
    }
    const sameMerchant = norm(candidate.merchant) && norm(candidate.merchant) === norm(existing.merchant);
    const sameDate = candidate.noteDate && candidate.noteDate === existing.noteDate;
    const sameAmount = Number(candidate.amountMinor) > 0 && Number(candidate.amountMinor) === Number(existing.amountMinor);
    if (sameMerchant && sameDate && sameAmount) return "combinacao";
    return "";
  }

  function findDuplicate(candidate, entries) {
    const list = entries || [];
    for (let i = 0; i < list.length; i += 1) {
      const kind = duplicateKind(candidate, list[i]);
      if (kind) return { entry: list[i], kind: kind };
    }
    return null;
  }

  function sameAmountAndDateOnly(candidate, entries) {
    if (findDuplicate(candidate, entries)) return false;
    return (entries || []).some(function (existing) {
      if (!existing || existing.archived || existing.id === candidate.id) return false;
      return (
        Number(candidate.amountMinor) > 0 &&
        Number(candidate.amountMinor) === Number(existing.amountMinor) &&
        candidate.noteDate &&
        candidate.noteDate === existing.noteDate
      );
    });
  }

  function norm(value) {
    return String(value || "")
      .trim()
      .toLocaleLowerCase("pt-BR");
  }

  return {
    monthKey: monthKey,
    isOpen: isOpen,
    isRealized: isRealized,
    summarize: summarize,
    findDuplicate: findDuplicate,
    sameAmountAndDateOnly: sameAmountAndDateOnly,
  };
});
