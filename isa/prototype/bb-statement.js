/* Perfil do extrato de conta corrente do Banco do Brasil observado em 16/10/2026.
   Não grava senha, não envia o arquivo e não trata número de documento como identidade. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.IsaStatement = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const HEADER = ["Data", "Lançamento", "Detalhes", "N° documento", "Valor", "Tipo Lançamento"];

  function decodeStatement(bytes) {
    const raw = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    let data = raw;
    if (raw.length >= 3 && raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf) {
      data = raw.subarray(3);
    }
    try {
      return { encoding: "utf-8", text: new TextDecoder("utf-8", { fatal: true }).decode(data) };
    } catch (err) {
      return { encoding: "windows-1252", text: new TextDecoder("windows-1252").decode(data) };
    }
  }

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let field = "";
    let quoted = false;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"') {
          if (text[i + 1] === '"') {
            field += '"';
            i += 1;
          } else quoted = false;
        } else field += ch;
      } else if (ch === '"') quoted = true;
      else if (ch === ",") {
        row.push(field);
        field = "";
      } else if (ch === "\n") {
        row.push(field);
        if (row.some(function (cell) { return cell !== ""; })) rows.push(row);
        row = [];
        field = "";
      } else if (ch !== "\r") field += ch;
    }
    if (field !== "" || row.length) {
      row.push(field);
      if (row.some(function (cell) { return cell !== ""; })) rows.push(row);
    }
    return rows;
  }

  function fold(text) {
    return String(text || "").normalize("NFC").replace(/\s+/g, " ").trim().toLocaleLowerCase("pt-BR");
  }

  function plain(text) {
    return fold(text).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function balanceClass(history) {
    const name = fold(history);
    if (name === "saldo anterior") return "saldo_anterior";
    if (name === "saldo do dia") return "saldo_do_dia";
    if (name === "s a l d o") return "saldo_informado";
    return "";
  }

  function familyOf(history) {
    const name = fold(history);
    if (name === "bb rende fácil" || name.indexOf("bb rende fácil ") === 0) return "bb_rende_facil";
    return "";
  }

  function meioOf(history) {
    const name = plain(history);
    if (/\bpix\b/.test(name)) return "pix";
    if (name.indexOf("transferencia") >= 0) return "transferencia";
    if (name.indexOf("cartao") >= 0 || name.indexOf("compra com cart") >= 0) return "cartao";
    return "";
  }

  function parseDate(text) {
    const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(text || "").trim());
    if (!match) return "";
    const day = Number(match[1]);
    const month = Number(match[2]);
    const year = Number(match[3]);
    if (month < 1 || month > 12) return "";
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (day < 1 || day > days[month - 1]) return "";
    return year + "-" + String(month).padStart(2, "0") + "-" + String(day).padStart(2, "0");
  }

  function parseCents(text) {
    const value = String(text || "").trim();
    if (!/^-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}$/.test(value)) return null;
    const negative = value.charAt(0) === "-";
    const digits = value.replace("-", "").replace(/\./g, "").replace(",", "");
    const cents = Number(digits);
    if (!Number.isSafeInteger(cents)) return null;
    return negative ? -cents : cents;
  }

  function batchIdentity(text) {
    let h1 = 0x811c9dc5;
    let h2 = 0x9e3779b9;
    for (let i = 0; i < text.length; i += 1) {
      const code = text.charCodeAt(i);
      h1 = Math.imul(h1 ^ code, 0x01000193);
      h2 = Math.imul(h2 ^ (code + i), 0x01000193);
    }
    return (h1 >>> 0).toString(16).padStart(8, "0") + (h2 >>> 0).toString(16).padStart(8, "0");
  }

  function lineSignature(row) {
    return [row.date, row.history, row.details, row.document, String(row.cents), row.class].join("\u001f");
  }

  function fail(message) {
    return { ok: false, error: message, rows: [] };
  }

  function parseStatement(text) {
    const table = parseCsv(String(text || "").replace(/^\uFEFF/, ""));
    if (!table.length) return fail("O arquivo não tem o cabeçalho do extrato do Banco do Brasil.");
    const header = table[0].map(function (cell) { return cell.trim(); });
    if (header.length !== HEADER.length || HEADER.some(function (name, index) { return header[index] !== name; })) {
      return fail("Este arquivo não traz as colunas Data, Lançamento, Detalhes, N° documento, Valor e Tipo Lançamento, nesta ordem.");
    }
    const rows = [];
    for (let i = 1; i < table.length; i += 1) {
      const cells = table[i];
      const line = i + 1;
      if (cells.length !== 6) return fail("A linha " + line + " não tem as 6 colunas. Nada foi importado.");
      const date = parseDate(cells[0]);
      if (!date) return fail("A linha " + line + " não tem uma data civil em dd/MM/aaaa. Nada foi importado.");
      const history = cells[1];
      const details = cells[2];
      const document = cells[3];
      const cents = parseCents(cells[4]);
      if (cents === null) return fail("A linha " + line + " não tem valor no formato brasileiro. Nada foi importado.");
      const tipo = cells[5].trim();
      const balance = balanceClass(history);
      if (tipo !== "Entrada" && tipo !== "Saída" && tipo !== "") {
        return fail("A linha " + line + " tem um tipo de lançamento desconhecido. Nada foi importado.");
      }
      if (balance && tipo) return fail("A linha " + line + " mistura observação de saldo com movimentação. Nada foi importado.");
      if (!balance && !tipo) return fail("A linha " + line + " não diz se é entrada, saída ou observação de saldo. Nada foi importado.");
      let rowClass = balance;
      if (tipo === "Entrada") {
        if (cents <= 0) return fail("A linha " + line + " está como entrada, mas o sinal não confere. Nada foi importado.");
        rowClass = "entrada";
      }
      if (tipo === "Saída") {
        if (cents >= 0) return fail("A linha " + line + " está como saída, mas o sinal não confere. Nada foi importado.");
        rowClass = "saida";
      }
      rows.push({
        line: line,
        date: date,
        history: history,
        details: details,
        document: document,
        cents: cents,
        tipo: tipo,
        class: rowClass,
        family: rowClass === "entrada" || rowClass === "saida" ? familyOf(history) : "",
        meio: rowClass === "entrada" || rowClass === "saida" ? meioOf(history) : "",
      });
    }
    const chain = checkChain(rows);
    const movements = rows.filter(function (row) { return row.class === "entrada" || row.class === "saida"; });
    const balances = rows.filter(function (row) { return row.class.indexOf("saldo_") === 0; });
    return {
      ok: true,
      rows: rows,
      movements: movements,
      balances: balances,
      counts: {
        movements: movements.length,
        balances: balances.length,
        entries: rows.filter(function (row) { return row.class === "entrada"; }).length,
        exits: rows.filter(function (row) { return row.class === "saida"; }).length,
        rendeFacil: movements.filter(function (row) { return row.family === "bb_rende_facil"; }).length,
      },
      chain: chain,
      batchId: batchIdentity(String(text || "").replace(/^\uFEFF/, "")),
    };
  }

  function checkChain(rows) {
    let running = null;
    let opened = false;
    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i];
      if (row.class === "saldo_anterior") {
        if (opened) return { ok: false, reason: "mais_de_um_saldo_anterior" };
        opened = true;
        running = row.cents;
      } else if (row.class === "entrada" || row.class === "saida") {
        if (running === null) return { ok: false, reason: "movimentacao_antes_do_saldo_anterior" };
        running += row.cents;
      } else if (running === null || running !== row.cents) {
        return { ok: false, reason: "saldo_nao_fecha" };
      }
    }
    return { ok: true, reason: "" };
  }

  function readStatement(bytes) {
    const decoded = decodeStatement(bytes);
    const parsed = parseStatement(decoded.text);
    parsed.encoding = decoded.encoding;
    return parsed;
  }

  function compareOverlap(existingSignatures, rows) {
    const have = {};
    (existingSignatures || []).forEach(function (signature) {
      have[signature] = (have[signature] || 0) + 1;
    });
    const groups = {};
    rows.forEach(function (row) {
      const signature = lineSignature(row);
      if (!groups[signature]) groups[signature] = { signature: signature, rows: [], already: have[signature] || 0 };
      groups[signature].rows.push(row);
    });
    return Object.keys(groups).map(function (signature) {
      const group = groups[signature];
      const incoming = group.rows.length;
      const status = group.already === 0 ? "nova" : "candidata";
      return { signature: signature, incoming: incoming, already: group.already, status: status, rows: group.rows };
    });
  }

  function planOccurrences(stored, movements) {
    const groups = {};
    (movements || []).forEach(function (row) {
      const signature = lineSignature(row);
      if (!groups[signature]) groups[signature] = [];
      groups[signature].push(row);
    });
    const importRows = [];
    const pendingRows = [];
    let reused = 0;
    Object.keys(groups).forEach(function (signature) {
      const rows = groups[signature];
      const incorporated = (stored || []).filter(function (item) {
        return item.signature === signature && item.state === "incorporada";
      }).length;
      const pending = (stored || []).filter(function (item) {
        return item.signature === signature && item.state === "pendente";
      }).length;
      const same = (stored || []).filter(function (item) {
        return item.signature === signature && item.state === "mesma";
      }).length;
      const covered = pending + same;
      if (incorporated === 0 && covered === 0) {
        rows.forEach(function (row) { importRows.push(row); });
        return;
      }
      if (covered >= rows.length) {
        reused += rows.length;
        return;
      }
      rows.slice(0, rows.length - covered).forEach(function (row) { pendingRows.push(row); });
      reused += covered;
    });
    return { importRows: importRows, pendingRows: pendingRows, reused: reused };
  }

  return {
    HEADER: HEADER,
    decodeStatement: decodeStatement,
    parseStatement: parseStatement,
    readStatement: readStatement,
    lineSignature: lineSignature,
    compareOverlap: compareOverlap,
    planOccurrences: planOccurrences,
    balanceClass: balanceClass,
    parseDate: parseDate,
    parseCents: parseCents,
  };
});
