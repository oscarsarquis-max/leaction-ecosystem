import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const CREDENCIAIS_VALIDAS = {
  email: "sistema@prodinx.com.br",
  codigo: "prodinx2026",
};

function LoginDecor3D() {
  return (
    <div className="login-scene-3d relative hidden h-32 w-52 shrink-0 lg:block" aria-hidden="true">
      <div className="login-slab login-slab-1" />
      <div className="login-slab login-slab-2" />
      <div className="login-slab login-slab-3" />
    </div>
  );
}

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const destinoAposLogin = location.state?.from?.pathname || "/dashboard";
  const [email, setEmail] = useState("");
  const [codigo, setCodigo] = useState("");
  const [erro, setErro] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    setErro("");

    if (email === CREDENCIAIS_VALIDAS.email && codigo === CREDENCIAIS_VALIDAS.codigo) {
      login();
      navigate(destinoAposLogin, { replace: true });
      return;
    }

    setErro("E-mail ou código de acesso inválidos.");
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-r from-[#E8F5EE] via-[#9BC4AD] to-brand-verde">
      <header className="login-header-zone relative w-full px-4 pb-8 pt-6 sm:px-8 sm:pb-10 sm:pt-8">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black/5 to-transparent"
          aria-hidden="true"
        />

        <div className="relative mx-auto flex max-w-7xl items-end justify-between gap-8">
          <div className="hidden flex-col gap-2 lg:flex">
            <LoginDecor3D />
            <p className="max-w-[13rem] text-[10px] font-semibold uppercase tracking-[0.18em] text-white/80 [text-shadow:0_1px_2px_rgba(0,0,0,0.2)]">
              Acesso em camadas · Individual · Equipe · Organização
            </p>
          </div>

          <div className="relative ml-auto w-full max-w-3xl">
            <div className="login-panel-3d relative overflow-hidden rounded-2xl border border-white/70 bg-white/95 px-5 py-5 backdrop-blur-md sm:px-6">
              <div
                className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-brand-laranja/15 blur-2xl"
                aria-hidden="true"
              />
              <div
                className="pointer-events-none absolute -bottom-6 -left-6 h-20 w-20 rounded-full bg-brand-verde/20 blur-2xl"
                aria-hidden="true"
              />

              <div className="relative flex flex-col items-end gap-2">
                <p className="mb-1 w-full text-right text-[10px] font-bold uppercase tracking-[0.2em] text-brand-verde/70 sm:text-xs">
                  Portal de acesso
                </p>

                <form
                  onSubmit={handleSubmit}
                  className="flex w-full flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-end"
                >
                  <label className="flex min-w-[200px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-brand-cinza sm:min-w-[220px]">
                    E-mail
                    <input
                      type="email"
                      name="email"
                      autoComplete="username"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className="login-input-inset rounded-lg border border-brand-verde/15 bg-[#f7faf8] px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-brand-cinza outline-none transition focus:border-brand-verde"
                      placeholder="seu@email.com"
                      required
                    />
                  </label>

                  <label className="flex min-w-[200px] flex-1 flex-col gap-1.5 text-xs font-semibold uppercase tracking-wide text-brand-cinza sm:min-w-[180px]">
                    Código de Acesso
                    <input
                      type="password"
                      name="codigo"
                      autoComplete="current-password"
                      value={codigo}
                      onChange={(event) => setCodigo(event.target.value)}
                      className="login-input-inset rounded-lg border border-brand-verde/15 bg-[#f7faf8] px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-brand-cinza outline-none transition focus:border-brand-verde"
                      placeholder="••••••••"
                      required
                    />
                  </label>

                  <button
                    type="submit"
                    className="login-btn-extrude rounded-lg bg-brand-verde px-7 py-2.5 text-sm font-bold uppercase tracking-wide text-white focus:outline-none focus:ring-2 focus:ring-brand-laranja focus:ring-offset-2 sm:self-end"
                  >
                    Acessar
                  </button>
                </form>

                {erro && (
                  <p
                    className="text-right text-xs font-medium text-brand-vermelho"
                    role="alert"
                    aria-live="polite"
                  >
                    {erro}
                  </p>
                )}
              </div>

              <div className="login-panel-lip" aria-hidden="true" />
            </div>
          </div>
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
        <div className="flex flex-col items-start">
          <h1
            className="select-none text-left text-7xl font-black uppercase tracking-tight sm:text-8xl md:text-9xl"
            aria-label="Prodinx"
          >
            <span className="text-brand-verde">PROD</span>
            <span className="text-brand-laranja">INX</span>
          </h1>

          <p className="mt-2 text-left text-xs font-semibold uppercase tracking-[0.12em] text-brand-laranja sm:text-sm md:text-base">
            Sistema de Medição de Produtividade Empresarial
          </p>
        </div>
      </main>
    </div>
  );
}

export default Login;
