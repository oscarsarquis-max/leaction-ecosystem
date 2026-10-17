(function () {
  "use strict";
  var timer, latest = null, busy = false, seen = {}, pendingBefore = 0;
  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function(c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function brl(v) { return v == null ? "Ainda não informado" : new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(v/100); }
  function date(v) { return v ? v.slice(0,10).split("-").reverse().join("/") : ""; }
  function request(method, path, body) {
    return fetch(path, {method:method, credentials:"include",headers:{"Content-Type":"application/json"},body:body === undefined ? undefined : JSON.stringify(body)})
      .then(function(r) { return r.json().then(function(data) { if (!r.ok) throw new Error(data.error || "Não foi possível concluir. Tente de novo."); return data; }); });
  }
  function event(id, kind) { return request("POST", "/api/ai/suggestions/"+encodeURIComponent(id)+"/events", {event:kind}); }
  function measure(label, value) { return '<div><span>'+esc(label)+'</span><strong>'+esc(value)+'</strong></div>'; }
  function resultHtml(job) {
    if (!job) return '<p>A ISA considera seus compromissos e o dinheiro disponível para ajudar no próximo passo.</p>';
    if (job.status === "queued" || job.status === "running") return '<p role="status">A ISA está olhando seus dados. Você pode continuar usando o aplicativo.</p>';
    if (job.status === "failed") return '<p role="status">'+esc(job.message)+'</p>';
    var r = job.result;
    if (!r) return "";
    var p = r.current || {}, option = r.option, html = '';
    if (r.stale) html += '<p class="note">Seus dados mudaram. Esta análise ficou no histórico; peça uma nova antes de decidir.</p>';
    html += '<p class="ai-summary">'+esc(r.summary)+'</p>';
    if (p.complete) {
      html += '<div class="ai-metrics">'+measure("Menor disponível · "+date(p.minimum.date),brl(p.minimum.cents))+
        measure("Margem adicional no período",brl(p.margin.capacity_cents))+'</div>';
      html += '<p class="muted">Projeção até '+date(p.horizon_end)+', com os compromissos informados. Confira se falta alguma conta.</p>';
    } else html += '<p class="note">'+esc((p.missing || []).join(" "))+'</p>';
    html += '<h3>Seu próximo passo</h3><p>'+esc(r.nextStep)+'</p>';
    if (r.question) html += '<p class="ai-question">'+esc(r.question)+'</p>';
    if (r.expense) {
      var e = r.expense;
      html += '<div class="ai-alternative"><h3>Se gastar '+brl(e.request.cents)+'</h3>'+
        (e.result.complete ? '<p>Menor disponível: <strong>'+brl(e.result.minimum.cents)+'</strong> em '+date(e.result.minimum.date)+'.</p>' : '<p>Faltam informações para avaliar esse gasto.</p>')+'</div>';
    }
    if (option) html += '<div class="ai-alternative"><h3>Uma possibilidade para comparar</h3><p>'+esc(option.label)+' em '+date(option.changes[0].dueOn)+
      '.</p><p>O menor disponível seria <strong>'+brl(option.result.minimum.cents)+'</strong>.</p><p class="muted">Depende de combinar a data com o credor. Os custos ainda não foram informados. O vencimento continua igual.</p></div>';
    if (r.sources && r.sources.length) html += '<details><summary>De onde veio esta análise</summary><ul>'+r.sources.map(function(s) { return '<li>'+esc(s.description)+' · '+brl(s.cents)+' · '+date(s.on)+'</li>'; }).join("")+'</ul></details>';
    html += '<p class="muted">Análise salva em '+date(job.createdAt)+'. Claude na AWS; valores calculados pela ISA.</p>';
    if (r.decision === "aceita") html += '<p class="oknote">Plano escolhido salvo. O vencimento original não mudou.</p>';
    else if (!r.stale) html += '<div class="ai-actions">'+(option ? '<button class="secondary" data-ai-event="aceita" data-ai-id="'+esc(r.suggestionId)+'">Guardar como plano escolhido</button>' : '')+'<button class="quiet" data-ai-event="adiada" data-ai-id="'+esc(r.suggestionId)+'">Ver depois</button><button class="quiet" data-ai-event="recusada" data-ai-id="'+esc(r.suggestionId)+'">Não me ajuda</button></div>';
    return html;
  }
  function draw() {
    var box = document.getElementById("isa-ai-result");
    if (!box) return;
    var job = latest && latest.plans[0];
    box.innerHTML = resultHtml(job);
    var btn = document.getElementById("isa-ai-send");
    if (btn) { btn.disabled = busy || !!(job && (job.status === "queued" || job.status === "running")); btn.textContent = btn.disabled ? "Analisando…" : "Pedir ajuda à ISA"; }
    var history = document.getElementById("isa-ai-history");
    if (history && latest) history.innerHTML = latest.plans.length > 1 ? '<details><summary>Análises anteriores</summary>'+latest.plans.slice(1).map(function(j) { return '<article class="ai-history-item">'+resultHtml(j)+'</article>'; }).join("")+'</details>' : "";
    box.querySelectorAll("[data-ai-event]").forEach(function(b) {
      b.onclick = function() { b.disabled = true; event(b.dataset.aiId,b.dataset.aiEvent).then(function(r) { b.textContent = r.message || "Guardado"; }).catch(function(err) { b.disabled = false; b.textContent = err.message; }); };
    });
    if (job && job.result && !seen[job.id]) { seen[job.id] = true; event(job.result.suggestionId,"apresentada").catch(function() { delete seen[job.id]; }); }
  }
  function poll() {
    clearTimeout(timer);
    if (!window.isaPublic || !document.getElementById("nav-inicio")) return;
    request("GET","/api/ai/status").then(function(data) {
      latest = data; draw();
      var note = document.getElementById("isa-ai-categories");
      if (note) note.textContent = data.pendingCategories ? "A ISA está organizando suas categorias. Os lançamentos já estão salvos." :
        data.failedCategories ? "Algumas categorias ainda precisam de ajuda. Você pode tentar a análise novamente." : "A ISA organiza as categorias depois de salvar. Você pode corrigir qualquer uma.";
      if (pendingBefore && !data.pendingCategories && window.isaRefreshEntries) window.isaRefreshEntries();
      pendingBefore = data.pendingCategories;
      var working = data.pendingCategories || data.plans.some(function(j) { return j.status === "queued" || j.status === "running"; });
      if (working) timer = setTimeout(poll, 3500);
    }).catch(function() { var node = document.getElementById("isa-ai-result"); if (node && !latest) node.textContent = "Seus dados estão salvos. Não foi possível consultar a ajuda agora."; });
  }
  function submit(e) {
    e.preventDefault();
    var payload = {question:document.getElementById("isa-ai-question").value};
    var raw = document.getElementById("isa-ai-amount").value.trim();
    if (raw) {
      if (!/^\d+(,\d{1,2})?$/.test(raw)) { document.getElementById("isa-ai-result").textContent = "Use um valor como 50,00."; return; }
      payload.amountCents = Math.round(Number(raw.replace(",","."))*100);
    }
    busy = true; draw();
    request("POST","/api/ai/analyze",payload).then(function(j) {
      busy = false;
      if (j.status === "unavailable") { document.getElementById("isa-ai-result").textContent = j.message; return; }
      latest = {plans:[j]}; draw(); poll();
    }).catch(function(err) { busy = false; draw(); document.getElementById("isa-ai-result").textContent = err.message; });
  }
  function gapAction(gap) {
    if (gap === "availability") return { href: "#planejar/disponivel", label: "Informar dinheiro disponível" };
    if (gap === "inflow") return { href: "#planejar/entrada", label: "Informar a próxima entrada" };
    if (gap === "commitments" || gap === "commitment-values") return { href: "#planejar/contas", label: "Informar contas a pagar" };
    return null;
  }
  function buildCard(gap) {
    var card = document.createElement("section");
    card.id = "isa-ai-card"; card.className = "ai-card"; card.setAttribute("aria-labelledby","isa-ai-title");
    var action = gapAction(gap);
    var missing = action ? '<p class="note">Ainda falta informação para uma análise completa. Você não precisa escrever o valor aqui.</p><a class="secondary plan-gap-link" href="'+action.href+'">'+esc(action.label)+'</a>' : "";
    card.innerHTML = '<div class="ai-card-heading"><span class="ai-star" aria-hidden="true">✦</span><div><p class="ai-eyebrow">Sua ajuda com o dinheiro</p><h2 id="isa-ai-title">Vamos organizar o próximo passo?</h2></div></div>'+
      missing + '<div id="isa-ai-result" aria-live="polite"></div><form id="isa-ai-form" class="stack"><label for="isa-ai-question">O que você quer resolver?</label><textarea id="isa-ai-question" maxlength="500" rows="2" placeholder="Meu dinheiro chega até o próximo pagamento?"></textarea>'+
      '<details><summary>Quero avaliar um gasto</summary><label for="isa-ai-amount">Quanto pretende gastar agora?</label><input id="isa-ai-amount" inputmode="decimal" placeholder="Informe o valor"></details>'+
      '<button id="isa-ai-send" class="primary" type="submit">Pedir ajuda à ISA</button></form><p class="muted ai-privacy">A ISA usa o Claude na AWS para interpretar os dados necessários à análise. Nenhum pagamento é feito por ela.</p><div id="isa-ai-history"></div>';
    return card;
  }
  function bindCard(card) {
    var form = card.querySelector("#isa-ai-form");
    if (form) form.onsubmit = submit;
  }
  function place(mode, gap) {
    if (!window.isaPublic) return;
    var current = document.getElementById("isa-ai-card");
    if (mode === "quiet") {
      if (current) current.remove();
      return;
    }
    var slot = document.getElementById(mode === "help" ? "plan-help-slot" : "plan-ai-slot");
    if (!slot) return;
    slot.hidden = false;
    if (current) current.remove();
    var card = buildCard(gap || slot.getAttribute("data-gap") || "");
    slot.appendChild(card);
    bindCard(card);
    draw();
    poll();
  }
  function mount() {
    if (!window.isaPublic || !document.getElementById("nav-inicio")) { latest = null; clearTimeout(timer); return; }
    var hash = location.hash || "", root = document.getElementById("app"), title = root.querySelector("h1");
    if (hash === "#inicio" && document.getElementById("isa-ai-card")) document.getElementById("isa-ai-card").remove();
    if ((hash === "#planejar" || hash.indexOf("#planejar/") === 0) && document.getElementById("isa-ai-card") && !document.getElementById("plan-ai-slot")) {
      document.getElementById("isa-ai-card").remove();
    }
    if (hash === "#lancamentos" && !document.getElementById("isa-ai-categories")) {
      var note = document.createElement("p"); note.id = "isa-ai-categories"; note.className = "ai-reason"; title.insertAdjacentElement("afterend",note);
      var retry = document.createElement("button"); retry.className = "quiet"; retry.textContent = "Organizar categorias pendentes";
      note.insertAdjacentElement("afterend",retry); retry.onclick = function() { retry.disabled = true; request("POST","/api/ai/categorize",{}).then(function() { poll(); retry.disabled = false; }).catch(function() { retry.disabled = false; }); };
    }
  }
  window.IsaAssistant = {mount:mount, place:place};
  mount();
})();
