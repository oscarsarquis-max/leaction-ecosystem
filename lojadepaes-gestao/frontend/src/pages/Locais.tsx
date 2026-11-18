import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useGestao } from "../contexto";
import { alterarLocal, criarLocal, listarLocais, textoDoErro, type Local } from "../lib/api";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";

export function Locais() {
  const { pode } = useGestao();
  const [locais, setLocais] = useState<Local[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [novo, setNovo] = useState(false);
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setLocais(await listarLocais());
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function agir(acao: () => Promise<unknown>) {
    setOcupado(true);
    setErro(null);
    try {
      await acao();
      await carregar();
      return true;
    } catch (falha) {
      setErro(textoDoErro(falha));
      return false;
    } finally {
      setOcupado(false);
    }
  }

  async function criar(event: FormEvent) {
    event.preventDefault();
    if (await agir(() => criarLocal(nome.trim()))) {
      setNome("");
      setNovo(false);
    }
  }

  const podeEditar = pode("lancar");
  return (
    <main className="fluxo-pagina">
      <PageHeader
        title="Locais"
        description="Onde as coisas ficam guardadas. A Despensa é o local padrão."
        actions={podeEditar ? <Button variant="primary" onClick={() => setNovo(true)}>Novo local</Button> : undefined}
      />
      {erro && !novo ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os locais agora.</p>
          <Button onClick={() => void carregar()}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!locais && !falhou ? <p className="fluxo-estado">Carregando os locais.</p> : null}
      {locais ? (
        <Card className="fluxo-lista-card">
          <ul className="fluxo-linhas" aria-label="Locais">
            {locais.map((l) => (
              <li key={l.id} className="fluxo-linha local-linha">
                <span className="col-nome">
                  <strong>{l.nome}</strong>
                </span>
                <span className="col-estado">
                  {l.padrao ? <StatusChip stage="ok" label="Padrão" /> : null}
                  {!l.ativo ? <StatusChip stage="completed" label="Inativo" /> : null}
                </span>
                {podeEditar ? (
                  <span className="col-acoes">
                    {!l.padrao && l.ativo ? (
                      <Button disabled={ocupado} onClick={() => void agir(() => alterarLocal(l.id, { padrao: true }))}>
                        Tornar padrão
                      </Button>
                    ) : null}
                    {!l.padrao ? (
                      <Button disabled={ocupado} onClick={() => void agir(() => alterarLocal(l.id, { ativo: !l.ativo }))}>
                        {l.ativo ? "Inativar" : "Reativar"}
                      </Button>
                    ) : null}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {novo ? (
        <SidePanel
          titulo="Novo local"
          onFechar={() => {
            setNovo(false);
            setErro(null);
          }}
        >
          <form className="painel-form" onSubmit={(e) => void criar(e)}>
            <label className="gestao-field">
              <span>Nome do local</span>
              <input type="text" value={nome} maxLength={80} onChange={(e) => setNome(e.target.value)} />
            </label>
            {erro ? (
              <p role="alert" className="form-erro">
                {erro}
              </p>
            ) : null}
            <div className="painel-acoes">
              <Button type="submit" variant="primary" disabled={ocupado || nome.trim().length === 0}>
                Criar local
              </Button>
              <Button onClick={() => setNovo(false)}>Cancelar</Button>
            </div>
          </form>
        </SidePanel>
      ) : null}
    </main>
  );
}
