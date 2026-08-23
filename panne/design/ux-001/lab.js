const params = new URLSearchParams(location.search);
const state = {
  direcao: params.get("dir") || "aprovada",
  tela: params.get("tela") || "login",
  papel: params.get("papel") || "gestor",
  menu: params.get("menu") || "",
  assistente: params.get("assistente") === "1",
  assistenteTipo: params.get("guia") || "primeiros",
  selecionado: 0,
  densidade: params.get("densidade") || "media",
  estado: params.get("estado") || "ok",
};

const direcoes = [
  ["aprovada", "Direção aprovada — Oficina + Atelier"],
  ["atelier", "Atelier (histórico)"],
  ["oficina", "Oficina (histórico)"],
  ["mesa", "Mesa (histórico)"],
];

const telas = [
  ["login", "Login"],
  ["inicio", "Início autenticado"],
  ["quadro", "Quadro"],
  ["ingredientes", "Ingredientes"],
  ["ingrediente", "Assistente de ingrediente"],
  ["receita", "Laboratório de receita"],
  ["operacional", "Ordem em execução"],
  ["ficha", "Ficha"],
  ["tokens", "Sistema de design"],
  ["comparar", "Comparação"],
];

function aprovada() {
  return state.direcao === "aprovada";
}

function menusDe(id) {
  const items = UX001.menus[id] || [];
  if (aprovada() && id === "receitas") {
    return items.filter((item) => item !== "Propostas assistidas");
  }
  return items;
}

function syncUrl() {
  const next = new URLSearchParams({
    dir: state.direcao,
    tela: state.tela,
    papel: state.papel,
    menu: state.menu,
    assistente: state.assistente ? "1" : "0",
    guia: state.assistenteTipo,
    densidade: state.densidade,
    estado: state.estado,
  });
  history.replaceState(null, "", `${location.pathname}?${next}`);
}

function pode(campo) {
  return UX001.papeis[state.papel][campo];
}

function badge(tone, text) {
  return `<span class="badge badge-${tone}">${text}</span>`;
}

function brandMarkup() {
  if (state.tela === "login") return "";
  if (aprovada()) {
    return `<a class="brand" href="#" data-go="inicio">
      <img class="horizontal" src="imagens/aprovados/horizontal-escuro.png" alt="Panne" />
      <img class="compacto" src="imagens/aprovados/compacto-escuro.png" alt="Panne" />
    </a>`;
  }
  const src =
    state.direcao === "atelier"
      ? "imagens/assinatura-horizontal-clara.png"
      : "imagens/cabecalho-compacto-escuro.png";
  return `<a class="brand" href="#" data-go="inicio"><img src="${src}" alt="Panne" /></a>`;
}

function renderMeta() {
  return `
    <div class="lab-meta no-print">
      <strong>Laboratório UX — não é a aplicação produtiva</strong>
      <label>Direção
        <select id="dir">${direcoes.map(([id, label]) => `<option value="${id}" ${state.direcao === id ? "selected" : ""}>${label}</option>`).join("")}</select>
      </label>
      <label>Tela
        <select id="tela">${telas.map(([id, label]) => `<option value="${id}" ${state.tela === id ? "selected" : ""}>${label}</option>`).join("")}</select>
      </label>
      <label>Papel
        <select id="papel">${Object.entries(UX001.papeis).map(([id, p]) => `<option value="${id}" ${state.papel === id ? "selected" : ""}>${p.nome}</option>`).join("")}</select>
      </label>
      <label>Menu
        <select id="menu">
          <option value="">fechado</option>
          ${Object.keys(UX001.menus).map((id) => `<option value="${id}" ${state.menu === id ? "selected" : ""}>${id}</option>`).join("")}
        </select>
      </label>
      <label>Estado
        <select id="estado">${["ok", "vazio", "carregando", "erro", "conflito", "bloqueio"].map((e) => `<option ${state.estado === e ? "selected" : ""}>${e}</option>`).join("")}</select>
      </label>
      <button type="button" id="toggle-ass">${state.assistente ? "Dispensar assistente" : "Abrir assistente"}</button>
    </div>`;
}

