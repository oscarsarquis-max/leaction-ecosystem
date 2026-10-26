import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const lotes = require("./lotes.js");
const calc = require("./calc.js");

function booked(entry) {
  return entry.statusDate || entry.noteDate || "";
}

function byBook(a, b) {
  return booked(a).localeCompare(booked(b)) || String(a.id).localeCompare(String(b.id));
}

function sliceLike(entries, cut, activeIds) {
  let primary;
  if (cut.kind === "all") primary = entries.slice();
  else if (cut.kind === "batch") primary = entries.filter(function (entry) { return (entry.workBatchId || "") === cut.batch; });
  else if (cut.kind === "range") {
    primary = entries.filter(function (entry) {
      const when = lotes.whenOf(entry);
      return when >= cut.start && when <= cut.end;
    });
  } else primary = entries.filter(function (entry) { return lotes.monthOf(entry) === cut.month; });
  if (!cut.archived) primary = primary.filter(function (entry) { return !entry.archived; });
  primary.sort(byBook);
  const seen = new Set(primary.map(function (entry) { return entry.id; }));
  const extra = [];
  primary.forEach(function (entry) {
    if (!entry.linkId || seen.has(entry.linkId)) return;
    const other = entries.find(function (item) { return item.id === entry.linkId; });
    if (!other) return;
    seen.add(other.id);
    extra.push(Object.assign({}, other, { outsideSlice: true }));
  });
  if (cut.kind === "month" || cut.kind === "range") {
    (activeIds || []).forEach(function (id) {
      if (seen.has(id)) return;
      const other = entries.find(function (item) { return item.id === id; });
      if (!other) return;
      seen.add(id);
      extra.push(Object.assign({}, other, { outsideSlice: true }));
    });
  }
  return primary.concat(extra);
}

function visible(entries, filters, month, batches) {
  return (entries || []).filter(function (entry) {
    return lotes.inList(entry, filters, month, batches) && lotes.matchesQuick(entry, (filters || {}).quick || "");
  });
}

function sameRows(full, sliced, filters, month, batches, label) {
  const left = visible(full, filters, month, batches);
  const right = visible(sliced, filters, month, batches);
  assert.deepEqual(left.map(function (entry) { return entry.id; }), right.map(function (entry) { return entry.id; }), label + " ids");
  assert.deepEqual(lotes.summarize(left), lotes.summarize(right), label + " totais");
  assert.deepEqual(lotes.composition(left, "BRL", "pagos"), lotes.composition(right, "BRL", "pagos"), label + " composição pagos");
  assert.deepEqual(lotes.composition(left, "BRL", "a_pagar"), lotes.composition(right, "BRL", "a_pagar"), label + " composição a pagar");
  assert.deepEqual(calc.summarize(left, month), calc.summarize(right, month), label + " cálculo das linhas");
  assert.equal(left.length, right.length, label + " contagem");
}

function comparePayload(data) {
  data.views.forEach(function (view) {
    sameRows(data.full, view.entries, view.filters || {}, view.month, view.batches || data.batches || [], view.name);
    if (view.wholeCalc) {
      assert.deepEqual(calc.summarize(view.entries, view.calcMonth), calc.summarize(data.full, view.calcMonth), view.name + " cálculo do mês");
    }
  });
  (data.months || []).forEach(function (row) {
    assert.equal(lotes.monthOf(row.entry), row.expect, JSON.stringify(row.entry));
  });
  if (data.partnerId) {
    const kept = data.monthEntries.filter(function (entry) { return entry.id !== data.partnerId; });
    assert.notDeepEqual(calc.summarize(data.monthEntries, data.calcMonth), calc.summarize(kept, data.calcMonth));
    assert.deepEqual(calc.summarize(data.monthEntries, data.calcMonth), calc.summarize(data.full, data.calcMonth));
  }
  return (data.duplicates || []).map(function (candidate) {
    const hit = calc.findDuplicate(candidate, data.dupEntries || []);
    if (hit) return { kind: hit.kind, id: hit.entry.id };
    return { soft: calc.sameAmountAndDateOnly(candidate, data.dupEntries || []) };
  });
}

