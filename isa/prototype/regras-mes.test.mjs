import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const lotes = require("./lotes.js");
const calc = require("./calc.js");
const table = JSON.parse(fs.readFileSync(new URL("./regras-mes.json", import.meta.url), "utf8"));

table.cases.forEach(function (row) {
  assert.equal(lotes.whenOf(row.entry), row.when, row.name);
  assert.equal(lotes.monthOf(row.entry), row.month, row.name);
});

const month = "2026-10";
const entries = [
  { id: "a", merchant: "Mercado", direction: "gasto", nature: "consumo", status: "pago", statusDate: "2026-10-05", noteDate: "2026-10-05", amountMinor: 10000 },
  { id: "b", merchant: "Luz", direction: "gasto", nature: "consumo", status: "a_pagar", noteDate: "2026-10-10", dueDate: "2026-10-30", amountMinor: 20000 },
  { id: "c", merchant: "Internet", direction: "gasto", nature: "consumo", status: "a_pagar", noteDate: "2026-10-01", dueDate: "2026-11-15", amountMinor: 9000 },
  { id: "d", merchant: "Farmácia", direction: "gasto", nature: "a_conferir", status: "pago", statusDate: "2026-10-12", noteDate: "2026-10-12", amountMinor: 5000, source: "extrato-bb-arquivo" },
  { id: "e", merchant: "Padaria", direction: "gasto", nature: "a_conferir", status: "pago", statusDate: "2026-10-14", noteDate: "2026-10-14", amountMinor: 3000, source: "extrato-bb-arquivo", archived: true },
  { id: "f", merchant: "Freela", direction: "ganho", nature: "consumo", status: "a_receber", noteDate: "2026-10-02", dueDate: "2026-10-28", amountMinor: 50000 },
  { id: "g", merchant: "Aluguel", direction: "gasto", nature: "consumo", status: "a_pagar", dueDate: "2026-10-20", amountMinor: 100000 },
];

assert.equal(lotes.monthOf(entries[2]), "2026-11");
assert.equal(lotes.monthOf(entries[4]), "2026-10");
const october = entries.filter(function (entry) { return lotes.monthOf(entry) === month && !entry.archived; });
assert.deepEqual(october.map(function (entry) { return entry.id; }), ["a", "b", "d", "f", "g"]);
const summary = calc.summarize(entries, month);
assert.equal(summary.paid, 10000);
assert.equal(summary.bankOut, 5000);
assert.equal(summary.received, 0);
assert.equal(summary.toPay, 120000);
assert.equal(summary.toReceive, 50000);
assert.equal(calc.summarize(entries, "2026-11").toPay, 9000);
assert.equal(calc.summarize([entries[4]], month).paid, 0);
assert.equal(calc.summarize([entries[4]], month).bankOut, 0);

const paidWithoutStatusDate = calc.summarize([
  { id: "sem", direction: "gasto", nature: "consumo", status: "pago", noteDate: "2026-10-12", amountMinor: 700 },
], month);
assert.equal(paidWithoutStatusDate.paid, 700);

console.log("regras-mes ok");