function renderNav() {
  if (state.tela === "login" || state.tela === "comparar" || state.tela === "tokens") return "";
  const domains = [
    ["producao", "Produção"],
    ["receitas", "Receitas"],
    ["componentes", "Componentes"],
    ["conformidade", "Conformidade"],
  ];
  if (pode("gestao")) domains.push(["gestao", "Gestão"]);
  const menuAtivo = state.menu || ((aprovada() || state.direcao === "oficina") ? "producao" : "");
  const submenu = menuAtivo
    ? `<nav class="submenu" aria-label="Submenu ${menuAtivo}">${menusDe(menuAtivo)
        .map((item) => {
          const go = item === "Ingredientes" ? "ingredientes" : item === "Quadro" ? "quadro" : item === "Minhas receitas" ? "receita" : "";
          return `<button type="button" class="linkish" data-go="${go}">${item}</button>`;
        })
        .join("")}</nav>`
    : "";
  return `
    <header class="shell-header">
      ${brandMarkup()}
      <nav class="domains" aria-label="Domínios">
        ${domains
          .map(
            ([id, label]) =>
              `<button type="button" aria-expanded="${menuAtivo === id}" aria-current="${menuAtivo === id}" data-menu="${id}">${label}</button>`,
          )
          .join("")}
      </nav>
      <div>
        <span>${UX001.papeis[state.papel].nome}</span>
        <button type="button" data-go="login">Sair</button>
      </div>
    </header>
    ${submenu}
    <p class="crumb">Início / ${menuAtivo || "Produção"} / ${telas.find((t) => t[0] === state.tela)?.[1]}</p>`;
}

function renderAssistente() {
  if (!state.assistente || state.tela === "login" || state.tela === "comparar") return "";
  const guias = {
    primeiros: ["Conhecer o quadro", "Abrir uma ordem", "Registrar a primeira pesagem"],
    ingrediente: ["Identificar o item", "Informar unidade de massa", "Anexar fonte técnica"],
    receita: ["Escolher base", "Lançar farinha", "Revisar porcentagem do padeiro"],
    producao: ["Abrir sessão de pesagem", "Aguardar segunda conferência", "Seguir para a etapa"],
    erro: ["Ler o conflito 409", "Recarregar a ordem", "Reenviar o comando"],
  };
  const passos = guias[state.assistenteTipo] || guias.primeiros;
  const cls = state.direcao === "mesa" ? "overlay-assist panel" : state.direcao === "atelier" ? "sheet-assist panel" : "drawer-assist panel";
  return `
    <aside class="${cls}" role="dialog" aria-labelledby="ass-title">
      <h2 id="ass-title">Assistente: ${state.assistenteTipo}</h2>
      <p>Etapa 2 de ${passos.length} · objetivo: concluir sem apagar o que já foi digitado.</p>
      <div class="progress" aria-valuenow="66" aria-valuemin="0" aria-valuemax="100"><span style="width:66%"></span></div>
      <ol>${passos.map((p, i) => `<li${i === 1 ? " aria-current='step'" : ""}>${p}</li>`).join("")}</ol>
      <p>Bloqueio atual: ${state.estado === "bloqueio" ? "ocorrência bloqueante aberta" : "nenhum"}.</p>
      <p>Dado ausente: lote do fermento.</p>
      <p class="badge badge-info">Assistido por IA · fontes: ficha v2 e política da ordem · decisão humana</p>
      <div>
        <button type="button" data-ass="min">Minimizar</button>
        <button type="button" data-ass="off">Dispensar</button>
        <button type="button">Retomar depois</button>
      </div>
    </aside>`;
}

function nextAction() {
  if (pode("operar")) return "Registrar pesagem da Farinha";
  if (pode("escrever")) return "Completar dados nutricionais do fermento";
  if (pode("gestao")) return "Revisar acessos do estabelecimento";
  return "Somente leitura: acompanhar o quadro";
}

function renderEstado() {
  if (state.estado === "carregando") return `<p class="panel" role="status">Carregando dados sintéticos…</p>`;
  if (state.estado === "vazio") return `<p class="panel" role="status">Não há itens neste recorte sintético.</p>`;
  if (state.estado === "erro") return `<div class="panel" role="alert"><h2>API indisponível</h2><p>Falha simulada. Nenhuma chamada real foi feita.</p><button type="button">Tentar de novo</button></div>`;
  if (state.estado === "conflito") return `<div class="panel" role="alert"><h2>Conflito de estado</h2><p>O servidor recusou o comando. Os valores digitados foram preservados.</p><button type="button">Recarregar</button></div>`;
  if (state.estado === "bloqueio") return `<div class="panel" role="alert"><h2>Ordem bloqueada</h2><p>Há ocorrência bloqueante. A UI explica o motivo e não sugere bypass.</p></div>`;
  return "";
}