if (process.argv[2] === "--compare") {
  const data = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const duplicates = comparePayload(data);
  process.stdout.write(JSON.stringify({ duplicates: duplicates }));
  process.exit(0);
}

const months = ["2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01"];
const batchId = "lote-obra";
const entries = [];
for (let i = 0; i < 2100; i += 1) {
  const month = months[i % months.length];
  const day = String((i % 27) + 1).padStart(2, "0");
  const open = i % 11 === 0;
  entries.push({
    id: "e-" + String(i).padStart(5, "0"),
    merchant: i % 23 === 0 ? "Padaria do teste" : "Linha " + i,
    direction: i % 3 === 0 ? "ganho" : "gasto",
    nature: i % 19 === 0 ? "" : ["consumo", "transferencia", "a_conferir"][i % 3],
    status: open ? (i % 3 === 0 ? "a_receber" : "a_pagar") : (i % 3 === 0 ? "recebido" : "pago"),
    statusDate: open ? "" : month + "-" + day,
    dueDate: open ? (i % 2 === 0 ? "2026-11-20" : month + "-" + day) : "",
    noteDate: month + "-01",
    amountMinor: 100 + (i % 400),
    currency: i % 29 === 0 ? "USD" : "BRL",
    category: i % 13 === 0 ? "" : "Alimentação",
    archived: i % 41 === 0,
    workBatchId: i < 40 ? batchId : "",
    source: i % 7 === 0 ? "extrato-bb-arquivo" : "digitado",
    documentId: i === 4 ? "NF-9" : "",
    fingerprint: i === 6 ? "img-9" : "",
  });
}
entries.push({
  id: "par-out",
  merchant: "Extrato ligado",
  direction: "gasto",
  nature: "a_conferir",
  status: "pago",
  statusDate: "2026-10-08",
  dueDate: "",
  noteDate: "2026-10-08",
  amountMinor: 8800,
  currency: "BRL",
  category: "",
  source: "extrato-bb-arquivo",
  linkId: "par-set",
});
entries.push({
  id: "par-set",
  merchant: "Manual ligado",
  direction: "gasto",
  nature: "consumo",
  status: "pago",
  statusDate: "2026-09-08",
  dueDate: "",
  noteDate: "2026-09-08",
  amountMinor: 8800,
  currency: "BRL",
  category: "Moradia",
  source: "digitado",
});
entries.sort(byBook);
const batches = [{ id: batchId, name: "Obra", documentRef: "DOC-1", supplier: "Fornecedor", criterionLabel: "Outro" }];
const activeIds = entries.filter(function (entry) { return entry.workBatchId === batchId; }).map(function (entry) { return entry.id; });

