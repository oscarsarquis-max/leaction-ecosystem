import { NavLink, Outlet } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { apiBaseUrl, fetchSystemInfo, type SystemInfo } from '../api/systemInfo';
import SegSenseLogo from './SegSenseLogo';
import TechnicalAuditDetails from './TechnicalAuditDetails';
import RouteFocus from './RouteFocus';

function environmentLabel(info: SystemInfo | null, failed: boolean): string {
  if (failed) {
    return 'Ambiente indisponível';
  }
  if (info == null) {
    return 'Verificando ambiente…';
  }
  return info.operationalState === 'UP' ? 'Ambiente disponível' : 'Ambiente degradado';
}

export default function AdminShell() {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchSystemInfo(apiBaseUrl(), controller.signal)
      .then((payload) => {
        setInfo(payload);
        setFailed(false);
      })
      .catch(() => {
        setInfo(null);
        setFailed(true);
      });
    return () => {
      controller.abort();
    };
  }, []);

  return (
    <div className="admin-app">
      <RouteFocus />
      <header className="admin-header">
        <SegSenseLogo surface="admin" withName />
        <nav className="admin-nav" aria-label="Principal">
          <NavLink to="/admin" end>
            Início
          </NavLink>
          <NavLink to="/admin/catalogo">Catálogo</NavLink>
          <NavLink to="/admin/oportunidades">Oportunidades</NavLink>
          <NavLink to="/admin/demonstracoes">Demonstrações</NavLink>
        </nav>
        <p className="admin-environment">{environmentLabel(info, failed)}</p>
      </header>
      <main id="main-content" className="admin-body" tabIndex={-1}>
        <Outlet />
        {info ? (
          <TechnicalAuditDetails summary="Detalhes técnicos do ambiente">
            <p>Nome: {info.name}</p>
            <p>Versão: {info.version}</p>
            <p>Identidade da aplicação: {info.applicationId}</p>
            <p>Estado operacional interno: {info.operationalState}</p>
          </TechnicalAuditDetails>
        ) : null}
      </main>
    </div>
  );
}
