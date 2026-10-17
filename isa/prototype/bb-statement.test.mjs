import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const bb = require("./bb-statement.js");

const fixture = fs.readFileSync(new URL("./fixtures/bb-extrato-sintetico.csv", import.meta.url));
const overlapFile = fs.readFileSync(new URL("./fixtures/bb-extrato-sintetico-sobreposicao.csv", import.meta.url));
const read = bb.readStatement(fixture);
assert.equal(read.ok, true);
assert.equal(read.encoding, "utf-8");
assert.equal(read.counts.movements, 8);
assert.equal(read.counts.balances, 5);
assert.equal(read.counts.entries, 2);
assert.equal(read.counts.exits, 6);
assert.equal(read.counts.rendeFacil, 2);
assert.equal(read.chain.ok, true);
assert.equal(read.movements.length + read.balances.length, read.rows.length);
assert.notEqual(read.rows.length, read.counts.movements);

const saldoFinal = read.balances.find(function (row) { return row.class === "saldo_informado"; });
assert.equal(saldoFinal.date, "2026-10-16");
assert.equal(saldoFinal.cents, 84350);
assert.equal("s a l d o".includes("saldo"), false);
assert.equal(bb.balanceClass("S A L D O"), "saldo_informado");
assert.equal(bb.balanceClass("Pagamento de saldo devedor"), "");

const mentioned = read.movements.find(function (row) { return row.history === "Pagamento de saldo devedor"; });
assert.equal(mentioned.class, "saida");
assert.equal(mentioned.cents, -800);

const docs = {};
read.movements.forEach(function (row) {
  docs[row.document] = (docs[row.document] || 0) + 1;
});
assert.equal(docs["000123"], 2);
assert.equal(docs["009001"], 2);
assert.equal(docs["12.345-6"], 1);
const sameDoc = read.movements.filter(function (row) { return row.document === "009001"; });
assert.equal(sameDoc[0].cents !== sameDoc[1].cents, true);
assert.equal(sameDoc[0].date, "2026-10-02");
assert.notEqual(sameDoc[0].class, sameDoc[1].class);

const twins = read.movements.filter(function (row) { return row.document === "555"; });
assert.equal(twins.length, 2);
assert.equal(bb.lineSignature(twins[0]), bb.lineSignature(twins[1]));
const firstGroups = bb.compareOverlap([], read.rows);
const twinGroup = firstGroups.find(function (group) { return group.incoming === 2 && group.rows[0].document === "555"; });
assert.equal(twinGroup.status, "nova");

const pix = read.movements.find(function (row) { return row.history === "Pix recebido"; });
assert.equal(pix.meio, "pix");
assert.equal(pix.family, "");
assert.equal(pix.details, "Nota, exemplo");
assert.equal(pix.document, "000123");
const rende = read.movements.filter(function (row) { return row.family === "bb_rende_facil"; });
assert.equal(rende.length, 2);
assert.ok(rende.every(function (row) { return row.meio === ""; }));

assert.equal(bb.parseDate("01/10/2026"), "2026-10-01");
assert.equal(bb.parseDate("31/02/2026"), "");
assert.equal(bb.parseCents("0,00"), 0);
assert.equal(bb.parseCents("1.234,56"), 123456);
assert.equal(bb.parseCents("-1.234,56"), -123456);
assert.equal(bb.parseCents("10.50"), null);

const zero = bb.parseStatement(
  '"Data","Lançamento","Detalhes","N° documento","Valor","Tipo Lançamento"\n' +
  '"01/10/2026","Saldo Anterior","","","0,00",""\n' +
  '"01/10/2026","S A L D O","","","0,00",""\n'
);
assert.equal(zero.ok, true);
assert.equal(zero.chain.ok, true);
assert.equal(zero.balances[1].cents, 0);
assert.equal(zero.counts.movements, 0);

const shifted = bb.parseStatement(
  '"Data","Lançamento","Detalhes","N° documento","Valor","Tipo Lançamento"\n' +
  '"01/10/2026","Pix","","1","10,00"\n'
);
assert.equal(shifted.ok, false);
assert.equal(shifted.rows.length, 0);
assert.match(shifted.error, /6 colunas/);

