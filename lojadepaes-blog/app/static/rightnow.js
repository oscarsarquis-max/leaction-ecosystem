(function () {
  "use strict";
  var store = {
    get: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { window.localStorage.setItem(k, v); } catch (e) {} }
  };

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      if (!r.ok) { var err = new Error("http " + r.status); err.status = r.status; throw err; }
      return r.json();
    });
  }

  // Quero!
  Array.prototype.forEach.call(document.querySelectorAll(".rn-quero"), function (btn) {
    var slug = btn.getAttribute("data-slug");
    if (store.get("lp_quero_" + slug) === "1") { btn.setAttribute("aria-pressed", "true"); }
    btn.addEventListener("click", function () {
      if (btn.getAttribute("aria-pressed") === "true" || btn.disabled) { return; }
      btn.disabled = true;
      post("/api/rn/quero", { slug: slug }).then(function (data) {
        btn.setAttribute("aria-pressed", "true");
        store.set("lp_quero_" + slug, "1");
        var count = btn.querySelector(".rn-count");
        if (count && typeof data.count === "number") { count.textContent = String(data.count); }
      }).catch(function () {}).then(function () { btn.disabled = false; });
    });
  });

  // Compartilhar (curiosidade): usa o menu nativo quando houver; senão segue o link do WhatsApp
  if (navigator.share) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-share]"), function (a) {
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        navigator.share({ text: a.getAttribute("data-share") }).catch(function () {});
      });
    });
  }

  // Enquete
  var box = document.getElementById("rn-poll");
  if (!box || !window.fetch) { return; }
  var lang = box.getAttribute("data-lang") || "pt";

  function endsLabel(iso) {
    if (!iso) { return ""; }
    var end = new Date(String(iso).slice(0, 10) + "T12:00:00");
    var now = new Date(); now.setHours(12, 0, 0, 0);
    var days = Math.round((end - now) / 86400000);
    if (days < 0) { return ""; }
    if (days === 0) { return box.getAttribute("data-ends-today"); }
    if (days === 1) { return box.getAttribute("data-ends-tomorrow"); }
    return box.getAttribute("data-ends-in").replace("{n}", String(days));
  }

  function render(poll, mine) {
    box.querySelector(".rn-poll-q").textContent = poll.pergunta || "";
    box.querySelector(".rn-poll-ends").textContent = endsLabel(poll.fecha_em);
    var list = box.querySelector(".rn-poll-options");
    list.textContent = "";
    var results = {};
    (poll.resultado || []).forEach(function (r) { results[r.id] = r.pct; });
    var voted = !!poll.votou || !!poll.resultado;
    (poll.opcoes || []).forEach(function (opt) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "rn-opt" + (mine && mine === String(opt.id) ? " is-mine" : "");
      var bar = document.createElement("i"); bar.className = "bar"; bar.setAttribute("aria-hidden", "true");
      var label = document.createElement("span"); label.textContent = opt.texto;
      var pct = document.createElement("span");
      b.appendChild(bar); b.appendChild(label); b.appendChild(pct);
      if (voted) {
        var value = Math.round(results[opt.id] || 0);
        pct.textContent = value + "%";
        b.disabled = true;
        b.setAttribute("aria-label", opt.texto + ": " + value + "%");
        window.requestAnimationFrame(function () { bar.style.width = value + "%"; });
      } else {
        b.addEventListener("click", function () { vote(poll, opt.id); });
      }
      list.appendChild(b);
    });
    if (voted && typeof poll.total === "number") {
      var note = box.querySelector(".rn-poll-note");
      note.textContent = poll.total + " " + box.getAttribute("data-votes");
    }
    box.hidden = false;
  }

  function vote(poll, optionId) {
    Array.prototype.forEach.call(box.querySelectorAll(".rn-opt"), function (b) { b.disabled = true; });
    post("/api/rn/enquete/voto", { enquete_id: poll.id, opcao_id: optionId }).then(function (data) {
      store.set("lp_poll_" + poll.id, String(optionId));
      poll.resultado = data.resultado; poll.total = data.total; poll.votou = true;
      render(poll, String(optionId));
      var note = box.querySelector(".rn-poll-note");
      note.textContent = box.getAttribute("data-thanks") + " · " + note.textContent;
    }).catch(function (err) {
      if (err && err.status === 409) { load(); return; }
      Array.prototype.forEach.call(box.querySelectorAll(".rn-opt"), function (b) { b.disabled = false; });
      box.querySelector(".rn-poll-note").textContent = box.getAttribute("data-error");
    });
  }

  function load() {
    fetch("/api/rn/enquete?idioma=" + encodeURIComponent(lang), { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (poll) {
        if (!poll || !poll.id || !poll.opcoes || !poll.opcoes.length) { return; }
        render(poll, store.get("lp_poll_" + poll.id));
      })
      .catch(function () {});
  }
  load();
})();
