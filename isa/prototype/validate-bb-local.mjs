import { createRequire } from "node:module";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const bb = require("./bb-statement.js");
const file = process.argv[2];
if (!file) {
  console.error("Informe o caminho do CSV. O resultado não inclui linhas nem valores.");
  process.exit(2);
}
const bytes = fs.readFileSync(file);
let utf8 = true;
try {
  new TextDecoder("utf-8", { fatal: true }).decode(bytes);
} catch (err) {
  utf8 = false;
}
const read = bb.readStatement(bytes);
const summary = {
  bytes: bytes.length,
  bom: bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf,
  utf8: utf8,
  encoding: read.encoding,
  ok: read.ok,
  movements: read.ok ? read.counts.movements : 0,
  balances: read.ok ? read.counts.balances : 0,
  entries: read.ok ? read.counts.entries : 0,
  exits: read.ok ? read.counts.exits : 0,
  chainClosed: !!(read.ok && read.chain.ok),
};
console.log(JSON.stringify(summary));
if (!read.ok || summary.movements !== 53 || summary.balances !== 11 || !summary.chainClosed) process.exit(1);
