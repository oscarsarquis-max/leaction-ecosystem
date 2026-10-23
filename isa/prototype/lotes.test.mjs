import { createRequire } from "node:module";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
const lotes = require("./lotes.js");

const paid = [
  { id: "a", direction: "gasto", nature: "consumo", status: "pago", amountMinor: 10000, currency: "BRL", category: "Alimentação" },
  { id: "b", direction: "gasto", nature: "consumo", status: "pago", amountMinor: 2790, currency: "BRL", category: "" },
];
const totals = lotes.summarize(paid);
assert.equal(totals.byCurrency.BRL.gastosPagos, 12790);
const comp = lotes.composition(paid, "BRL", "pagos");
assert.equal(comp.total, 12790);
paid[1].category = "Transporte";
assert.equal(lotes.composition(paid, "BRL", "pagos").total, 12790);

const mixed = lotes.summarize([
  { direction: "gasto", nature: "consumo", status: "pago", amountMinor: 15380, currency: "BRL", category: "Alimentação" },
  { direction: "gasto", nature: "consumo", status: "a_pagar", amountMinor: 10000, currency: "BRL" },
  { direction: "ganho", nature: "consumo", status: "recebido", amountMinor: 5000, currency: "BRL" },
  { direction: "gasto", nature: "transferencia", status: "pago", amountMinor: 20000, currency: "BRL" },
  { direction: "gasto", nature: "consumo", status: "pago", amountMinor: 500, currency: "USD" },
]);
assert.equal(mixed.byCurrency.BRL.gastosPagos, 15380);
assert.equal(mixed.byCurrency.BRL.gastosAPagar, 10000);
assert.equal(mixed.byCurrency.BRL.ganhosRecebidos, 5000);
assert.equal(mixed.byCurrency.BRL.transferencias, 20000);
assert.equal(mixed.byCurrency.USD.gastosPagos, 500);
assert.equal(lotes.fold("Táxi"), "taxi");
console.log("lotes ok");
