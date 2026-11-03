import { useCallback, useEffect, useState, type FormEvent } from "react";
import { alterarMembro, criarMembro, listarMembros, textoDoErro, type Membro } from "../lib/api";
import { PAPEIS } from "../lib/format";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { PageHeader } from "../shell/PageHeader";
import { SidePanel } from "../shell/SidePanel";
import { StatusChip } from "../shell/StatusChip";
import "./fluxo.css";

type Painel = { tipo: "novo" } | { tipo: "membro"; id: string } | null;

export function Usuarios() {
  const [membros, setMembros] = useState<Membro[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [painel, setPainel] = useState<Painel>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const [usuario, setUsuario] = useState("");
  const [nome, setNome] = useState("");
  const [papel, setPapel] = useState("operador");
  const [senha, setSenha] = useState("");
  const [email, setEmail] = useState("");

  const carregar = useCallback(async () => {
    try {
      setMembros(await listarMembros());
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  function fechar() {
    setPainel(null);
    setErro(null);
    setUsuario("");
    setNome("");
    setSenha("");
    setEmail("");
    setPapel("operador");
  }

  async function criar(event: FormEvent) {
    event.preventDefault();
    setOcupado(true);
    setErro(null);
    try {
      await criarMembro({ usuario: usuario.trim(), nome: nome.trim(), papel, senha, email_contato: email.trim() || undefined });
      await carregar();
      fechar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  async function alterar(id: string, corpo: { papel?: string; ativo?: boolean }) {
    setOcupado(true);
    setErro(null);
    try {
      await alterarMembro(id, corpo);
      await carregar();
    } catch (falha) {
      setErro(textoDoErro(falha));
    } finally {
      setOcupado(false);
    }
  }

  const atual = painel?.tipo === "membro" ? membros?.find((m) => m.id === painel.id) : undefined;

  return (
    <main className="fluxo-pagina">
      <PageHeader
        title="Usuários"
        description="Quem opera a padaria no sistema. Só o dono convida ou altera."
        actions={
          <Button variant="primary" onClick={() => setPainel({ tipo: "novo" })}>
            Nova pessoa
          </Button>
        }
      />
      {falhou ? (
        <Card className="fluxo-vazio">
          <p role="alert">Não foi possível carregar os usuários agora.</p>
          <Button onClick={() => void carregar()}>Tentar de novo</Button>
        </Card>
      ) : null}
      {!membros && !falhou ? <p className="fluxo-estado">Carregando os usuários.</p> : null}
      {membros ? (
        <Card className="fluxo-lista-card">
          <ul className="fluxo-linhas" aria-label="Usuários da organização">
            {membros.map((m) => (
              <li key={m.id}>
                <button type="button" className="fluxo-linha usuario-linha" onClick={() => setPainel({ tipo: "membro", id: m.id })}>
                  <span className="col-nome">
                    <strong>{m.nome}</strong>
                    <span className="sub">
                      {m.usuario}
                      {m.voce ? " · você" : ""}
                    </span>
                  </span>
                  <span className="col-num">{PAPEIS[m.papel] ?? m.papel}</span>
                  <span className="col-estado">
                    <StatusChip stage={m.ativo ? "ok" : "completed"} label={m.ativo ? "Ativo" : "Inativo"} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {painel?.tipo === "novo" ? (
        <SidePanel titulo="Nova pessoa" subtitulo="O sistema não envia e-mail. Combine a senha pessoalmente." onFechar={fechar}>
          <form className="painel-form" onSubmit={(e) => void criar(e)}>
            <label className="gestao-field">
              <span>Nome</span>
              <input type="text" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)} />
            </label>
            <label className="gestao-field">
              <span>Login (usuário)</span>
              <input
                type="text"
                value={usuario}
                maxLength={80}
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                onChange={(e) => setUsuario(e.target.value)}
              />
            </label>
            <label className="gestao-field">
              <span>E-mail de contato (opcional)</span>
              <input type="email" value={email} maxLength={200} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="gestao-field">
              <span>Papel</span>
              <select value={papel} onChange={(e) => setPapel(e.target.value)}>
                {Object.entries(PAPEIS).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </label>
            <label className="gestao-field">
              <span>Senha inicial (mínimo de 12 caracteres)</span>
              <input type="password" autoComplete="new-password" value={senha} onChange={(e) => setSenha(e.target.value)} />
            </label>
            {erro ? (
              <p role="alert" className="form-erro">
                {erro}
              </p>
            ) : null}
            <div className="painel-acoes">
              <Button type="submit" variant="primary" disabled={ocupado || !nome.trim() || usuario.trim().length < 3 || senha.length < 12}>
                Criar pessoa
              </Button>
              <Button onClick={fechar}>Cancelar</Button>
            </div>
          </form>
        </SidePanel>
      ) : null}

      {atual ? (
        <SidePanel titulo={atual.nome} subtitulo={atual.usuario} onFechar={fechar}>
          {erro ? (
            <p role="alert" className="form-erro">
              {erro}
            </p>
          ) : null}
          <div className="painel-form">
            <label className="gestao-field">
              <span>Papel</span>
              <select value={atual.papel} disabled={ocupado} onChange={(e) => void alterar(atual.id, { papel: e.target.value })}>
                {Object.entries(PAPEIS).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </select>
            </label>
            {atual.email_contato ? <p className="sub">E-mail de contato: {atual.email_contato}</p> : null}
            <div className="painel-acoes">
              <Button disabled={ocupado} onClick={() => void alterar(atual.id, { ativo: !atual.ativo })}>
                {atual.ativo ? "Desativar acesso" : "Reativar acesso"}
              </Button>
            </div>
            <p className="sub">A organização precisa de pelo menos um dono ativo.</p>
          </div>
        </SidePanel>
      ) : null}
    </main>
  );
}