const views = [
  { name: "mês", cut: { kind: "month", month: "2026-10" }, filters: {}, month: "2026-10", wholeCalc: true },
  { name: "lote", cut: { kind: "batch", batch: batchId }, filters: { batchId: batchId }, month: "2026-10" },
  { name: "todos", cut: { kind: "all" }, filters: { mode: "todos-meses" }, month: "2026-10", wholeCalc: true },
  { name: "período", cut: { kind: "range", start: "2026-09-01", end: "2026-10-15" }, filters: { mode: "todos-meses", dateFrom: "2026-09-01", dateTo: "2026-10-15" }, month: "2026-10" },
  { name: "arquivados", cut: { kind: "month", month: "2026-10", archived: true }, filters: { archived: true }, month: "2026-10" },
  { name: "realizados", cut: { kind: "month", month: "2026-10" }, filters: { quick: "realizados" }, month: "2026-10" },
  { name: "previstos", cut: { kind: "month", month: "2026-10" }, filters: { quick: "previstos" }, month: "2026-10" },
  { name: "conferir", cut: { kind: "month", month: "2026-10" }, filters: { quick: "conferir" }, month: "2026-10" },
  { name: "direção", cut: { kind: "month", month: "2026-10" }, filters: { direction: "gasto" }, month: "2026-10" },
  { name: "categoria", cut: { kind: "month", month: "2026-10" }, filters: { category: "Alimentação" }, month: "2026-10" },
  { name: "situação", cut: { kind: "month", month: "2026-10" }, filters: { status: "pago" }, month: "2026-10" },
  { name: "moeda", cut: { kind: "month", month: "2026-10" }, filters: { currency: "USD" }, month: "2026-10" },
  { name: "busca", cut: { kind: "month", month: "2026-10" }, filters: { q: "padaria" }, month: "2026-10" },
  { name: "resultado", cut: { kind: "month", month: "2026-10" }, filters: { mode: "resultado" }, month: "2026-10" },
  { name: "consumo", cut: { kind: "month", month: "2026-10" }, filters: { consumption: true }, month: "2026-10" },
];

const monthSlice = sliceLike(entries, { kind: "month", month: "2026-10" }, activeIds);
views.forEach(function (view) {
  const sliced = view.wholeCalc && view.name === "mês" ? monthSlice : sliceLike(entries, view.cut, activeIds);
  sameRows(entries, sliced, view.filters, view.month, batches, view.name);
  if (view.wholeCalc) {
    assert.deepEqual(calc.summarize(sliced, "2026-10"), calc.summarize(entries, "2026-10"), view.name);
  }
});
const withoutPartner = monthSlice.filter(function (entry) { return entry.id !== "par-set"; });
assert.notDeepEqual(calc.summarize(monthSlice, "2026-10"), calc.summarize(withoutPartner, "2026-10"));
assert.equal(monthSlice.some(function (entry) { return entry.id === "par-set" && entry.outsideSlice; }), true);

[
  { entry: { statusDate: "2026-10-02", dueDate: "2026-11-02", noteDate: "2026-09-02" }, expect: "2026-10" },
  { entry: { dueDate: "2026-11-20", noteDate: "2026-10-02" }, expect: "2026-11" },
  { entry: { noteDate: "2026-08-01" }, expect: "2026-08" },
  { entry: {}, expect: "" },
].forEach(function (row) {
  assert.equal(lotes.monthOf(row.entry), row.expect);
});

const dupEntries = [
  { id: "d1", merchant: "Padaria", noteDate: "2026-10-03", amountMinor: 2500, documentId: "NF-1", booked: "2026-10-03" },
  { id: "d2", merchant: "Outro", noteDate: "2026-10-04", amountMinor: 2500, fingerprint: "abc", booked: "2026-10-04" },
  { id: "d3", merchant: "Mercado", noteDate: "2026-10-05", amountMinor: 900, booked: "2026-10-05" },
];
assert.equal(calc.findDuplicate({ merchant: "X", noteDate: "2026-01-01", amountMinor: 1, documentId: "NF-1" }, dupEntries).kind, "documento");
assert.equal(calc.findDuplicate({ merchant: "X", noteDate: "2026-01-01", amountMinor: 1, fingerprint: "abc" }, dupEntries).kind, "imagem");
assert.equal(calc.findDuplicate({ merchant: "padaria", noteDate: "2026-10-03", amountMinor: 2500 }, dupEntries).kind, "combinacao");
assert.equal(calc.findDuplicate({ merchant: "Novo", noteDate: "2026-10-05", amountMinor: 900 }, dupEntries), null);
assert.equal(calc.sameAmountAndDateOnly({ merchant: "Novo", noteDate: "2026-10-05", amountMinor: 900 }, dupEntries), true);
assert.equal(calc.sameAmountAndDateOnly({ id: "d3", merchant: "Mercado", noteDate: "2026-10-05", amountMinor: 900 }, dupEntries), false);
