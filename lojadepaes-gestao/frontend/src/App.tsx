import { useCallback, useEffect, useMemo, useState } from "react";
import { podeSair } from "./lib/guardaSaida";
import { GestaoContext, type GestaoCtx } from "./contexto";
import {
  aoPerderSessao,
  carregarFluxo,
  carregarSessao,
  escolherOrganizacao,
  sair,
  textoDoErro,
  type Etapa,
  type SessaoInfo,
} from "./lib/api";
import { EscolherOrganizacao, SemOrganizacao } from "./pages/Conta";
import { EntradaSemNota } from "./pages/EntradaSemNota";
import { Entradas } from "./pages/Entradas";
import { Hoje } from "./pages/Hoje";
import { Comanda } from "./pages/Comanda";
import { Producao } from "./pages/Producao";
import { Programacoes } from "./pages/Programacoes";
import { Ingredientes } from "./pages/Ingredientes";
import { Produtos } from "./pages/Produtos";
import { EditorReceita, Receitas } from "./pages/Receitas";
import { Locais } from "./pages/Locais";
import { Padroes } from "./pages/Padroes";
import { Login } from "./pages/Login";
import { Usuarios } from "./pages/Usuarios";
import { Shell } from "./shell/Shell";

type Estado =
  | { fase: "carregando" }
  | { fase: "anonimo" }
  | { fase: "logado"; sessao: SessaoInfo }
  | { fase: "erro" };

const ROTAS = ["/", "/entradas", "/entradas/sem-nota", "/ingredientes", "/produtos", "/receitas", "/producao", "/producao/dia", "/producao/programacoes", "/producao/comanda", "/gestao/padroes", "/gestao/locais", "/gestao/usuarios"];

function enderecoAtual(): { path: string; search: string } {
  return { path: window.location.pathname || "/", search: window.location.search || "" };
}

