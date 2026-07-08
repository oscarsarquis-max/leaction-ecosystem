import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Scale, Variable } from "lucide-react";
import AppNavbar from "../components/AppNavbar";
import FormulasIndicadoresTab from "../components/configuracao/FormulasIndicadoresTab";
import PesosIapsTab from "../components/configuracao/PesosIapsTab";
import { getOrganizacaoNome } from "../config/organizacao";

const ABA_STORAGE_KEY = "prodinx.config.abaAtiva";

const ABAS = [
  {
    id: "pesos",
    rotulo: "Pesos do IAPS",
    descricao: "Proporção Individual/Equipe e pesos SPACE por subpapel",
    icone: Scale,
  },
  {
    id: "formulas",
    rotulo: "Fórmulas e Variáveis",
    descricao: "Expressões mathjs e parâmetros mesclados ao JSON ingerido",
    icone: Variable,
  },
];

function ConfiguracaoParametros() {
  const [abaAtiva, setAbaAtiva] = useState(() => {
    if (typeof window === "undefined") {
      return "pesos";
    }

    const salva = window.sessionStorage.getItem(ABA_STORAGE_KEY);
    return ABAS.some((aba) => aba.id === salva) ? salva : "pesos";
  });

  useEffect(() => {
    window.sessionStorage.setItem(ABA_STORAGE_KEY, abaAtiva);
  }, [abaAtiva]);

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-brand-verde text-white shadow-md">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-laranja font-bold text-white">
              P
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-white/70">
                {getOrganizacaoNome()} · Administração
              </p>
              <h1 className="text-xl font-bold leading-tight">Configuração de Parâmetros IAPS</h1>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <AppNavbar />
            <Link
              to="/dashboard"
              className="btn-primary inline-flex items-center gap-2 bg-brand-laranja"
            >
              <ArrowLeft className="h-4 w-4" strokeWidth={2} />
              Voltar para o Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 border-b border-gray-200">
          <nav
            className="-mb-px flex gap-1 overflow-x-auto"
            aria-label="Secções de configuração"
            role="tablist"
          >
            {ABAS.map((aba) => {
              const Icone = aba.icone;
              const ativa = abaAtiva === aba.id;

              return (
                <button
                  key={aba.id}
                  id={`tab-${aba.id}`}
                  type="button"
                  role="tab"
                  aria-selected={ativa}
                  aria-controls={`panel-${aba.id}`}
                  onClick={() => setAbaAtiva(aba.id)}
                  className={`inline-flex shrink-0 flex-col items-start gap-0.5 border-b-2 px-4 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-brand-laranja/40 focus:ring-offset-2 sm:flex-row sm:items-center sm:gap-2 ${
                    ativa
                      ? "border-brand-laranja text-brand-verde"
                      : "border-transparent text-brand-cinza/70 hover:border-brand-verde/30 hover:text-brand-cinza"
                  }`}
                >
                  <span className="inline-flex items-center gap-2 text-sm font-semibold">
                    <Icone className="h-4 w-4" strokeWidth={2} />
                    {aba.rotulo}
                  </span>
                  <span className="hidden text-xs font-normal text-brand-cinza/60 lg:inline">
                    {aba.descricao}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {ABAS.map((aba) => (
          <div
            key={aba.id}
            id={`panel-${aba.id}`}
            role="tabpanel"
            aria-labelledby={`tab-${aba.id}`}
            hidden={abaAtiva !== aba.id}
            className={abaAtiva === aba.id ? "block" : "hidden"}
          >
            {aba.id === "pesos" ? <PesosIapsTab /> : <FormulasIndicadoresTab />}
          </div>
        ))}
      </main>
    </div>
  );
}

export default ConfiguracaoParametros;
