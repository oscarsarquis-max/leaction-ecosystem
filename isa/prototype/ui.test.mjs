import { createRequire } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const ui = require("./ui.js");

function channel(hex, index) {
  const value = parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16) / 255;
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function contrast(front, back) {
  const lum = function (hex) {
    return 0.2126 * channel(hex, 0) + 0.7152 * channel(hex, 1) + 0.0722 * channel(hex, 2);
  };
  const left = lum(front);
  const right = lum(back);
  const hi = Math.max(left, right);
  const lo = Math.min(left, right);
  return (hi + 0.05) / (lo + 0.05);
}

const entrada = ui.amount(150000, "entrada");
assert.match(entrada, /class="amt num in"/);
assert.match(entrada, /↑ R\$ 1\.500,00/);
assert.match(entrada, /aria-label="Entrada de R\$ 1\.500,00"/);

const saida = ui.amount(18640, "saida");
assert.match(saida, /class="amt num out"/);
assert.match(saida, /↓ − R\$ 186,40/);
assert.match(saida, /aria-label="Saída de R\$ 186,40"/);
assert.match(saida, /−/);

const agora = ui.monthControl({ title: "Outubro de 2026", current: true, ids: { prev: "home-prev", next: "home-next", current: "home-current" } });
assert.match(agora, /aria-label="Mês anterior"/);
assert.match(agora, /aria-label="Próximo mês"/);
assert.match(agora, /<strong class="month-title">Outubro de 2026<\/strong>/);
assert.equal(agora.includes("Mês atual"), false);

const outro = ui.monthControl({ title: "Setembro de 2026", current: false });
assert.match(outro, />Mês atual</);

const grade = ui.calendar({
  month: "2026-10",
  today: "2026-10-26",
  selected: "2026-10-03",
  days: [
    { date: "2026-10-03", entrada: true, label: "Freela R$ 500,00" },
    { date: "2026-10-26", saida: true, label: "Mercado R$ 100,00" },
    { date: "2026-10-28", attention: true, label: "falta dinheiro" },
  ],
});
assert.match(grade, /Dom/);
assert.match(grade, /Sáb/);
assert.equal(/\d+ sai/.test(grade), false);
assert.equal(/\d+ entra/.test(grade), false);
assert.match(grade, /●/);
assert.match(grade, /■/);
assert.match(grade, /▲/);
assert.match(grade, /aria-label="26\. Mercado R\$ 100,00"/);
assert.match(grade, /aria-label="3\. Freela R\$ 500,00"/);
assert.ok(grade.indexOf('class="legend') > grade.indexOf("data-day=\"2026-10-31\""));
assert.match(grade, /is-today/);
assert.match(grade, /is-attention/);

const casca = ui.shell({
  signedIn: true,
  name: "Marina Alves",
  route: "#inicio",
  showAccount: true,
  accountHtml: '<label class="account-switch">Visualizando<select id="account-switch"></select></label>',
});
assert.match(casca, /Visualizando/);
assert.match(casca, /id="brand-leave"/);
assert.match(casca, /Início/);
assert.match(casca, /Lançamentos/);
assert.match(casca, /Planejar/);
assert.match(casca, /Contas/);
assert.match(casca, /Perfil/);
assert.match(casca, /\+ Registrar/);
assert.match(casca, /id="nav-registrar" aria-label="Registrar"/);
assert.match(casca, />MA</);
assert.equal((casca.match(/\+ Registrar/g) || []).length, 1);
assert.equal((casca.match(/aria-label="Registrar"/g) || []).length, 1);
assert.ok(casca.indexOf("brand-mark") < casca.indexOf("brand-initials"));
assert.ok(casca.indexOf("brand-initials") < casca.indexOf("brand-tools"));
assert.ok(casca.indexOf("account-slot") < casca.indexOf("brand-leave"));
assert.match(casca, /alt="Action Finance — ISA Personal Finance"/);
assert.match(casca, /src="marca-faixa.png"/);

const appSource = fs.readFileSync(new URL("./app.js", import.meta.url), "utf8");
assert.equal(appSource.includes("home-register"), false);
assert.equal(appSource.includes("ledger-register"), false);
assert.match(appSource, /const hideRegistrar = false/);

const tarefa = ui.shell({ signedIn: true, name: "Marina Alves", route: "#importar", task: true, taskLabel: "Cancelar", taskTitle: "Importar", hideRegistrar: true, showAccount: false });
assert.match(tarefa, /Cancelar/);
assert.equal(tarefa.includes("nav-registrar"), false);
assert.equal(tarefa.includes("account-switch"), false);

const barra = ui.limitBar({ used: 120, total: 100, pace: 0.8, label: "Limite passado" });
assert.match(barra, /fill over/);
assert.match(barra, /class="pace"/);

const pares = [
  ["tinta sobre cartão", "#15171C", "#FFFFFF"],
  ["tinta sobre fundo", "#15171C", "#F4F5F8"],
  ["texto de apoio sobre cartão", "#3A3F4C", "#FFFFFF"],
  ["rótulo sobre cartão", "#5A6072", "#FFFFFF"],
  ["rótulo sobre fundo", "#5A6072", "#F4F5F8"],
  ["branco sobre marca", "#FFFFFF", "#1800AD"],
  ["marca sobre cartão", "#1800AD", "#FFFFFF"],
  ["entrada sobre cartão", "#0F766E", "#FFFFFF"],
  ["saída sobre cartão", "#B4441C", "#FFFFFF"],
  ["atenção sobre faixa", "#7A4E00", "#FFF4DF"],
  ["título da faixa", "#5C3A00", "#FFF4DF"],
];
pares.forEach(function (pair) {
  const ratio = contrast(pair[1], pair[2]);
  assert.ok(ratio >= 4.5, pair[0] + " " + ratio.toFixed(2));
  console.log(pair[0] + ": " + ratio.toFixed(2) + ":1");
});

const html = fs.readFileSync(new URL("./index.html", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("./styles.css", import.meta.url), "utf8");
assert.equal(html.includes("fonts.bunny.net"), false);
assert.equal(css.includes("Geist Mono"), false);
assert.match(html, /fonts\/fonts\.css/);
assert.match(css, /--marca: #1800AD/);
assert.match(css, /--entrada: #0F766E/);

console.log("ui ok");
