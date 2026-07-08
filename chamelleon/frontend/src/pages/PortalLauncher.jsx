import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  canAccessDiarioObra,
  getDiarioObraAuthUrl,
  loginDataFromSession,
} from '../utils/appLauncher';
import { getSession } from '../services/session';

function AppCard({ title, description, icon, accent, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'group flex min-h-[220px] w-full flex-col items-center justify-center rounded-2xl border-2 bg-white p-8 text-center shadow-md transition',
        'hover:-translate-y-1 hover:shadow-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        accent,
      ].join(' ')}
    >
      <span
        className="mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-white/80 text-5xl shadow-inner transition group-hover:scale-105"
        aria-hidden
      >
        {icon}
      </span>
      <h2 className="text-lg font-bold text-slate-900">{title}</h2>
      <p className="mt-2 max-w-xs text-sm leading-relaxed text-slate-600">{description}</p>
    </button>
  );
}

export default function PortalLauncher() {
  const navigate = useNavigate();
  const { userName, logout, sector, frameworkId } = useAuth();
  const displayName = userName?.split(' ')[0] || 'colega';
  const showDiario = canAccessDiarioObra({ sector, framework_id: frameworkId });

  function openDiarioObra() {
    const payload = loginDataFromSession(getSession());
    if (!payload || !canAccessDiarioObra(payload)) return;
    window.location.replace(getDiarioObraAuthUrl(payload));
  }

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 via-white to-chameleon/10">
      <header className="flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-3">
          <img
            src="/images/camelleonlogo.png"
            alt="Chamelleon"
            className="h-12 w-12 rounded-xl object-cover shadow-sm"
          />
          <span className="text-sm font-semibold text-slate-600">Chamelleon</span>
        </div>
        <button
          type="button"
          onClick={() => {
            logout();
            navigate('/acesso', { replace: true });
          }}
          className="text-sm font-medium text-slate-500 hover:text-slate-800"
        >
          Sair
        </button>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-4 pb-16 pt-4">
        <div className="w-full max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-chameleon-dark">
            Portal de aplicativos
          </p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900 sm:text-4xl">
            Olá, {displayName}. Onde vamos trabalhar hoje?
          </h1>
          <p className="mx-auto mt-3 max-w-lg text-slate-600">
            {showDiario
              ? 'Escolha o ambiente para continuar. Você pode alternar entre eles a qualquer momento voltando a este portal.'
              : 'Acesse o painel de gestão do Chamelleon. O Diário de Obra (Gemba) está disponível apenas para o setor Construção Civil.'}
          </p>
        </div>

        <div
          className={[
            'mt-10 flex w-full flex-col gap-4 sm:gap-6',
            showDiario ? 'max-w-4xl sm:flex-row' : 'max-w-md',
          ].join(' ')}
        >
          <AppCard
            title="Painel de Gestão (Chamelleon)"
            description="Dashboards, diagnósticos, avaliações e gestão da transformação."
            icon="📊"
            accent="border-chameleon/30 hover:border-chameleon focus-visible:ring-chameleon"
            onClick={() => navigate('/', { replace: true })}
          />
          {showDiario && (
            <AppCard
              title="Diário de Obra (Gemba)"
              description="Registro diário no canteiro — clima, efetivo, segurança e insumos."
              icon="⛑️"
              accent="border-emerald-300 hover:border-emerald-500 focus-visible:ring-emerald-500"
              onClick={openDiarioObra}
            />
          )}
        </div>
      </main>
    </div>
  );
}
