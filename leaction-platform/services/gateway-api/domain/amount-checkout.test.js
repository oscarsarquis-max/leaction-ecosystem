const test = require("node:test");
const assert = require("node:assert/strict");
const { returnOriginAllowed } = require("./amount-checkout");
const { authenticateApp } = require("./entitlements-api");

test("checkout avulso só aceita a origem cadastrada, sem curinga", () => {
  const allowed = ["https://lojadepaes.com.br"];
  assert.equal(returnOriginAllowed("https://lojadepaes.com.br", allowed).ok, true);
  assert.equal(returnOriginAllowed("https://outra.example", allowed).ok, false);
  assert.equal(returnOriginAllowed("https://lojadepaes.com.br", []).ok, false);
  assert.equal(returnOriginAllowed("https://lojadepaes.com.br", ["*"]).ok, false);
  assert.equal(returnOriginAllowed("https://lojadepaes.com.br", null).ok, false);
});

test("autenticação do app devolve as origens cadastradas", async () => {
  let sql = "";
  const pool = {
    query: async (text) => {
      sql = text;
      return {
        rows: [
          {
            app_id: "lojadepaes",
            name: "Loja",
            active: true,
            webhook_secret: "segredo-de-teste",
            webhook_url: "https://lojadepaes.com.br/api/v1/webhooks/actionhub",
            return_origins: ["https://lojadepaes.com.br"],
          },
        ],
      };
    },
  };
  const auth = await authenticateApp(pool, "lojadepaes", "segredo-de-teste");
  assert.equal(auth.ok, true);
  assert.deepEqual(auth.app.return_origins, ["https://lojadepaes.com.br"]);
  assert.match(sql, /return_origins/);
  assert.match(sql, /webhook_url/);
});