const badSign = bb.parseStatement(
  '"Data","Lançamento","Detalhes","N° documento","Valor","Tipo Lançamento"\n' +
  '"01/10/2026","Saldo Anterior","","","10,00",""\n' +
  '"02/10/2026","Pix","","1","-5,00","Entrada"\n'
);
assert.equal(badSign.ok, false);
assert.match(badSign.error, /sinal/);

function encode1252(text) {
  const bytes = [];
  for (const ch of text) {
    const code = ch.codePointAt(0);
    const map = { 231: 0xe7, 227: 0xe3, 176: 0xb0, 237: 0xed, 225: 0xe1, 250: 0xfa };
    if (code < 128) bytes.push(code);
    else if (map[code]) bytes.push(map[code]);
    else throw new Error("sem byte");
  }
  return Uint8Array.from(bytes);
}

const legacyText =
  '"Data","Lançamento","Detalhes","N° documento","Valor","Tipo Lançamento"\n' +
  '"30/09/2026","Saldo Anterior","","","10,00",""\n' +
  '"01/10/2026","Pix","São Paulo","0007","2,00","Entrada"\n' +
  '"01/10/2026","S A L D O","","","12,00",""\n';
const legacy = bb.readStatement(encode1252(legacyText));
assert.equal(legacy.encoding, "windows-1252");
assert.equal(legacy.ok, true);
assert.equal(legacy.chain.ok, true);
assert.equal(legacy.counts.movements, 1);
assert.equal(legacy.movements[0].details, "São Paulo");
assert.equal(legacy.text, undefined);

const again = bb.readStatement(fixture);
assert.equal(again.batchId, read.batchId);
const other = bb.readStatement(overlapFile);
assert.notEqual(other.batchId, read.batchId);
assert.equal(other.chain.ok, true);

const prior = read.rows.map(bb.lineSignature);
const compared = bb.compareOverlap(prior, other.rows);
const card = compared.find(function (group) { return group.rows[0].document === "555"; });
const fresh = compared.find(function (group) { return group.rows[0].document === "888"; });
assert.equal(card.status, "candidata");
assert.equal(card.incoming, 2);
assert.equal(card.already, 2);
assert.equal(fresh.status, "nova");

const stored = read.movements.filter(function (row) { return row.document === "555"; }).map(function (row) {
  return { signature: bb.lineSignature(row), state: "incorporada" };
});
const firstPlan = bb.planOccurrences([], read.movements);
assert.equal(firstPlan.importRows.length, read.movements.length);
assert.equal(firstPlan.pendingRows.length, 0);
const secondPlan = bb.planOccurrences(stored, other.movements);
assert.equal(secondPlan.importRows.filter(function (row) { return row.document === "888"; }).length, 1);
assert.equal(secondPlan.pendingRows.filter(function (row) { return row.document === "555"; }).length, 2);
const withPending = stored.concat(secondPlan.pendingRows.map(function (row) {
  return { signature: bb.lineSignature(row), state: "pendente" };
}));
const thirdPlan = bb.planOccurrences(withPending, other.movements);
assert.equal(thirdPlan.pendingRows.length, 0);
assert.equal(thirdPlan.reused, 2);
assert.equal(withPending.filter(function (item) { return item.state === "incorporada"; }).length, 2);
const decidedSame = stored.map(function (item) { return { signature: item.signature, state: "mesma" }; }).concat(stored);
const pointed = bb.planOccurrences(decidedSame, other.movements.filter(function (row) { return row.document === "555"; }));
assert.equal(pointed.pendingRows.length, 0);
assert.equal(pointed.importRows.length, 0);
assert.equal(pointed.reused, 2);

const thirdFile = fs.readFileSync(new URL("./fixtures/bb-extrato-sintetico-terceira.csv", import.meta.url));
const third = bb.readStatement(thirdFile);
assert.equal(third.ok, true);
assert.equal(third.chain.ok, true);
assert.notEqual(third.batchId, other.batchId);
assert.equal(third.counts.movements, 4);

const emptyFile = bb.parseStatement("");
assert.equal(emptyFile.ok, false);
assert.equal(emptyFile.rows.length, 0);

console.log("bb-statement ok");
