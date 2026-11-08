import { useRef, useState, type FormEvent } from "react";
import { ApiError, entrar, type SessaoInfo } from "../lib/api";
import { Button } from "../shell/Button";
import { Card } from "../shell/Card";
import { Marca } from "../shell/Marca";
import "../shell/tokens.css";
import "./pages.css";

type Props = {
  onEntrou: (sessao: SessaoInfo) => void;
};

function mensagemDeErro(erro: unknown): string {
  if (erro instanceof ApiError) {
    if (erro.status === 401) return "Usuário ou senha inválidos.";
    if (erro.status === 429) return "Muitas tentativas. Aguarde alguns minutos e tente de novo.";
    if (erro.status === 503) return "O acesso ainda não está configurado neste servidor.";
  }
  return "Não foi possível entrar agora. Tente de novo em instantes.";
}

export function Login({ onEntrou }: Props) {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const senhaRef = useRef<HTMLInputElement>(null);

  async function enviar(event: FormEvent) {
    event.preventDefault();
    if (enviando) return;
    setEnviando(true);
    setErro(null);
    try {
      onEntrou(await entrar(usuario, senha));
    } catch (falha) {
      setErro(mensagemDeErro(falha));
      setSenha("");
      senhaRef.current?.focus();
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="gestao-frame gestao-login-frame">
      <main className="gestao-login">
        <p className="gestao-login-brand">
          <Marca altura={72} />
        </p>
        <Card className="gestao-login-card">
          <form onSubmit={enviar} noValidate>
            <h1>Entrar</h1>
            <p className="gestao-login-help">Acesso restrito à equipe da padaria.</p>
            <label className="gestao-field">
              <span>Usuário</span>
              <input
                name="usuario"
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                value={usuario}
                onChange={(event) => setUsuario(event.target.value)}
                aria-invalid={erro ? true : undefined}
                aria-describedby={erro ? "login-erro" : undefined}
                required
              />
            </label>
            <label className="gestao-field">
              <span>Senha</span>
              <input
                ref={senhaRef}
                name="senha"
                type="password"
                autoComplete="current-password"
                value={senha}
                onChange={(event) => setSenha(event.target.value)}
                aria-invalid={erro ? true : undefined}
                aria-describedby={erro ? "login-erro" : undefined}
                required
              />
            </label>
            {erro ? (
              <p id="login-erro" role="alert" className="gestao-login-erro">
                {erro}
              </p>
            ) : null}
            <Button type="submit" variant="primary" className="gestao-login-submit" disabled={enviando || !usuario || !senha}>
              {enviando ? "Entrando…" : "Entrar"}
            </Button>
          </form>
        </Card>
      </main>
    </div>
  );
}
