import { type ReactNode } from 'react';
import SegSenseLogo from './SegSenseLogo';
import RouteFocus from './RouteFocus';

export default function PublicShell(props: { children: ReactNode }) {
  return (
    <div className="public-app">
      <RouteFocus />
      <header className="public-header">
        <SegSenseLogo surface="public" />
      </header>
      <main id="main-content" className="public-main" tabIndex={-1}>
        {props.children}
      </main>
    </div>
  );
}
