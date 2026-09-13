import { type ReactNode } from 'react';

export type OpportunityTabId = 'content' | 'governance' | 'purpose' | 'links';

const TABS: Array<{ id: OpportunityTabId; label: string }> = [
  { id: 'content', label: 'Conteúdo' },
  { id: 'governance', label: 'Governança' },
  { id: 'purpose', label: 'Finalidade e transparência' },
  { id: 'links', label: 'Links contextuais' },
];

export default function OpportunityTabs(props: {
  selected: OpportunityTabId;
  onSelect: (tab: OpportunityTabId) => void;
  panels: Record<OpportunityTabId, ReactNode>;
}) {
  return (
    <div className="opportunity-tabs">
      <div role="tablist" aria-label="Visões da oportunidade" className="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={props.selected === tab.id}
            aria-controls={`panel-${tab.id}`}
            tabIndex={props.selected === tab.id ? 0 : -1}
            onClick={() => {
              props.onSelect(tab.id);
            }}
            onKeyDown={(event) => {
              const index = TABS.findIndex((item) => item.id === props.selected);
              let next: (typeof TABS)[number] | undefined;
              if (event.key === 'ArrowRight') {
                next = TABS[(index + 1 + TABS.length) % TABS.length];
              } else if (event.key === 'ArrowLeft') {
                next = TABS[(index - 1 + TABS.length) % TABS.length];
              } else if (event.key === 'Home') {
                next = TABS[0];
              } else if (event.key === 'End') {
                next = TABS[TABS.length - 1];
              } else {
                return;
              }
              event.preventDefault();
              if (!next) {
                return;
              }
              props.onSelect(next.id);
              document.getElementById(`tab-${next.id}`)?.focus();
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {TABS.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={props.selected !== tab.id}
        >
          {props.selected === tab.id ? props.panels[tab.id] : null}
        </div>
      ))}
    </div>
  );
}