export function App() {
  const [estado, setEstado] = useState<Estado>({ fase: "carregando" });
  const [local, setLocal] = useState(enderecoAtual);
  const [etapas, setEtapas] = useState<Etapa[] | null>(null);
  const [erroOrg, setErroOrg] = useState<string | null>(null);
  const [tituloPagina, setTituloPagina] = useState<string | null>(null);
  const definirTitulo = useCallback((titulo: string | null) => setTituloPagina(titulo), []);

  const navegar = useCallback((para: string, substituir = false) => {
    const alvo = new URL(para, window.location.origin);
    const completo = `${alvo.pathname}${alvo.search}`;
    if (completo !== `${window.location.pathname}${window.location.search}`) {
      if (!podeSair()) return;
      if (substituir) window.history.replaceState(null, "", completo);
      else window.history.pushState(null, "", completo);
    }
    setLocal({ path: alvo.pathname, search: alvo.search });
    window.scrollTo?.(0, 0);
  }, []);

  useEffect(() => {
    const aoVoltar = () => {
      if (!podeSair()) {
        window.history.pushState(null, "", `${local.path}${local.search}`);
        return;
      }
      setLocal(enderecoAtual());
    };
    window.addEventListener("popstate", aoVoltar);
    return () => window.removeEventListener("popstate", aoVoltar);
  }, [local]);

  useEffect(() => {
    aoPerderSessao(() => setEstado({ fase: "anonimo" }));
    return () => aoPerderSessao(null);
  }, []);

  useEffect(() => {
    let ativo = true;
    carregarSessao()
      .then((sessao) => {
        if (ativo) setEstado(sessao ? { fase: "logado", sessao } : { fase: "anonimo" });
      })
      .catch(() => {
        if (ativo) setEstado({ fase: "erro" });
      });
    return () => {
      ativo = false;
    };
  }, []);

  const sessao = estado.fase === "logado" ? estado.sessao : null;
  const operando = Boolean(sessao?.organizacao) && !sessao?.precisa_escolher_organizacao;
  const organizacaoId = sessao?.organizacao?.id ?? null;

  const atualizarFluxo = useCallback(() => {
    carregarFluxo()
      .then((fluxo) => setEtapas(fluxo.etapas))
      .catch(() => {
        // as bolinhas ficam como estavam; a tela em si mostra o erro se for o caso
      });
  }, []);

  useEffect(() => {
    if (operando) atualizarFluxo();
    else setEtapas(null);
  }, [operando, organizacaoId, atualizarFluxo]);

  // Endereço que não existe volta para Hoje; quem não pode ver Usuários também.
  useEffect(() => {
    if (!operando || !sessao) return;
    const conhecida = ROTAS.includes(local.path) || /^\/receitas\/[^/]+$/.test(local.path);
    const permitida = local.path !== "/gestao/usuarios" || sessao.permissoes.includes("gerenciar_usuarios");
    if (!conhecida || !permitida) navegar("/", true);
  }, [operando, sessao, local.path, navegar]);

  async function aoSair() {
    try {
      await sair();
    } catch {
      // sem sessão no servidor: o resultado para quem usa é o mesmo
    }
    setEstado({ fase: "anonimo" });
    setEtapas(null);
    navegar("/entrar", true);
  }

  async function trocarOrganizacao(id: string) {
    setErroOrg(null);
    try {
      const nova = await escolherOrganizacao(id);
      setEstado({ fase: "logado", sessao: nova });
      navegar("/", true);
    } catch (falha) {
      setErroOrg(textoDoErro(falha, "Não foi possível trocar de organização agora."));
    }
  }

  const contexto: GestaoCtx | null = useMemo(
    () =>
      sessao
        ? {
            sessao,
            search: local.search,
            navegar,
            atualizarFluxo,
            pode: (acao: string) => sessao.permissoes.includes(acao),
            definirTitulo,
            tituloPagina,
          }
        : null,
    [sessao, local.search, navegar, atualizarFluxo, definirTitulo, tituloPagina],
  );

  if (estado.fase === "carregando") {
    return (
      <div className="gestao-frame" role="status" aria-live="polite">
        <p style={{ padding: 24, margin: 0 }}>Carregando…</p>
      </div>
    );
  }

  if (estado.fase === "erro") {
    return (
      <div className="gestao-frame">
        <p role="alert" style={{ padding: 24, margin: 0 }}>
          Não consegui falar com o servidor. Recarregue a página em instantes.
        </p>
      </div>
    );
  }

  if (estado.fase === "anonimo") {
    return (
      <Login
        onEntrou={(nova) => {
          setEstado({ fase: "logado", sessao: nova });
          navegar("/", true);
        }}
      />
    );
  }

  if (estado.sessao.precisa_escolher_organizacao) {
    return (
      <EscolherOrganizacao
        sessao={estado.sessao}
        erro={erroOrg}
        onEscolher={(org) => void trocarOrganizacao(org.id)}
        onSair={() => void aoSair()}
      />
    );
  }

  if (!estado.sessao.organizacao || !contexto) {
    return <SemOrganizacao sessao={estado.sessao} onSair={() => void aoSair()} />;
  }

  if (local.path === "/producao/comanda") {
    return (
      <GestaoContext.Provider value={contexto}>
        <Comanda />
      </GestaoContext.Provider>
    );
  }

  let pagina;
  switch (local.path) {
    case "/entradas":
      pagina = <Entradas />;
      break;
    case "/entradas/sem-nota":
      pagina = <EntradaSemNota />;
      break;
    case "/ingredientes":
      pagina = <Ingredientes />;
      break;
    case "/produtos":
      pagina = <Produtos />;
      break;
    case "/receitas":
      pagina = <Receitas />;
      break;
    case "/producao":
    case "/producao/dia":
      pagina = <Producao dia={local.path === "/producao/dia"} />;
      break;
    case "/producao/programacoes":
      pagina = <Programacoes />;
      break;
    case "/gestao/padroes":
      pagina = <Padroes />;
      break;
    case "/gestao/locais":
      pagina = <Locais />;
      break;
    case "/gestao/usuarios":
      pagina = <Usuarios />;
      break;
    default:
      pagina = local.path.startsWith("/receitas/") ? (
        <EditorReceita produtoId={decodeURIComponent(local.path.slice("/receitas/".length))} />
      ) : (
        <Hoje />
      );
  }

  return (
    <GestaoContext.Provider value={contexto}>
      <Shell
        path={local.path}
        onNavigate={navegar}
        sessao={estado.sessao}
        etapas={etapas}
        onSair={() => void aoSair()}
        onTrocarOrganizacao={(id) => void trocarOrganizacao(id)}
      >
        {pagina}
      </Shell>
    </GestaoContext.Provider>
  );
}
