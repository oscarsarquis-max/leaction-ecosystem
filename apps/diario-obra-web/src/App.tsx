import { useEffect, useState } from 'react';
import DailyLogForm from './components/DailyLogForm';
import Header from './components/Header';
import MicPermissionBanner from './components/MicPermissionBanner';
import SiteCalendar from './components/SiteCalendar';
import SiteSelector from './components/SiteSelector';
import type { CalendarDay, ProjectSite } from './types';
import { RDO_TENANT_KEY, RDO_USER_NAME_KEY, SSO_TOKEN_KEY } from './services/rdoSession';

function consumeSsoCallback(): boolean {
  const path = window.location.pathname.replace(/\/$/, '');
  if (!path.endsWith('/auth')) return false;

  const token = new URLSearchParams(window.location.search).get('token');
  if (token) {
    localStorage.setItem(SSO_TOKEN_KEY, token);
    try {
      const payload = JSON.parse(decodeURIComponent(escape(atob(token))));
      if (payload.tenant_id) localStorage.setItem(RDO_TENANT_KEY, payload.tenant_id);
      if (payload.name) localStorage.setItem(RDO_USER_NAME_KEY, payload.name);
    } catch {
      /* JWT ou formato opaco — mantém só o token */
    }
  }

  const base = import.meta.env.BASE_URL || '/';
  window.history.replaceState({}, '', base.endsWith('/') ? base : `${base}/`);
  return true;
}

type View = 'sites' | 'calendar' | 'form';

export default function App() {
  const [ready, setReady] = useState(() => !window.location.pathname.endsWith('/auth'));
  const [site, setSite] = useState<ProjectSite | null>(null);
  const [view, setView] = useState<View>('sites');
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null);
  const [calendarKey, setCalendarKey] = useState(0);

  useEffect(() => {
    consumeSsoCallback();
    setReady(true);
  }, []);

  function handleOpenDay(day: CalendarDay) {
    setSelectedDay(day);
    setView('form');
  }

  const readOnly = !selectedDay?.is_editable;

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Autenticando…
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-screen max-w-md flex-col overflow-hidden bg-slate-50 shadow-2xl">
      <Header subtitle={site ? site.name : 'Selecione o canteiro'} />
      <MicPermissionBanner />

      <main className="flex flex-1 flex-col overflow-hidden">
        {!site || view === 'sites' ? (
          <SiteSelector
            onSelect={(s) => {
              setSite(s);
              setView('calendar');
            }}
          />
        ) : view === 'calendar' ? (
          <SiteCalendar
            key={calendarKey}
            site={site}
            onBack={() => {
              setSite(null);
              setView('sites');
            }}
            onOpenDay={handleOpenDay}
          />
        ) : selectedDay ? (
          <DailyLogForm
            site={site}
            date={selectedDay.date}
            readOnly={readOnly}
            onBack={() => setView('calendar')}
            onSaved={() => setCalendarKey((k) => k + 1)}
          />
        ) : null}
      </main>
    </div>
  );
}
