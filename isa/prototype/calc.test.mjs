import { createRequire } from "node:module";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const calc = require("./calc.js");

const month = "2026-10";

function entry(partial) {
  return Object.assign(
    {
      id: Math.random().toString(16).slice(2),
      direction: "gasto",
      nature: "consumo",
      status: "pago",
      statusDate: "2026-10-12",
      noteDate: "2026-10-12",
      dueDate: "",
      amountMinor: 0,
      category: "Alimentação",
      merchant: "",
      archived: false,
      documentId: "",
      fingerprint: "",
    },
    partial
  );
}

const summary = calc.summarize(
  [
    entry({ id: "r", direction: "ganho", status: "recebido", statusDate: "2026-10-05", amountMinor: 250000, category: "Salário" }),
    entry({ id: "p", direction: "gasto", status: "pago", statusDate: "2026-10-12", amountMinor: 100000, category: "Moradia" }),
    entry({ id: "ap", direction: "gasto", status: "a_pagar", statusDate: "", dueDate: "2026-10-20", amountMinor: 80000, category: "Saúde" }),
    entry({ id: "ar", direction: "ganho", status: "a_receber", statusDate: "", dueDate: "2026-10-25", amountMinor: 40000, category: "Serviços" }),
    entry({ id: "tr", direction: "gasto", nature: "transferencia", status: "pago", statusDate: "2026-10-08", amountMinor: 500000 }),
    entry({ id: "nov", direction: "gasto", status: "pago", statusDate: "2026-11-02", noteDate: "2026-10-30", amountMinor: 1500 }),
  ],
  month
);

assert.equal(summary.received, 250000);
assert.equal(summary.paid, 100000);
assert.equal(summary.result, 150000);
assert.equal(summary.toPay, 80000);
assert.equal(summary.toReceive, 40000);
assert.equal(summary.excluded, 500000);
assert.equal(summary.paidByCategory.Moradia, 100000);

const unpaidNote = calc.summarize(
  [entry({ status: "a_pagar", statusDate: "", dueDate: "2026-11-03", noteDate: "2026-10-30", amountMinor: 4280 })],
  month
);
assert.equal(unpaidNote.paid, 0);
assert.equal(unpaidNote.toPay, 0);

const paidNext = calc.summarize(
  [entry({ status: "pago", statusDate: "2026-11-02", noteDate: "2026-10-30", amountMinor: 4280 })],
  "2026-11"
);
assert.equal(paidNext.paid, 4280);

const first = entry({
  id: "a",
  merchant: "Padaria do Largo",
  noteDate: "2026-10-12",
  amountMinor: 4280,
  documentId: "ISA-NOTA-100",
  fingerprint: "img-100",
});
const secondPhoto = entry({
  id: "b",
  merchant: "Padaria do Largo",
  noteDate: "2026-10-12",
  amountMinor: 4280,
  documentId: "ISA-NOTA-100",
  fingerprint: "img-100",
});
assert.equal(calc.findDuplicate(secondPhoto, [first]).kind, "documento");

const onlyAmountDate = entry({
  id: "c",
  merchant: "Outro lugar",
  noteDate: "2026-10-12",
  amountMinor: 4280,
  documentId: "",
  fingerprint: "",
});
assert.equal(calc.findDuplicate(onlyAmountDate, [first]), null);
assert.equal(calc.sameAmountAndDateOnly(onlyAmountDate, [first]), true);

const linked = calc.summarize(
  [
    entry({ id: "manual", direction: "gasto", status: "pago", statusDate: "2026-10-03", amountMinor: 4000, source: "digitado", linkId: "banco" }),
    entry({ id: "banco", direction: "gasto", status: "pago", statusDate: "2026-10-03", amountMinor: 4000, source: "extrato-sintetico", nature: "a_conferir", linkId: "manual" }),
  ],
  month
);
assert.equal(linked.paid, 4000);
assert.equal(linked.aside, 0);

const partial = calc.summarize(
  [
    entry({ id: "saida", nature: "a_conferir", source: "exemplo-sintetico", direction: "gasto", status: "pago", statusDate: "2026-10-03", amountMinor: 4000, category: "" }),
    entry({ id: "gasto", nature: "consumo", direction: "gasto", status: "pago", statusDate: "2026-10-04", amountMinor: 2790, category: "", categorizationStatus: "a_categorizar" }),
    entry({ id: "rende", nature: "bb_rende_facil", source: "exemplo-sintetico", direction: "ganho", status: "recebido", statusDate: "2026-10-02", amountMinor: 350 }),
  ],
  month
);
assert.equal(partial.paid, 2790);
assert.equal(partial.received, 0);
assert.equal(partial.unidentified, 1);
assert.equal(partial.bankOut, 4000);
assert.equal(partial.rende, 350);
assert.equal(partial.paidByCategory["A categorizar"], 2790);

const legacyFile = calc.summarize([
  entry({ id: "antigo", nature: "a_conferir", source: "arquivo-teste", direction: "gasto", status: "pago", statusDate: "2026-10-03", amountMinor: 4000, category: "" }),
], month);
const realFile = calc.summarize([
  entry({ id: "real", nature: "a_conferir", source: "extrato-bb-arquivo", direction: "gasto", status: "pago", statusDate: "2026-10-03", amountMinor: 4000, category: "" }),
], month);
assert.deepEqual(
  { unidentified: realFile.unidentified, bankOut: realFile.bankOut, paid: realFile.paid },
  { unidentified: legacyFile.unidentified, bankOut: legacyFile.bankOut, paid: legacyFile.paid }
);

console.log("calc ok");
