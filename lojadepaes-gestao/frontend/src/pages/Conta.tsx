import type { Organizacao, SessaoInfo } from "../lib/api";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Marca } from "../shell/Marca";
import "../shell/tokens.css";
import "./pages.css";

/** Quem entrou mas não opera nenhuma organização (como o admin da plataforma). */
export function SemOrganizacao({ sessao, onSair }: { sessao: SessaoInfo; onSair: () => void }) {
  return (
    <div className="gestao-frame gestao-login-frame">
      <main className="gestao-login">
        <p className="gestao-login-brand">
          <Marca altura={72} />
        </p>
        <Card className="gestao-login-card">
          <div className="gestao-login-corpo">
            <h1>Sua conta não opera nenhuma organização</h1>
            <p className="gestao-login-help">
              Você entrou como <strong>{sessao.nome}</strong>
              {sessao.admin_plataforma ? ", administrador da plataforma" : ""}. Esta conta não lança, ajusta nem junta nada:
              quem opera uma padaria é o membro dela. Peça a quem administra para vincular você a uma organização.
            </p>
            <Button className="gestao-login-submit" onClick={onSair}>
              Sair
            </Button>
          </div>
        </Card>
      </main>
    </div>
  );
}

/** Quem tem mais de uma organização escolhe em qual vai trabalhar. */
export function EscolherOrganizacao({
  sessao,
  onEscolher,
  onSair,
  erro,
}: {
  sessao: SessaoInfo;
  onEscolher: (org: Organizacao) => void;
  onSair: () => void;
  erro: string | null;
}) {
  return (
    <div className="gestao-frame gestao-login-frame">
      <main className="gestao-login">
        <p className="gestao-login-brand">
          <Marca altura={72} />
        </p>
        <Card className="gestao-login-card">
          <div className="gestao-login-corpo">
            <h1>Em qual organização você vai trabalhar?</h1>
            <p className="gestao-login-help">Olá, {sessao.nome}. Você pode trocar depois, pelo menu da sua conta.</p>
            <ul className="gestao-org-lista" aria-label="Suas organizações">
              {sessao.organizacoes.map((org) => (
                <li key={org.id}>
                  <button type="button" className="gestao-org-opcao" onClick={() => onEscolher(org)}>
                    <strong>{org.nome}</strong>
                    <span>CNPJ {org.cnpj_formatado}</span>
                  </button>
                </li>
              ))}
            </ul>
            {erro ? (
              <p role="alert" className="gestao-login-erro">
                {erro}
              </p>
            ) : null}
            <Button className="gestao-login-submit" onClick={onSair}>
              Sair
            </Button>
          </div>
        </Card>
      </main>
    </div>
  );
}