function aux(title, body) {
  return `<aside class="panel"><h2>${title}</h2>${body}</aside>`;
}

function screenLogin() {
  const logo = "imagens/original-pannebege.png";
  return `<main class="login"><img src="${logo}" alt="panne — quality recipes" /><h1>Entrar na Panne</h1><p>Protótipo visual. Sem provedor real e sem token.</p><button type="button" data-go="inicio">Entrar no laboratório</button></main>`;
}

function screenInicio() {
  const cards = `<div class="cards">
    <article class="card"><h2>Produção</h2><p>Quadro do turno e execução.</p><button type="button" data-go="quadro">Abrir quadro</button></article>
    <article class="card"><h2>Receitas</h2><p>Laboratório e fichas técnicas.</p><button type="button" data-go="receita">Abrir receitas</button></article>
    <article class="card"><h2>Componentes</h2><p>Ingredientes e bases — não “Cadastros”.</p><button type="button" data-go="ingredientes">Abrir ingredientes</button></article>
  </div>`;
  if (aprovada()) {
    return `<main class="main"><div class="stage"><div><h1>Início</h1><p class="lede">A marca permanece no cabeçalho. Próxima ação para ${UX001.papeis[state.papel].nome}: <strong>${nextAction()}</strong>.</p>${cards}</div>${aux("Neste turno", `<p>${badge("ok", "rastreabilidade completa do turno")}</p><p>${badge("atencao", "pendência de conferência")}</p>`)}</div></main>`;
  }
  return `<main class="main"><h1>Início</h1><p>Marca visível no cabeçalho. Próxima ação para ${UX001.papeis[state.papel].nome}: <strong>${nextAction()}</strong>.</p>${cards}</main>`;
}

function screenQuadro() {
  const rows = UX001.ordens
    .map(
      (o) => `<tr class="${o.bloqueio ? "bloqueada" : ""}"><td>${o.codigo}</td><td>${o.produto}</td><td>${badge(o.bloqueio ? "erro" : "info", o.estado)}</td><td>${o.acao}</td><td>${pode("operar") ? "<button type='button' data-go='operacional'>Executar</button>" : "—"}</td></tr>`,
    )
    .join("");
  const table = `<table><caption>Ordens sintéticas do turno</caption><thead><tr><th>Ordem</th><th>Produto</th><th>Estado</th><th>Próxima ação</th><th></th></tr></thead><tbody>${state.estado === "ok" ? rows : ""}</tbody></table>`;
  if (state.direcao === "mesa") {
    return `<main class="workbench"><div><h1>Quadro de produção</h1>${renderEstado()}<p>Atualizado agora.</p>${table}</div><aside class="inspector"><h2>Painel da tarefa</h2><p>${nextAction()}</p></aside></main>`;
  }
  if (aprovada()) {
    return `<main class="main"><div class="stage"><div><h1>Quadro de produção</h1><p class="lede">Atualizado agora. Ações críticas permanecem no lugar. Os blocos não se empilham como na Oficina original.</p>${renderEstado()}${table}</div>${aux("Próxima ação", `<p>${nextAction()}</p><p>${badge("info", "em execução")}</p>`)}</div></main>`;
  }
  return `<main class="main"><h1>Quadro de produção</h1>${renderEstado()}<p>Atualizado agora · densidade ${state.densidade}.</p>${table}</main>`;
}

