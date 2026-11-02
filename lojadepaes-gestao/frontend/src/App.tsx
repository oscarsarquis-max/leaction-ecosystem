import { useCallback, useEffect, useState } from "react";
import { aoPerderSessao, carregarSessao, sair, type SessaoInfo } from "./lib/api";
import { Hoje } from "./pages/Hoje";
import { Login } from "./pages/Login";
import { Shell } from "./shell/Shell";

type Estado = { fase: "carregando" } | { fase: "anonimo" } | { fase: "logado"; sessao: SessaoInfo } | { fase: "erro" };

function caminhoAtual(): string {
  return window.location.pathname || "/";
}

export function App() {
  const [estado, setEstado] = useState<Estado>({ fase: "carregando" });
  const [path, setPath] = useState(caminhoAtual);

  const navegar = useCallback((to: string, substituir = false) => {
    if (to !== window.location.pathname) {
      if (substituir) window.history.replaceState(null, "", to);
      else window.history.pushState(null, "", to);
    }
    setPath(to);
    window.scrollTo?.(0, 0);
  }, []);

  useEffect(() => {
    const aoVoltar = () => setPath(caminhoAtual());
    window.addEventListener("popstate", aoVoltar);
    return () => window.removeEventListener("popstate", aoVoltar);
  }, []);

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

  // Só a tela Hoje existe nesta etapa: depois do login, qualquer outro endereço volta para ela.
  useEffect(() => {
    if (estado.fase === "logado" && path !== "/") {
      navegar("/", true);
    }
  }, [estado.fase, path, navegar]);

  async function aoSair() {
    try {
      await sair();
    } catch {
      // sem sessão no servidor: o resultado para quem usa é o mesmo
    }
    setEstado({ fase: "anonimo" });
    navegar("/entrar", true);
  }

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
        onEntrou={(sessao) => {
          setEstado({ fase: "logado", sessao });
          navegar("/", true);
        }}
      />
    );
  }

  return (
    <Shell path="/" onNavigate={navegar} sessao={estado.sessao} onSair={() => void aoSair()}>
      <Hoje />
    </Shell>
  );
}