function screenIngredientes() {
  const rows = UX001.ingredientes
    .map((i, idx) => `<tr><td><button type="button" data-go="ingrediente" data-idx="${idx}">${i.nome}</button></td><td>${badge(i.estado === "completo" ? "ok" : "atencao", i.estado)}</td><td>${i.pendencia}</td><td>${i.versao}</td></tr>`)
    .join("");
  const criar = pode("escrever") ? "<button type='button'>Novo ingrediente</button>" : "criação oculta neste papel";
  const table = `<table><caption>Componentes sintéticos</caption><thead><tr><th>Nome</th><th>Qualidade do dado</th><th>Pendência</th><th>Versão</th></tr></thead><tbody>${rows}</tbody></table>`;
  if (aprovada()) {
    return `<main class="main"><div class="stage"><div><h1>Ingredientes</h1><p class="lede">Ação interna: ${criar} — não vive na barra horizontal.</p>${table}</div>${aux("Qualidade", `<p>${badge("ok", "ingrediente completo")}</p><p>${badge("atencao", "dados nutricionais pendentes")}</p><p>${badge("atencao", "fonte ou alergênico pendente")}</p>`)}</div></main>`;
  }
  return `<main class="main"><h1>Ingredientes</h1><p>Ação interna: ${criar}.</p>${table}<p>${badge("ok", "ingrediente completo")} ${badge("atencao", "dados nutricionais pendentes")}</p></main>`;
}

function screenIngrediente() {
  const item = UX001.ingredientes[state.selecionado] || UX001.ingredientes[0];
  const form = `<form class="panel" onsubmit="return false">
      <label>Unidade de massa <select><option>g</option><option>kg</option></select></label>
      <label>Lote de referência <input value="" placeholder="não informado" /></label>
      <p>Assistente de cadastro: etapa 2 · informar unidade compatível. Sem CRUD real.</p>
      ${pode("escrever") ? "<button type='button'>Guardar rascunho sintético</button>" : "<p>Papel sem escrita.</p>"}
    </form>`;
  if (state.direcao === "mesa") {
    return `<main class="workbench"><div><h1>${item.nome}</h1>${form}</div><aside class="inspector"><h2>Completude</h2><div class="progress"><span style="width:55%"></span></div></aside></main>`;
  }
  if (aprovada()) {
    return `<main class="main"><div class="stage"><div><h1>${item.nome}</h1><p class="lede">${badge("info", item.versao)} ${badge(item.estado === "completo" ? "ok" : "atencao", item.pendencia)}</p>${form}</div>${aux("Completude", `<div class="progress"><span style="width:55%"></span></div><p>Nutrição e fonte ainda abertas.</p>`)}</div></main>`;
  }
  return `<main class="main"><h1>${item.nome}</h1><p>${badge("info", item.versao)}</p>${form}</main>`;
}

function screenReceita() {
  const cards = `<div class="cards">
      <article class="card planned"><h2>Planejado</h2><p>Farinha 1000 g · água 680 g · sal 20 g</p></article>
      <article class="card"><h2>Em construção</h2><p>Porcentagem do padeiro recalculada pelo domínio, não por este protótipo.</p>${pode("escrever") ? "<button type='button'>Abrir proposta assistida</button>" : ""}</article>
    </div>`;
  if (aprovada()) {
    return `<main class="main"><div class="stage"><div><h1>Laboratório de receita</h1><p class="lede">${badge("info", "receita pronta para trial")} ${badge("ok", "melhoria validada de rendimento")}</p>${cards}</div>${aux("Aprendizagem", `<p>Progresso da ficha técnica: 2 de 4 passos.</p><div class="progress"><span style="width:50%"></span></div>`)}</div></main>`;
  }
  return `<main class="main"><h1>Laboratório de receita</h1>${cards}</main>`;
}

function screenOperacional() {
  const blocos = `
    <section class="card"><h2>Pesagem</h2><p>Farinha 7,250 kg · fora da tolerância · outra sessão deve conferir.</p>${pode("operar") ? "<button type='button'>Registrar pesagem</button>" : "<p>Operação oculta neste papel.</p>"}</section>
    <section class="card"><h2>Etapas</h2><p>Fermentação · cronômetro visual 12:40</p></section>
    <section class="card"><h2>Encerramento</h2><p>Conclusão normal e encerramento parcial permanecem distintos.</p></section>`;
  if (aprovada()) {
    return `<main class="main"><h1>Executar OP-2026-0001</h1><p class="lede">${badge("info", "em execução")} ${badge("erro", "ocorrência bloqueante")} ${badge("atencao", "aguardando conferência")}</p><div class="ops-grid">${blocos}</div><div class="pin-action"><button type="button">Próxima ação operacional</button></div></main>`;
  }
  return `<main class="main"><h1>Executar OP-2026-0001</h1><p>${badge("info", "em execução")}</p><section class="panel">Pesagem</section><section class="panel">Etapas</section><section class="panel">Encerramento</section></main>`;
}

function screenFicha() {
  return `<article class="main panel"><img src="imagens/original-pannebege.png" alt="Panne" style="width:min(16rem,100%);height:auto" /><h1>Ficha de produção OP-2026-0001</h1>
    <p>Estabelecimento: Padaria Central (snapshot) · Responsável: Ana Padeiro · 23/08/2026</p>
    <p>Prévia A4, preto e branco. Sem custos. Logo completo na impressão.</p>
    <button type="button" class="no-print" onclick="window.print()">Imprimir prévia</button></article>`;
}

function screenTokens() {
  return `<main class="main"><h1>Sistema de design canônico</h1>
    <p class="lede">Oficina no cromado. Atelier na página. Bege #E5E4D6 · grafite #323334.</p>
    <p><button type="button">Primário</button> <button type="button">Secundário</button></p>
    <p>${badge("ok", "sucesso")} ${badge("atencao", "atenção")} ${badge("erro", "erro")} ${badge("info", "info")}</p>
    <div class="progress"><span style="width:40%"></span></div>
    <form class="panel"><label>Campo <input value="7,250" inputmode="decimal" /></label></form>
    <p>Gamificação responsável: ${badge("ok", "rastreabilidade completa do turno")}. Evitado: ${UX001.badgesProibidos.join("; ")}.</p></main>`;
}

function screenComparar() {
  return `<main class="main"><h1>Comparação</h1>
    <div class="cards">
      <article class="card"><h2>Oficina original</h2><p>Cabeçalho grafite, submenu trilho, seções empilhadas, gaveta. Aprovado como estrutura.</p></article>
      <article class="card"><h2>Atelier original</h2><p>Título grande, 8vw, cartões em grade, auxiliar ao lado. Aprovado só como página central.</p></article>
      <article class="card"><h2>Oficina + Atelier</h2><p>Cromado da Oficina + palco do Atelier. Sem empilhar blocos. Marca horizontal depois do login.</p></article>
      <article class="card"><h2>Mesa (histórico)</h2><p>Não entra na combinação. Permanece só para consulta.</p></article>
    </div></main>`;
}

const screens = {
  login: screenLogin,
  inicio: screenInicio,
  quadro: screenQuadro,
  ingredientes: screenIngredientes,
  ingrediente: screenIngrediente,
  receita: screenReceita,
  operacional: screenOperacional,
  ficha: screenFicha,
  tokens: screenTokens,
  comparar: screenComparar,
};

function render() {
  document.documentElement.dataset.direcao = state.direcao;
  document.getElementById("app").innerHTML =
    `<a class="skip" href="#conteudo">Ir para o conteúdo</a>` +
    renderMeta() +
    `<div class="prototype" id="conteudo">${renderNav()}${screens[state.tela]()}${renderAssistente()}</div>`;
  bind();
  syncUrl();
}

function bind() {
  const byId = (id) => document.getElementById(id);
  byId("dir")?.addEventListener("change", (e) => { state.direcao = e.target.value; render(); });
  byId("tela")?.addEventListener("change", (e) => { state.tela = e.target.value; render(); });
  byId("papel")?.addEventListener("change", (e) => { state.papel = e.target.value; render(); });
  byId("menu")?.addEventListener("change", (e) => { state.menu = e.target.value; render(); });
  byId("estado")?.addEventListener("change", (e) => { state.estado = e.target.value; render(); });
  byId("toggle-ass")?.addEventListener("click", () => { state.assistente = !state.assistente; render(); });
  document.querySelectorAll("[data-menu]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.menu = state.menu === btn.dataset.menu ? "" : btn.dataset.menu;
      render();
    });
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      if (!btn.dataset.go) return;
      state.tela = btn.dataset.go;
      if (btn.dataset.idx) state.selecionado = Number(btn.dataset.idx);
      if (btn.dataset.go === "ingredientes") state.menu = "componentes";
      if (btn.dataset.go === "quadro") state.menu = "producao";
      if (btn.dataset.go === "receita") state.menu = "receitas";
      if (btn.dataset.go === "ingrediente") state.assistenteTipo = "ingrediente";
      render();
    });
  });
  document.querySelectorAll("[data-ass]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.ass === "off" || btn.dataset.ass === "min") state.assistente = false;
      render();
    });
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    state.menu = "";
    state.assistente = false;
    render();
  }
});

render();
